import pandas as pd
import glob
from pathlib import Path
from tqdm import tqdm

COLUMNS_TO_DROP = ["virtual_timestamp", "time_of_day", "protocols", "src_port", "dst_port"]
MIN_TIMESTAMP = pd.Timestamp("2026-01-01").timestamp()

project_root = Path(__file__).parent.parent
csv_files = sorted(glob.glob(f"{project_root}/data/simple-*.csv"))
output_file = project_root / "data" / "clean_dataset.csv"
output_file.unlink(missing_ok=True)

for i, f in enumerate(tqdm(csv_files)):
    df = pd.read_csv(f)
    df = df[df['protocols'].str.startswith('sll:ethertype:ip:tcp')]
    df = df.drop(columns=[c for c in COLUMNS_TO_DROP if c in df.columns])
    df = df[df['real_timestamp'] >= MIN_TIMESTAMP]
    df.to_csv(output_file, mode='a', index=False, header=(i == 0))
