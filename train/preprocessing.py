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

def create_sliding_windows(data_array, seq_length):
    xs, ys = [], []
    for i in range(len(data_array) - seq_length):
        xs.append(data_array[i : i + seq_length])
        ys.append(data_array[i + seq_length])
    return xs, ys

def prepare_network_data(data_dir, force_rebuild=False, window_size=30):
    path = Path(data_dir)

    train_file = path / "train.npz"
    test_file = path / "test.npz"
    scaler_file = path / "scaler.joblib"

    if not force_rebuild and train_file.exists() and test_file.exists() and scaler_file.exists():
        print("Prepared data found! Skipping Pandas processing...")
        return

    # Look for CSV files in both root and subdirectories
    datasets = sorted(glob.glob(str(path / "*.csv")))
    datasets += sorted(glob.glob(str(path / "*/*.csv")))
    
    if not datasets:
        raise ValueError(f"No CSV files found in {path} or its subdirectories!")
    
    print(f"Found {len(datasets)} CSV files to process")
    
    train_chunks = []
    test_chunks = []

    for file in datasets:
        df = pd.read_csv(file)
        
        ### Cleaning
        df["virtual_timestamp"] = pd.to_numeric(df["virtual_timestamp"], errors="coerce")
        df = df[df["virtual_timestamp"] > 0.0]

        if df.empty:
            continue

        COLUMNS = ["virtual_timestamp", "length"]
        df = df[[c for c in COLUMNS if c in df.columns]]

        df = df[df["virtual_timestamp"] < df["virtual_timestamp"].max()]   
            
        ### Binning
        bins = np.arange(df['virtual_timestamp'].min(), df['virtual_timestamp'].max() + BIN_SIZE, BIN_SIZE)
        df['bin'] = pd.cut(df['virtual_timestamp'], bins=bins, labels=bins[:-1], right=False, include_lowest=True)
        binned_data = df.groupby('bin', observed=False)['length'].sum().fillna(0).reset_index()

        ### Splitting
        split = 0.8
        split_index = int(len(binned_data) * split)
        
        train_chunk = binned_data.iloc[:split_index][['length']].values
        test_chunk = binned_data.iloc[split_index:][['length']].values
        
        if len(train_chunk) > window_size:
            train_chunks.append(train_chunk)
        if len(test_chunk) > window_size:
            test_chunks.append(test_chunk)

    ### Creating global scaler
    global_train_data = np.concatenate(train_chunks)
    scaler = MinMaxScaler()
    scaler.fit(global_train_data)

    ### Scaling and creating sliding windows for all chunks
    X_train_all, y_train_all = [], []
    X_test_all, y_test_all = [], []

    for chunk in train_chunks:
        scaled_chunk = scaler.transform(chunk)
        X, y = create_sliding_windows(scaled_chunk, window_size)
        X_train_all.extend(X)
        y_train_all.extend(y)

    for chunk in test_chunks:
        scaled_chunk = scaler.transform(chunk)
        X, y = create_sliding_windows(scaled_chunk, window_size)
        X_test_all.extend(X)
        y_test_all.extend(y)

    ### Saving the cleaned data and the scaler
    np.savez(train_file, X=np.array(X_train_all, dtype=np.float32), y=np.array(y_train_all, dtype=np.float32))
    np.savez(test_file, X=np.array(X_test_all, dtype=np.float32), y=np.array(y_test_all, dtype=np.float32))
    joblib.dump(scaler, scaler_file)

    print("Data preparation completed and saved!")

if __name__ == "__main__":
    prepare_network_data(data_dir=Path(__file__).parent.parent / "data", window_size=20, force_rebuild=True)