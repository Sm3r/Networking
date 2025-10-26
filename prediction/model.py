import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error


class NetworkTrafficPredictor:
    """RNN model with GRU for predicting network traffic patterns."""
    
    def __init__(self, sequence_length=12, gru_units=128, dropout_rate=0.3, learning_rate=0.001):
        """
        Initialize the network traffic predictor.
        
        Args:
            sequence_length: Number of time steps to look back
            gru_units: Number of units in GRU layers
            dropout_rate: Dropout rate for regularization
            learning_rate: Initial learning rate
        """
        self.sequence_length = sequence_length
        self.gru_units = gru_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.model = None
        self.scaler = MinMaxScaler()
        self.ip_to_index = {}
        self.index_to_ip = {}
        
    def prepare_sequences(self, aggregated_data):
        """
        Prepare sequences for time series prediction.
        
        Args:
            aggregated_data: Aggregated traffic data DataFrame
            
        Returns:
            tuple: (X, y, ip_columns, y_time_bins)
        """
        # Ensure data is sorted by time
        aggregated_data = aggregated_data.sort_values('time_bin').reset_index(drop=True)

        # Encode IP addresses
        unique_ips = sorted(aggregated_data['ip'].unique())
        self.ip_to_index = {ip: idx for idx, ip in enumerate(unique_ips)}
        self.index_to_ip = {idx: ip for ip, idx in self.ip_to_index.items()}
        
        # Create pivot table: rows=time_bins, columns=IPs, values=traffic_size
        pivot_data = aggregated_data.pivot(
            index='time_bin', 
            columns='ip', 
            values='total_traffic_size'
        ).fillna(0)
        
        # Ensure all IPs are present as columns
        for ip in unique_ips:
            if ip not in pivot_data.columns:
                pivot_data[ip] = 0
        
        # Sort columns by IP for consistency
        pivot_data = pivot_data[sorted(pivot_data.columns)]
        
        # Scale the data
        scaled_data = self.scaler.fit_transform(pivot_data.values)
        
        # Create sequences
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            y.append(scaled_data[i])

        y_time_bins = pivot_data.index.values[self.sequence_length:]

        return np.array(X), np.array(y), pivot_data.columns.tolist(), y_time_bins
    
    def build_model(self, n_features):
        """
        Build a simplified GRU model.
        
        Args:
            n_features: Number of features (IPs)
        """
        self.model = Sequential([
            # First GRU layer with return sequences
            GRU(self.gru_units, 
                return_sequences=True,
                input_shape=(self.sequence_length, n_features)),
            BatchNormalization(),
            Dropout(self.dropout_rate),
            
            # Second GRU layer
            GRU(self.gru_units // 2, return_sequences=False),
            BatchNormalization(),
            Dropout(self.dropout_rate),
            
            # Dense layers
            Dense(n_features * 2, activation='relu'),
            Dropout(self.dropout_rate * 0.5),
            
            # Output layer (linear activation for regression)
            Dense(n_features, activation='linear')
        ])
        
        optimizer = Adam(learning_rate=self.learning_rate, clipnorm=1.0)
        
        self.model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae']
        )
        
        return self.model
    
    def train(self, X, y, validation_split=0.2, epochs=50, batch_size=32):
        """
        Train the model.
        
        Args:
            X: Input sequences
            y: Target values
            validation_split: Fraction of data for validation
            epochs: Number of training epochs
            batch_size: Batch size for training
            
        Returns:
            Training history
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=20,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=10,
                verbose=1,
                min_lr=1e-6
            ),
            ModelCheckpoint(
                'best_model.keras',
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            )
        ]

        print(f"\nTraining on {len(X)} samples, validation split: {validation_split}")
        print(f"Batch size: {batch_size}, Max epochs: {epochs}\n")

        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            shuffle=False,  # Keep False for time series data
            callbacks=callbacks
        )
        
        return history
    
    def predict(self, X, batch_size=None):
        """
        Make predictions.
        
        Args:
            X: Input sequences
            batch_size: Batch size for prediction
            
        Returns:
            Predictions (non-negative, inverse transformed)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        predictions = self.model.predict(X, batch_size=batch_size)
        predictions_scaled = self.scaler.inverse_transform(predictions)
        
        # Ensure all predictions are non-negative
        return np.maximum(predictions_scaled, 0)
    
    def evaluate_model(self, X_test, y_test, batch_size=None):
        """
        Evaluate model performance.
        
        Args:
            X_test: Test sequences
            y_test: Test targets
            batch_size: Batch size for evaluation
            
        Returns:
            dict: Evaluation metrics (mse, mae, rmse, per_ip_mae)
        """
        predictions = self.model.predict(X_test, batch_size=batch_size)

        # Inverse transform for meaningful metrics
        y_test_inverse = self.scaler.inverse_transform(y_test)
        predictions_inverse = self.scaler.inverse_transform(predictions)

        mse = mean_squared_error(y_test_inverse, predictions_inverse)
        mae = mean_absolute_error(y_test_inverse, predictions_inverse)
        rmse = np.sqrt(mse)

        # Per-IP MAE for detailed analysis
        per_ip_mae = np.mean(np.abs(y_test_inverse - predictions_inverse), axis=0)

        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'per_ip_mae': per_ip_mae
        }