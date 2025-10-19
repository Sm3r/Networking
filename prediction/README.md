# Network Traffic Prediction

A deep learning model for predicting network traffic patterns using GRU (Gated Recurrent Unit) neural networks.

## Quick Start

### Basic Training
```bash
python3 prediction/train.py
```

### Training with Arguments Options
```bash
python3 prediction/train.py \
    --batch-size 128 \
    --predict-batch-size 128 \
    --epochs 200 \
    --sequence-length 15 \
    --gru-units 128 \
    --dropout-rate 0.3
```

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--batch-size`, `-b` | 64 | Training batch size |
| `--predict-batch-size` | 32 | Batch size for prediction/evaluation |
| `--epochs`, `-e` | 100 | Number of training epochs |
| `--sequence-length` | 10 | Time steps to look back for prediction |
| `--gru-units` | 64 | Number of units in GRU layers |
| `--dropout-rate` | 0.2 | Dropout rate for regularization |
| `--bin-size` | 1.0 | Time bin size for aggregating traffic |
| `--csv-path` | ../dataset.csv | Path to the CSV dataset |