import torch
import numpy as np
import matplotlib.pyplot as plt
import joblib
from pathlib import Path
from torch.utils.data import DataLoader

from data_loader import NetworkDataset
from network import LSTM
from constants import BIN_SIZE

DATA_DIR = Path(__file__).parent.parent / "data"

def plot_test_results():

    ### Load the Scaler and Test Dataset
    scaler_path = DATA_DIR / "scaler.joblib"
    scaler = joblib.load(scaler_path)
    test_dataset = NetworkDataset(data_dir=DATA_DIR, training=False)
    test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

    ### Load model
    model = LSTM()
    model.load_state_dict(torch.load("model_LSTM.pth"))
    model.eval()

    all_predictions = []
    all_actuals = []

    print("Running predictions on the test set...")

    ### Predict on test set
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            predictions = model(batch_x)

            all_predictions.extend(predictions.numpy())
            all_actuals.extend(batch_y.numpy())

    ### Convert lists to arrays an inverse transform to get real byte values
    all_predictions = np.array(all_predictions)
    all_actuals = np.array(all_actuals)
    real_predictions = scaler.inverse_transform(all_predictions)
    real_actuals = scaler.inverse_transform(all_actuals)

    ### Plotting the results
    print("Generating plot...")
    plt.figure(figsize=(15, 6))

    plt.plot(real_actuals, label='Actual Traffic (Bytes)', color='blue', alpha=0.6, linewidth=2)
    plt.plot(real_predictions, label='Predicted Traffic (Bytes)', color='red', alpha=0.9, linestyle='--', linewidth=1.5)

    plt.title('Network Byte Load: Actual vs. Predicted', fontsize=16)
    plt.xlabel("Virtual Simulation Timestamp")
    plt.ylabel(f"Bytes per {BIN_SIZE} Timestamps Bin")

    plt.legend(loc='upper right', fontsize=12)
    plt.grid(True, linestyle=':', alpha=0.7)

    ### Zoom
    #plt.xlim(0, 500)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_test_results()
