import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, TerminateOnNaN
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error


class NetworkTrafficPredictor:
    """
    RNN model with GRU for predicting network traffic patterns
    """
    
    def __init__(self, sequence_length=12, gru_units=128, dropout_rate=0.25, l2_reg=1e-4):
        """
        Initialize the network traffic predictor
        
        Args:
            sequence_length (int): Number of time steps to look back for prediction
            gru_units (int): Number of units in GRU layer
            dropout_rate (float): Dropout rate for regularization
        """
        self.sequence_length = sequence_length
        self.gru_units = gru_units
        self.dropout_rate = dropout_rate
        self.l2_reg = l2_reg
        self.model = None
        self.scaler = MinMaxScaler()
        self.label_encoder = LabelEncoder()
        self.ip_to_index = {}
        self.index_to_ip = {}
        
    def prepare_sequences(self, aggregated_data):
        """
        Prepare sequences for time series prediction
        
        Args:
            aggregated_data (pd.DataFrame): Aggregated traffic data
            
        Returns:
            tuple: (X, y, ip_mapping) where X is sequences, y is targets
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
        
        # Create sequences. Note: y corresponds to the time bin at index i
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            y.append(scaled_data[i])

        # The time bins corresponding to each y (target) start at position sequence_length
        y_time_bins = pivot_data.index.values[self.sequence_length:]

        return np.array(X), np.array(y), pivot_data.columns.tolist(), y_time_bins
    
    def build_model(self, n_features):
        """
        Build the GRU model
        
        Args:
            n_features (int): Number of features (IPs)
        """
        # Deeper GRU stack with an additional layer, batch norm, and L2 regularization
        from tensorflow.keras.regularizers import l2
        self.model = Sequential([
            GRU(self.gru_units,
                return_sequences=True,
                kernel_regularizer=l2(self.l2_reg),
                input_shape=(self.sequence_length, n_features)),
            BatchNormalization(),
            Dropout(self.dropout_rate),

            GRU(self.gru_units,
                return_sequences=True,
                kernel_regularizer=l2(self.l2_reg)),
            BatchNormalization(),
            Dropout(self.dropout_rate),

            GRU(self.gru_units // 2,
                return_sequences=False,
                kernel_regularizer=l2(self.l2_reg)),
            BatchNormalization(),
            Dropout(self.dropout_rate),

            Dense(max(64, n_features * 4), activation='relu', kernel_regularizer=l2(self.l2_reg)),
            Dropout(self.dropout_rate),

            Dense(n_features, activation='relu')
        ])
        
        # Use gradient clipping to stabilize training
        optimizer = Adam(learning_rate=0.0005, clipnorm=1.0)
        self.model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae']
        )
        
        return self.model
    
    def train(self, X, y, validation_split=0.2, epochs=50, batch_size=32):
        """
        Train the model
        
        Args:
            X (np.array): Input sequences
            y (np.array): Target values
            validation_split (float): Fraction of data for validation
            epochs (int): Number of training epochs
            batch_size (int): Batch size for training
            
        Returns:
            History: Training history
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        # More aggressive callbacks for intensive training
        from tensorflow.keras.callbacks import LearningRateScheduler
        
        def scheduler(epoch, lr):
            if epoch < 50:
                return lr
            elif epoch < 100:
                return lr * 0.8
            elif epoch < 150:
                return lr * 0.6
            else:
                return lr * 0.4
        
        callbacks = [
            TerminateOnNaN(),
            EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, min_delta=1e-6),
            ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=8, verbose=1, min_lr=1e-7),
            LearningRateScheduler(scheduler, verbose=1),
            ModelCheckpoint('best_model.keras', monitor='val_loss', save_best_only=True, verbose=1, save_weights_only=False)
        ]

        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            shuffle=False,
            callbacks=callbacks
        )
        
        return history
    
    def predict(self, X, batch_size=None):
        """
        Make predictions
        
        Args:
            X (np.array): Input sequences
            
        Returns:
            np.array: Predictions (guaranteed to be non-negative)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # default batch_size behaviour is left to Keras if None
        predictions = self.model.predict(X, batch_size=batch_size)
        predictions_scaled = self.scaler.inverse_transform(predictions)
        
        # Ensure all predictions are non-negative (traffic cannot be negative)
        return np.maximum(predictions_scaled, 0)
    
    def evaluate_model(self, X_test, y_test, batch_size=None):
        """
        Evaluate model performance
        
        Args:
            X_test (np.array): Test sequences
            y_test (np.array): Test targets
            
        Returns:
            dict: Evaluation metrics
        """
        predictions = self.model.predict(X_test, batch_size=batch_size)

        # Inverse transform for meaningful metrics
        y_test_inverse = self.scaler.inverse_transform(y_test)
        predictions_inverse = self.scaler.inverse_transform(predictions)

        mse = mean_squared_error(y_test_inverse, predictions_inverse)
        mae = mean_absolute_error(y_test_inverse, predictions_inverse)
        rmse = np.sqrt(mse)

        # Per-IP MAE to help diagnose which IPs are poorly predicted
        per_ip_mae = np.mean(np.abs(y_test_inverse - predictions_inverse), axis=0)

        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'per_ip_mae': per_ip_mae
        }