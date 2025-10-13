import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
from datapreparation import load_and_prepare_data, bin_timestamps_and_aggregate_traffic

class NetworkTrafficPredictor:
    """
    RNN model with GRU for predicting network traffic patterns
    """
    
    def __init__(self, sequence_length=10, gru_units=64, dropout_rate=0.2):
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
        
        return np.array(X), np.array(y), pivot_data.columns.tolist()
    
    def build_model(self, n_features):
        """
        Build the GRU model
        
        Args:
            n_features (int): Number of features (IPs)
        """
        self.model = Sequential([
            GRU(self.gru_units, 
                return_sequences=True, 
                input_shape=(self.sequence_length, n_features)),
            Dropout(self.dropout_rate),
            
            GRU(self.gru_units // 2, 
                return_sequences=False),
            Dropout(self.dropout_rate),
            
            Dense(n_features * 2, activation='relu'),
            Dropout(self.dropout_rate),
            
            Dense(n_features, activation='linear')
        ])
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
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
        
        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            shuffle=True
        )
        
        return history
    
    def predict(self, X):
        """
        Make predictions
        
        Args:
            X (np.array): Input sequences
            
        Returns:
            np.array: Predictions
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        predictions = self.model.predict(X)
        return self.scaler.inverse_transform(predictions)
    
    def evaluate_model(self, X_test, y_test):
        """
        Evaluate model performance
        
        Args:
            X_test (np.array): Test sequences
            y_test (np.array): Test targets
            
        Returns:
            dict: Evaluation metrics
        """
        predictions = self.model.predict(X_test)
        
        # Inverse transform for meaningful metrics
        y_test_inverse = self.scaler.inverse_transform(y_test)
        predictions_inverse = self.scaler.inverse_transform(predictions)
        
        mse = mean_squared_error(y_test_inverse, predictions_inverse)
        mae = mean_absolute_error(y_test_inverse, predictions_inverse)
        rmse = np.sqrt(mse)
        
        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse
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
        plt.show()

def main():
    """
    Main function to run the network traffic prediction pipeline
    """
    print("Loading and preparing data...")
    csv_file_path = '../dataset.csv'
    
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
    X, y, ip_columns = predictor.prepare_sequences(aggregated_data)
    
    print(f"Sequence data shape: X={X.shape}, y={y.shape}")
    print(f"Number of features (IPs): {len(ip_columns)}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )
    
    print(f"Training data: X_train={X_train.shape}, y_train={y_train.shape}")
    print(f"Test data: X_test={X_test.shape}, y_test={y_test.shape}")
    
    # Build and train model
    print("\nBuilding GRU model...")
    predictor.build_model(n_features=len(ip_columns))
    print(predictor.model.summary())
    
    print("\nTraining model...")
    history = predictor.train(X_train, y_train, epochs=30, batch_size=32)
    
    # Evaluate model
    print("\nEvaluating model...")
    metrics = predictor.evaluate_model(X_test, y_test)
    print(f"Test Metrics:")
    print(f"  MSE: {metrics['mse']:.4f}")
    print(f"  MAE: {metrics['mae']:.4f}")
    print(f"  RMSE: {metrics['rmse']:.4f}")
    
    # Plot training history
    predictor.plot_training_history(history)
    
    # Make sample predictions
    print("\nMaking sample predictions...")
    sample_predictions = predictor.predict(X_test[:5])
    print(f"Sample prediction shape: {sample_predictions.shape}")

if __name__ == "__main__":
    main()