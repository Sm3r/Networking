import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
import sys

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} dataset.csv")
    exit(0)

filename = Path(sys.argv[1])

DATA_FILE = Path(__file__).parent.parent / filename
SIGNAL_FILE = Path(__file__).parent.parent / "resources" / "traffic_signal.csv"
BIN = "1s"
CHUNKSIZE = 100_000


def plot_traffic():
    overall = defaultdict(int)

    for chunk in pd.read_csv(DATA_FILE, usecols=["time_of_day", "length"], chunksize=CHUNKSIZE):
        chunk["time_of_day"] = pd.to_numeric(chunk["time_of_day"], errors="coerce")
        chunk = chunk.dropna(subset=["time_of_day"])
        chunk["time"] = pd.to_datetime(chunk["time_of_day"], unit="s").dt.floor(BIN)
        for t, grp in chunk.groupby("time"):
            overall[t] += grp["length"].sum()

    fig, ax = plt.subplots(figsize=(12, 4))
    pd.Series(overall).sort_index().plot(ax=ax)
    ax.set_title("Overall traffic over time")
    ax.set_xlabel("Time of Day (HH:MM:SS)")
    ax.set_ylabel(f"Bytes / {BIN}")

    # Format x-axis as time of day (HH:MM:SS)
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))

    out_filename = filename.stem + ".png"
    out = Path(__file__).parent.parent / "plots" / out_filename
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved to {out}")


plot_traffic()
