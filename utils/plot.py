import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
import sys
import numpy as np

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} dataset.csv")
    exit(0)

filename = Path(sys.argv[1])

DATA_FILE = Path(__file__).parent.parent / filename
BIN = 1.0
CHUNKSIZE = 100_000


def plot_traffic():
    overall = defaultdict(int)

    for chunk in pd.read_csv(DATA_FILE, usecols=["virtual_timestamp", "length"], chunksize=CHUNKSIZE):
        chunk["virtual_timestamp"] = pd.to_numeric(chunk["virtual_timestamp"], errors="coerce")
        chunk = chunk.dropna(subset=["virtual_timestamp"])
        chunk["time_bin"] = np.floor(chunk["virtual_timestamp"] / BIN) * BIN
        for t, grp in chunk.groupby("time_bin"):
            overall[t] += grp["length"].sum()

    series = pd.Series(overall).sort_index()
    
    # Remove last timestamp
    series = series.drop(series.index[-1])
    
    fig, ax = plt.subplots(figsize=(12, 4))
    series.plot(ax=ax)
    ax.set_title("Overall traffic over time")
    ax.set_xlabel("Virtual Time (seconds)")
    ax.set_ylabel(f"Bytes / {BIN}s")

    out_filename = filename.stem + ".png"
    out = Path(__file__).parent.parent / "plots" / out_filename
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved to {out}")


plot_traffic()
