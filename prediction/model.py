import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, TerminateOnNaN
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic
import argparse

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

            Dense(n_features, activation='linear')
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
        
        # Callbacks to help training stability and generalization
        callbacks = [
            TerminateOnNaN(),
            EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=4, verbose=1),
            ModelCheckpoint('best_model.keras', monitor='val_loss', save_best_only=True, verbose=1)
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
            np.array: Predictions
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # default batch_size behaviour is left to Keras if None
        predictions = self.model.predict(X, batch_size=batch_size)
        return self.scaler.inverse_transform(predictions)
    
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
    
    def plot_training_history(self, history):
        """
        Plot training history
        
        Args:
            history: Training history from model.fit()
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        # Plot loss
        ax1.plot(history.history['loss'], label='Training Loss')
        ax1.plot(history.history['val_loss'], label='Validation Loss')
        ax1.set_title('Model Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        
        # Plot MAE
        ax2.plot(history.history['mae'], label='Training MAE')
        ax2.plot(history.history['val_mae'], label='Validation MAE')
        ax2.set_title('Model MAE')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('MAE')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig('training_history.png', dpi=150)
        plt.show()

    def plot_predictions(self, X_test, y_test, ip_columns, y_time_bins=None, ip_index=0, n_points=200):
        """
        Plot predicted vs actual for a selected IP (by column index) and aggregated traffic.

        Args:
            X_test, y_test: test arrays (already in original feature space before inverse?)
            ip_columns: list of IP column names (order matches model output)
            y_time_bins: optional array of time bins corresponding to y_test
            ip_index: integer index of IP column to plot
            n_points: max number of points to plot
        """
        # Make predictions and inverse-transform
        preds = self.model.predict(X_test)
        preds_inv = self.scaler.inverse_transform(preds)
        y_inv = self.scaler.inverse_transform(y_test)

        # Clip to n_points
        n = min(len(y_inv), n_points)

        # Single-IP plot
        ip_idx = int(ip_index)
        ip_name = ip_columns[ip_idx] if ip_idx < len(ip_columns) else f'ip_{ip_idx}'

        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        axes[0].plot(range(n), y_inv[:n, ip_idx], label='Actual')
        axes[0].plot(range(n), preds_inv[:n, ip_idx], label='Predicted', alpha=0.8)
        axes[0].set_title(f'IP {ip_name} - Actual vs Predicted')
        axes[0].set_ylabel('Traffic Size')
        axes[0].legend()

        # Aggregated traffic plot (sum across IPs)
        axes[1].plot(range(n), y_inv[:n].sum(axis=1), label='Actual (sum)')
        axes[1].plot(range(n), preds_inv[:n].sum(axis=1), label='Predicted (sum)', alpha=0.8)
        axes[1].set_title('Aggregated Traffic - Actual vs Predicted')
        axes[1].set_xlabel('Test sample index')
        axes[1].set_ylabel('Total Traffic')
        axes[1].legend()

        plt.tight_layout()
        plt.savefig('predictions_sample.png', dpi=150)
        plt.show()

def main():
    csv_file_path = 'dataset.csv'
    
    parser = argparse.ArgumentParser(description='Train/evaluate network traffic GRU model')
    parser.add_argument('--batch-size', '-b', type=int, default=64, help='Training batch size')
    parser.add_argument('--predict-batch-size', type=int, default=32, help='Batch size used for predict/evaluate')
    parser.add_argument('--epochs', '-e', type=int, default=100, help='Number of training epochs')
    args = parser.parse_args()

    # Load and prepare data
    data = load_and_prepare_data(csv_file_path)
    aggregated_data = bin_timestamps_and_aggregate_traffic(data, bin_size=1.0)
    
    print(f"Aggregated data shape: {aggregated_data.shape}")
    print(f"Unique IPs: {aggregated_data['ip'].nunique()}")
    print(f"Time range: {aggregated_data['time_bin'].min():.1f} - {aggregated_data['time_bin'].max():.1f}")
    
    # Initialize predictor
    predictor = NetworkTrafficPredictor(sequence_length=10, gru_units=64, dropout_rate=0.2)
    
    # Prepare sequences
    print("\nPreparing sequences for training...")
    X, y, ip_columns, y_time_bins = predictor.prepare_sequences(aggregated_data)
    
    print(f"Sequence data shape: X={X.shape}, y={y.shape}")
    print(f"Number of features (IPs): {len(ip_columns)}")
    
    # Time-based split: use the first 80% of time-ordered samples for training
    n_samples = X.shape[0]
    split_idx = int(n_samples * 0.8)

    X_train = X[:split_idx]
    y_train = y[:split_idx]
    X_test = X[split_idx:]
    y_test = y[split_idx:]

    split_time = y_time_bins[split_idx] if len(y_time_bins) > split_idx else None

    print(f"Training data: X_train={X_train.shape}, y_train={y_train.shape}")
    print(f"Test data: X_test={X_test.shape}, y_test={y_test.shape}")
    if split_time is not None:
        print(f"Time-based split boundary (first test time_bin): {split_time}")
    
    # Build and train model
    print("\nBuilding GRU model...")
    predictor.build_model(n_features=len(ip_columns))
    print(predictor.model.summary())
    
    print("\nTraining model...")
    history = predictor.train(X_train, y_train, epochs=args.epochs, batch_size=args.batch_size)
    
    # Evaluate model
    print("\nEvaluating model...")
    # If a best_model checkpoint exists, load it for evaluation
    try:
        # Load the full model saved in Keras native format (avoids HDF5 legacy warning)
        predictor.model = tf.keras.models.load_model('best_model.keras')
    except Exception:
        # fallback: if only weights (or older .h5) exist, try loading weights
        try:
            predictor.model.load_weights('best_model.h5')
        except Exception:
            pass

    metrics = predictor.evaluate_model(X_test, y_test, batch_size=args.predict_batch_size)
    print(f"Test Metrics:")
    print(f"  MSE: {metrics['mse']:.4f}")
    print(f"  MAE: {metrics['mae']:.4f}")
    print(f"  RMSE: {metrics['rmse']:.4f}")
    # Print top IPs by per-IP MAE
    if 'per_ip_mae' in metrics:
        per_ip = metrics['per_ip_mae']
        # sort descending by error
        idxs = np.argsort(per_ip)[::-1]
        top_k = min(10, len(per_ip))
        print("\nTop IPs by MAE:")
        for i in range(top_k):
            ip = ip_columns[idxs[i]] if idxs[i] < len(ip_columns) else f'ip_{idxs[i]}'
            print(f"  {i+1}. {ip}: MAE={per_ip[idxs[i]]:.4f}")
    
    # Plot training history
    predictor.plot_training_history(history)
    
    # Make sample predictions
    print("\nMaking sample predictions...")
    # Make sample predictions (use full test set but control batch size for progress)
    sample_predictions = predictor.predict(X_test, batch_size=args.predict_batch_size)
    print(f"Sample prediction shape (full test set): {sample_predictions.shape}")

    # Plot predictions for a sample IP (first IP) and aggregated traffic
    predictor.plot_predictions(X_test, y_test, ip_columns, y_time_bins=y_time_bins, ip_index=0, n_points=300)

if __name__ == "__main__":
    main()