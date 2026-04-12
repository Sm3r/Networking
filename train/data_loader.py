import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path

class NetworkDataset(Dataset):
    def __init__(self, data_dir, seq_length=30, training=True):

        self.seq_length = seq_length
        path = Path(data_dir)
        
        if training:
            data = np.load(path / "train.npy")
        else:
            data = np.load(path / "test.npy")
            
        ### Compute all sliding windows (X) and targets (y)
        xs, ys = [], []
        for i in range(len(data) - seq_length):
            # Grab 'seq_length' amount of data for the input
            xs.append(data[i : i + seq_length])
            # Grab the very next data point as the target
            ys.append(data[i + seq_length])
            
        ### Convert everything into PyTorch Tensors

        # Shape: (Number of Sequences, Seq_Length, Features)
        self.X = torch.tensor(np.array(xs), dtype=torch.float32)

        # Shape: (Number of Sequences, Features)
        self.y = torch.tensor(np.array(ys), dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]