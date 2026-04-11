import pandas as pd
from pathlib import Path
import sys

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} dataset.csv")
    exit(0)

filename = Path(sys.argv[1])

COLUMNS_TO_DROP = ["virtual_timestamp", "real_timestamp", "protocols", "src_port", "dst_port"]

project_root = Path(__file__).parent.parent
input_file = project_root / filename
output_file = project_root / "data" / "clean" / f"clean-{filename.name}"
output_file.unlink(missing_ok=True)

df = pd.read_csv(input_file)
df["virtual_timestamp"] = pd.to_numeric(df["virtual_timestamp"], errors="coerce")
df = df[df["virtual_timestamp"] > 0.0]
df = df[df['protocols'].str.startswith('sll:ethertype:ip:tcp', na=False)]
df = df.drop(columns=[c for c in COLUMNS_TO_DROP if c in df.columns])
df.to_csv(output_file, mode='a', index=False, header=True)

print(f"File saved to {output_file}")
