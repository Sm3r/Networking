import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, BatchNormalization, Bidirectional
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error


class NetworkTrafficPredictor:
    """
    Improved RNN model with better architecture and handling of temporal patterns.
    """
    
    def __init__(self, sequence_length=20, lstm_units=128, dropout_rate=0.2, learning_rate=0.001, 
                 use_bidirectional=False):
        """
        Initialize the network traffic predictor.
        
        Args:
            sequence_length: Number of time steps to look back
            lstm_units: Number of units in LSTM layers
            dropout_rate: Dropout rate for regularization
            learning_rate: Initial learning rate
            use_bidirectional: Whether to use bidirectional LSTM
        """
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.use_bidirectional = use_bidirectional
        self.model = None
        self.scaler = MinMaxScaler()
        self.ip_to_index = {}
        self.index_to_ip = {}
        
    def prepare_sequences(self, aggregated_data, include_time_features=True):
        """
        Prepare sequences for time series prediction with temporal features.
        
        Args:
            aggregated_data: Aggregated traffic data DataFrame
            include_time_features: Whether to include time-based features
            
        Returns:
            tuple: (X, y, ip_columns, y_time_bins)
        """
        from datapreparation import prepare_sequences_with_time
        
        X, y, ip_columns, y_time_bins, scaler = prepare_sequences_with_time(
            aggregated_data, 
            self.sequence_length, 
            include_time_features
        )
        
        # Store the scaler
        self.scaler = scaler
        
        # Create IP mappings
        unique_ips = sorted(ip_columns)
        self.ip_to_index = {ip: idx for idx, ip in enumerate(unique_ips)}
        self.index_to_ip = {idx: ip for ip, idx in self.ip_to_index.items()}
        
        return X, y, ip_columns, y_time_bins
    
    def build_model(self, n_features, n_output_features):
        """
        Build an improved LSTM model with attention to temporal patterns.
        
        Args:
            n_features: Number of input features (IPs + time features)
            n_output_features: Number of output features (just IPs, no time)
        """
        self.model = Sequential([
            # First layer - bidirectional optional
            (Bidirectional(LSTM(self.lstm_units, return_sequences=True, 
                               input_shape=(self.sequence_length, n_features)))
             if self.use_bidirectional else
             LSTM(self.lstm_units, return_sequences=True, 
                  input_shape=(self.sequence_length, n_features))),
            BatchNormalization(),
            Dropout(self.dropout_rate),
            
            # Second LSTM layer
            LSTM(self.lstm_units // 2, return_sequences=False),
            BatchNormalization(),
            Dropout(self.dropout_rate),
            
            # Dense layers with residual-like connection
            Dense(self.lstm_units, activation='relu'),
            BatchNormalization(),
            Dropout(self.dropout_rate * 0.5),
            
            Dense(n_output_features * 2, activation='relu'),
            Dropout(self.dropout_rate * 0.5),
            
            # Output layer
            Dense(n_output_features, activation='relu')  # Use ReLU to ensure non-negative
        ])
        
        # Use Huber loss for robustness to outliers
        optimizer = Adam(learning_rate=self.learning_rate, clipnorm=1.0)
        
        self.model.compile(
            optimizer=optimizer,
            loss='huber',  # More robust to outliers than MSE
            metrics=['mae', 'mse']
        )
        
        return self.model
    
    def train(self, X, y, validation_split=0.15, epochs=100, batch_size=64):
        """
        Train the model with improved callbacks.
        
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
                patience=25,
                restore_best_weights=True,
                verbose=1,
                min_delta=1e-4
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=12,
                verbose=1,
                min_lr=1e-7,
                min_delta=1e-4
            ),
            ModelCheckpoint(
                'best_model.keras',
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            )
        ]

        print(f"\n{'='*60}")
        print(f"Training Configuration:")
        print(f"  Samples: {len(X)}")
        print(f"  Validation split: {validation_split}")
        print(f"  Batch size: {batch_size}")
        print(f"  Max epochs: {epochs}")
        print(f"  Input shape: {X.shape}")
        print(f"  Output shape: {y.shape}")
        print(f"{'='*60}\n")

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
        
        predictions = self.model.predict(X, batch_size=batch_size, verbose=0)
        predictions_scaled = self.scaler.inverse_transform(predictions)
        
        # Ensure all predictions are non-negative
        return np.maximum(predictions_scaled, 0)
    
    def evaluate_model(self, X_test, y_test, batch_size=None):
        """
        Evaluate model performance with detailed metrics.
        
        Args:
            X_test: Test sequences
            y_test: Test targets
            batch_size: Batch size for evaluation
            
        Returns:
            dict: Evaluation metrics
        """
        predictions = self.model.predict(X_test, batch_size=batch_size, verbose=0)

        # Inverse transform for meaningful metrics
        y_test_inverse = self.scaler.inverse_transform(y_test)
        predictions_inverse = self.scaler.inverse_transform(predictions)
        
        # Clip negatives
        predictions_inverse = np.maximum(predictions_inverse, 0)

        mse = mean_squared_error(y_test_inverse, predictions_inverse)
        mae = mean_absolute_error(y_test_inverse, predictions_inverse)
        rmse = np.sqrt(mse)

        # Per-IP metrics
        per_ip_mae = np.mean(np.abs(y_test_inverse - predictions_inverse), axis=0)
        per_ip_mse = np.mean((y_test_inverse - predictions_inverse) ** 2, axis=0)
        
        # Percentage error
        # Avoid division by zero
        non_zero_mask = y_test_inverse > 0
        mape = np.mean(np.abs((y_test_inverse[non_zero_mask] - predictions_inverse[non_zero_mask]) 
                              / y_test_inverse[non_zero_mask])) * 100 if non_zero_mask.any() else 0

        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'mape': mape,
            'per_ip_mae': per_ip_mae,
            'per_ip_mse': per_ip_mse
        }