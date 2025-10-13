# Networking

Project for the University of Trento course of Virtualized network (Networking 2nd module).

This project implements a network simulation using Mininet with a Ryu SDN controller. It supports custom topologies defined in DOT format and includes traffic simulation capabilities.

## Project Structure

```
Networking/
├── README.md
├── requirements.txt
├── network/
│   ├── controller.py
│   ├── network.py
│   ├── topology.py
│   ├── capture/
│   │   ├── packetsniffer.py
│   │   └── packetwrapper.py
│   ├── customlogger/
│   │   ├── colors.py
│   │   └── formatter.py
│   └── simulation/
│       ├── simulation.py
│       ├── task.py
│       ├── taskqueue.py
│       └── traffic.py
├── prediction/
│   └── TODO
├── resources/
│   ├── file-list.json
│   └── website-list.json
├── topology/
│   ├── simple.dot
│   └── star.dot
└── utils/
    └── run.sh
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
