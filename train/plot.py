import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

DATA_FILE = Path(__file__).parent.parent / "test.csv"
SIGNAL_FILE = Path(__file__).parent.parent / "resources" / "traffic_signal.csv"
BIN = "1s"
CHUNKSIZE = 100_000


def plot_traffic():
    overall = defaultdict(int)

    for chunk in pd.read_csv(DATA_FILE, usecols=["real_timestamp", "length"], chunksize=CHUNKSIZE):
        chunk["real_timestamp"] = pd.to_numeric(chunk["real_timestamp"], errors="coerce")
        chunk = chunk.dropna(subset=["real_timestamp"])
        chunk["time"] = pd.to_datetime(chunk["real_timestamp"], unit="s").dt.floor(BIN)
        for t, grp in chunk.groupby("time"):
            overall[t] += grp["length"].sum()

    fig, ax = plt.subplots(figsize=(12, 4))
    pd.Series(overall).sort_index().plot(ax=ax)
    ax.set_title("Overall traffic over time")
    ax.set_ylabel(f"Bytes / {BIN}")

    out = Path(__file__).parent.parent / "data" / "traffic.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved to {out}")


plot_traffic()
