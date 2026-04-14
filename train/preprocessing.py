import glob
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib

try:
    from train.constants import BIN_SIZE
except ImportError:
    from constants import BIN_SIZE

def prepare_network_data(data_dir, force_rebuild=False):
    path = Path(data_dir)
    
    train_file = path / "train.npy"
    test_file = path / "test.npy"
    scaler_file = path / "scaler.joblib"
    
    if not force_rebuild and train_file.exists() and test_file.exists() and scaler_file.exists():
        return

    datasets = sorted(glob.glob(str(path / "dataset*.csv")))

    ### Merge datasets with offsetting virtual_timestamp to ensure continuity
    df_list = []
    current_offset = 0.0

    for file in datasets:
        temp_df = pd.read_csv(file)
        temp_df['virtual_timestamp'] += current_offset
        df_list.append(temp_df)
        current_offset = temp_df['virtual_timestamp'].max()

    traffic_data = pd.concat(df_list, ignore_index=True)

    ### Perform cleaning
    traffic_data["virtual_timestamp"] = pd.to_numeric(traffic_data["virtual_timestamp"], errors="coerce")
    traffic_data = traffic_data[traffic_data["virtual_timestamp"] > 0.0]

    COLUMNS = ["virtual_timestamp", "length"]
    traffic_data = traffic_data[[c for c in COLUMNS if c in traffic_data.columns]]

    ### Binning
    bins = np.arange(traffic_data['virtual_timestamp'].min(), traffic_data['virtual_timestamp'].max() + BIN_SIZE, BIN_SIZE)

    traffic_data['bin'] = pd.cut(
        traffic_data['virtual_timestamp'], 
        bins=bins, 
        labels=bins[:-1], 
        right=False,
        include_lowest=True
    )
    binned_data = traffic_data.groupby('bin', observed=False)['length'].sum().fillna(0).reset_index()

    ### Thresholding
    threshold = 18000
    binned_data['length'] = binned_data['length'].clip(upper=threshold)

    ### Splitting
    split = 0.8
    split_index = int(len(binned_data) * split)
    train_data = binned_data.iloc[:split_index]
    test_data = binned_data.iloc[split_index:]

    ### Scaling
    scaler = MinMaxScaler()
    train_data_scaled = scaler.fit_transform(train_data[['length']].values)
    test_data_scaled = scaler.transform(test_data[['length']].values)

    ### Saving the cleaned data and the scaler
    np.save(train_file, train_data_scaled)
    np.save(test_file, test_data_scaled)
    joblib.dump(scaler, scaler_file)

    print("Data preparation completed and saved!")

if __name__ == "__main__":
    prepare_network_data(data_dir=Path(__file__).parent.parent / "data", force_rebuild=True)
