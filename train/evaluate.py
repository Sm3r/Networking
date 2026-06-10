import torch
import numpy as np
import joblib
from pathlib import Path
from torch.utils.data import DataLoader
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from data_loader import NetworkDataset
from network import LSTM
from constants import BIN_SIZE, WINDOW_SIZE

import argparse
import pandas as pd
from preprocessing import create_sliding_windows

DATA_DIR = Path(__file__).parent.parent / "data"

def evaluate_model(csv_path=None):
    """
    Evaluate the LSTM model on the test set, or a single CSV if provided, and print relevant metrics.
    """
    
    print("=" * 70)
    print("LSTM Network Traffic Prediction Model Evaluation")
    print("=" * 70)
    
    ### Load the Scaler
    print("\nLoading scaler...")
    scaler_path = DATA_DIR / "scaler.joblib"
    scaler = joblib.load(scaler_path)
    
    if csv_path:
        print(f"Loading and processing single CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        df["virtual_timestamp"] = pd.to_numeric(df["virtual_timestamp"], errors="coerce")
        df = df[df["virtual_timestamp"] > 0.0]
        if df.empty:
            print("CSV is empty or invalid.")
            return
            
        COLUMNS = ["virtual_timestamp", "length"]
        df = df[[c for c in COLUMNS if c in df.columns]]
        df = df[df["virtual_timestamp"] < df["virtual_timestamp"].max()]
        
        bins = np.arange(df['virtual_timestamp'].min(), df['virtual_timestamp'].max() + BIN_SIZE, BIN_SIZE)
        df['bin'] = pd.cut(df['virtual_timestamp'], bins=bins, labels=bins[:-1], right=False, include_lowest=True)
        binned_data = df.groupby('bin', observed=False)['length'].sum().fillna(0).reset_index()
        
        chunk = binned_data[['length']].values
        scaled_chunk = scaler.transform(chunk)
        
        X_test, y_test = create_sliding_windows(scaled_chunk, WINDOW_SIZE)
        if len(X_test) == 0:
            print("Not enough data in CSV to create windows.")
            return
            
        class SingleCSVDataset(torch.utils.data.Dataset):
            def __init__(self, X, y):
                self.X = torch.tensor(np.array(X, dtype=np.float32), dtype=torch.float32)
                self.y = torch.tensor(np.array(y, dtype=np.float32), dtype=torch.float32)
            def __len__(self):
                return len(self.X)
            def __getitem__(self, idx):
                return self.X[idx], self.y[idx]
                
        test_dataset = SingleCSVDataset(X_test, y_test)
        test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)
    else:
        print("Loading test dataset...")
        test_dataset = NetworkDataset(data_dir=DATA_DIR, training=False)
        test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)
    
    print(f"Test set size: {len(test_dataset)} samples")
    
    ### Load model
    print("Loading model...")
    model = LSTM()
    model.load_state_dict(torch.load("model_LSTM.pth", map_location=torch.device('cpu')))
    model.eval()
    
    all_predictions = []
    all_actuals = []
    
    print("Running predictions on the set...\n")
    
    ### Predict on test set
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            predictions = model(batch_x)
            all_predictions.extend(predictions.numpy())
            all_actuals.extend(batch_y.numpy())
    
    ### Convert lists to arrays and inverse transform to get real byte values
    all_predictions = np.array(all_predictions).flatten()
    all_actuals = np.array(all_actuals).flatten()
    real_predictions = scaler.inverse_transform(all_predictions.reshape(-1, 1)).flatten()
    real_actuals = scaler.inverse_transform(all_actuals.reshape(-1, 1)).flatten()
    
    ### Calculate metrics
    print("=" * 70)
    print("PERFORMANCE METRICS (Normalized Values)")
    print("=" * 70)
    
    scaled_mse = mean_squared_error(all_actuals, all_predictions)
    scaled_rmse = np.sqrt(scaled_mse)
    scaled_mae = mean_absolute_error(all_actuals, all_predictions)
    scaled_r2 = r2_score(all_actuals, all_predictions)
    
    print(f"Mean Squared Error (MSE):      {scaled_mse:.6f}")
    print(f"Root Mean Squared Error (RMSE): {scaled_rmse:.6f}")
    print(f"Mean Absolute Error (MAE):     {scaled_mae:.6f}")
    print(f"R² Score:                      {scaled_r2:.6f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate LSTM model")
    parser.add_argument("csv", type=str, nargs="?", help="Path to a single CSV simulation file to evaluate", default=None)
    args = parser.parse_args()
    
    csv_file = None
    if args.csv:
        clean_path = args.csv.lstrip("/")
        csv_file = Path(__file__).parent.parent / clean_path
        
    evaluate_model(csv_path=csv_file)
