# Networking

Project for the University of Trento course of Virtualized network (Networking 2nd module).

This project implements a network simulation using Mininet with a Ryu SDN controller. It supports custom topologies defined in DOT format and includes traffic simulation capabilities.

## Project Structure

```
Networking/
├── README.md               
├── requirements.txt       # Python dependencies
├── network/               # Core networking modules
│   ├── controller.py      # Ryu SDN controller implementation
│   ├── network.py         # Main network setup and management
│   ├── topology.py        # Custom topology parser
│   ├── customlogger/      # Custom logging utilities
│   └── simulation/        # Traffic simulation modules
├── prediction/            # Traffic prediction ML models
│   ├── data_processing.py # Data preprocessing scripts
│   ├── model.py           # RNN model definition and training
│   └── run.py             # Main execution file for prediction pipeline
├── resources/             # Resource files (JSON configs)
├── topology/              # Sample topology files (.dot format)
│   ├── simple.dot         # Simple 2-host topology
│   └── star.dot           # Star topology
└── utils/
    └── run.sh             # Main execution script
```

## Dependency Installation

### System Dependencies
Make sure you have Mininet installed.

```bash
sudo apt install graphviz graphviz-dev mininet ifupdown vsftpd
```

### Python Dependencies
```bash
python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

```

