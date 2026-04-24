import torch
import numpy as np
import joblib
from pathlib import Path
from torch.utils.data import DataLoader
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from data_loader import NetworkDataset
from network import LSTM
from constants import BIN_SIZE

DATA_DIR = Path(__file__).parent.parent / "data"

def evaluate_model():
    """
    Evaluate the LSTM model on the test set and print relevant metrics.
    """
    
    print("=" * 70)
    print("LSTM Network Traffic Prediction Model Evaluation")
    print("=" * 70)
    
    ### Load the Scaler and Test Dataset
    print("\nLoading scaler and test dataset...")
    scaler_path = DATA_DIR / "scaler.joblib"
    scaler = joblib.load(scaler_path)
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
    
    print("Running predictions on the test set...\n")
    
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
    print("SCALED DATA METRICS (Normalized Values)")
    print("=" * 70)
    
    scaled_mse = mean_squared_error(all_actuals, all_predictions)
    scaled_rmse = np.sqrt(scaled_mse)
    scaled_mae = mean_absolute_error(all_actuals, all_predictions)
    scaled_r2 = r2_score(all_actuals, all_predictions)
    
    print(f"Mean Squared Error (MSE):      {scaled_mse:.6f}")
    print(f"Root Mean Squared Error (RMSE): {scaled_rmse:.6f}")
    print(f"Mean Absolute Error (MAE):     {scaled_mae:.6f}")
    print(f"R² Score:                      {scaled_r2:.6f}")
    
    print("\n" + "=" * 70)
    print("REAL DATA METRICS (Actual Byte Values)")
    print("=" * 70)
    
    real_mse = mean_squared_error(real_actuals, real_predictions)
    real_rmse = np.sqrt(real_mse)
    real_mae = mean_absolute_error(real_actuals, real_predictions)
    real_r2 = r2_score(real_actuals, real_predictions)
    
    # Calculate MAPE (Mean Absolute Percentage Error)
    # Avoid division by zero by adding a small epsilon
    epsilon = 1e-8
    mape = np.mean(np.abs((real_actuals - real_predictions) / (np.abs(real_actuals) + epsilon))) * 100
    
    print(f"Mean Squared Error (MSE):      {real_mse:.2f} bytes²")
    print(f"Root Mean Squared Error (RMSE): {real_rmse:.2f} bytes")
    print(f"Mean Absolute Error (MAE):     {real_mae:.2f} bytes")
    print(f"Mean Absolute % Error (MAPE):  {mape:.2f}%")
    print(f"R² Score:                      {real_r2:.6f}")
    
    print("\n" + "=" * 70)
    print("ADDITIONAL STATISTICS")
    print("=" * 70)
    
    # Residuals analysis
    residuals = real_actuals - real_predictions
    print(f"\nResiduals (Actual - Predicted):")
    print(f"  Mean:                        {np.mean(residuals):.2f} bytes")
    print(f"  Std Dev:                     {np.std(residuals):.2f} bytes")
    print(f"  Min:                         {np.min(residuals):.2f} bytes")
    print(f"  Max:                         {np.max(residuals):.2f} bytes")
    
    # Actual data statistics
    print(f"\nActual Traffic Statistics:")
    print(f"  Mean:                        {np.mean(real_actuals):.2f} bytes per {BIN_SIZE}s bin")
    print(f"  Std Dev:                     {np.std(real_actuals):.2f} bytes")
    print(f"  Min:                         {np.min(real_actuals):.2f} bytes")
    print(f"  Max:                         {np.max(real_actuals):.2f} bytes")
    
    # Predicted data statistics
    print(f"\nPredicted Traffic Statistics:")
    print(f"  Mean:                        {np.mean(real_predictions):.2f} bytes per {BIN_SIZE}s bin")
    print(f"  Std Dev:                     {np.std(real_predictions):.2f} bytes")
    print(f"  Min:                         {np.min(real_predictions):.2f} bytes")
    print(f"  Max:                         {np.max(real_predictions):.2f} bytes")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    evaluate_model()
