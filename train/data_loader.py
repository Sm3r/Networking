import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path

class NetworkDataset(Dataset):

    def __init__(self, data_dir, training=True):
        path = Path(data_dir)
        
        if training:
            data = np.load(path / "train.npz")
        else:
            data = np.load(path / "test.npz")
            
        self.X = torch.tensor(data['X'], dtype=torch.float32)
        self.y = torch.tensor(data['y'], dtype=torch.float32)
    

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
