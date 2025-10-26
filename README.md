# Networking

Project for the University of Trento course of Virtualized network (Networking 2nd module).

## Description

This is a **Network Traffic Simulation and Prediction System** that combines **Software-Defined Networking (SDN)** with **Machine Learning**. The system creates virtual networks using Mininet, generates realistic traffic patterns, captures all network packets, and uses an LSTM (Long Short-Term Memory) neural network to predict future traffic volumes per IP address.

**Key Components:**
- **Network Simulation**: Mininet-based virtual networks with Ryu SDN controller for intelligent packet routing
- **Traffic Generation**: Simulates HTTP/HTTPS and FTP traffic with randomized, time-distributed patterns
- **Packet Capture**: Real-time capture of all network traffic with detailed metadata logging
- **ML Prediction**: Deep learning LSTM model with temporal features that learns traffic patterns and forecasts future network loads
- **Data Preprocessing**: Advanced filtering (removes localhost traffic, low-volume IPs) and temporal feature engineering
- **Real-time Analysis**: Sliding window predictions for continuous traffic monitoring

**Key Improvements:**
- LSTM architecture for better long-term pattern recognition
- Huber loss function for robustness to outliers
- Temporal feature encoding (normalized time, cyclic patterns)
- Automatic noise filtering and IP traffic thresholding
- Comprehensive metrics (MSE, MAE, RMSE, MAPE) and per-IP analysis

## Project Structure

```
Networking/
├── README.md
├── requirements.txt
├── network/
│   ├── controller.py          # Ryu SDN controller with OpenFlow
│   ├── network.py              # Mininet network setup and simulation runner
│   ├── topology.py             # DOT file parser for custom topologies
│   ├── capture/
│   │   ├── packetsniffer.py   # Real-time packet capture thread
│   │   └── packetwrapper.py   # Packet metadata extraction
│   ├── customlogger/
│   │   ├── colors.py          # Terminal color codes
│   │   └── formatter.py       # Custom log formatting
│   └── simulation/
│       ├── simulation.py      # Simulation lifecycle manager
│       ├── task.py            # Task abstraction for traffic events
│       ├── taskqueue.py       # Priority queue for scheduled tasks
│       └── traffic.py         # HTTP/FTP traffic generator
├── prediction/
│   ├── datapreparation.py     # Data loading, filtering, temporal features
│   ├── model.py                # LSTM model with temporal pattern learning
│   ├── train.py                # Training script with advanced metrics
│   ├── predict.py              # Batch inference script
│   ├── realtime_predict.py    # Real-time sliding window predictions
│   └── plot.py                 # Visualization utilities
├── resources/
│   ├── file-list.json         # FTP file URLs for download simulation
│   └── website-list.json      # HTTP/HTTPS URLs for request simulation
├── topology/
│   ├── simple.dot             # Simple network topology definition
│   └── star.dot               # Star network topology definition
└── utils/
    └── run.sh                 # Convenience script to start simulation
```


# Running the Project

## Dependency Installation

### System Dependencies
Make sure you have Mininet installed.

```bash
sudo apt install graphviz graphviz-dev mininet ifupdown vsftpd libxml2-dev libxslt1-dev
sudo apt install build-essential python3-dev libffi-dev libssl-dev zlib1g-dev libjpeg-dev libpng-dev pkg-config
```

### Python Dependencies
```bash
python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

```
### Running the Simulation

```bash
# In the main project directory
./utils/run.sh topology/simple.dot
```

## Training the Prediction Model

After capturing network traffic data, train the LSTM model:

```bash
# Activate virtual environment
source venv/bin/activate

# Train with default parameters
python prediction/train.py

# Train with custom parameters
python prediction/train.py \
    --epochs 150 \
    --bin-size 5.0 \
    --sequence-length 30 \
    --batch-size 64 \
    --min-traffic 5000 \
    --learning-rate 0.001
```

**Training Parameters:**
- `--epochs`: Number of training epochs (default: 150)
- `--bin-size`: Time window for traffic aggregation in seconds (default: 5.0)
- `--sequence-length`: Number of past time steps to use for prediction (default: 30)
- `--batch-size`: Training batch size (default: 64)
- `--min-traffic`: Minimum total traffic per IP to include (filters noise) (default: 5000)
- `--lstm-units`: Number of LSTM units per layer (default: 128)
- `--dropout-rate`: Dropout rate for regularization (default: 0.2)
- `--learning-rate`: Initial learning rate (default: 0.001)
- `--csv-path`: Path to captured traffic CSV (default: datasetx.csv)

**Output Files:**
- `best_model.keras` - Trained model weights
- `test_inference_predictions.csv` - Model predictions on test set
- `test_inference_actuals.csv` - Actual values for comparison
- `all_ips_predictions.png` - Per-IP prediction visualization
- `total_traffic_by_time.png` - Total network traffic over time

## Making Predictions

```bash
# Batch prediction on captured data
python prediction/predict.py --csv-path datasetx.csv

# Real-time prediction with sliding window
python prediction/realtime_predict.py --csv-path datasetx.csv
```
