# Networking

Project for the University of Trento course: Softwarized and virtualized mobile networks (Networking 2nd module).

This project implements a network simulation using Mininet with a Ryu SDN controller. It supports custom topologies defined in DOT format and includes traffic simulation capabilities.

## Project Structure

```
Networking/
├── README.md
├── requirements.txt
├── model_LSTM.pth
├── data/
├── network/
│   ├── controller.py
│   ├── logger.py
│   ├── network.py
│   ├── topology.py
│   ├── capture/
│   │   ├── packetlogger.py
│   │   ├── packetsniffer.py
│   │   └── packetwrapper.py
│   └── simulation/
│       ├── simulation.py
│       └── traffic.py
├── plots/
├── resources/
│   ├── file-list.json
│   ├── traffic_signal.csv
│   └── website-list.json
├── topology/
│   ├── simple.dot
│   └── star.dot
├── train/
│   ├── constants.py
│   ├── data_loader.py
│   ├── network.py
│   ├── plot_results.py
│   ├── preprocessing.py
│   ├── realtime_predict.py
│   └── train.py
└── utils/
    ├── plot.py
    ├── run.sh
    └── traffic-distribution-gen.html
```

# Project Setup Guide
This guide will help you set up your environment and run the project step by step. 

## 1. ComNetsEmu

The first step is to install the ComNetsEmu network emulator following [this](https://www.granelli-lab.org/researches/relevant-projects/comnetsemu-labs) guide.

Once it is running, clone this repository **inside the virtual machine** and **move inside the project directory.**


## 2. Install Dependencies

**Make sure you have Mininet installed**

Before running the project, make sure the required system packages are installed.  
You can do so by running:

```bash
sudo apt install graphviz graphviz-dev mininet ifupdown vsftpd libxml2-dev libxslt1-dev
sudo apt install build-essential python3-dev libffi-dev libssl-dev zlib1g-dev libjpeg-dev libpng-dev pkg-config
```
These packages include tools for Python environments, graph visualization, network interfaces, file transfer, and packet inspection.

If not installed already we need a matplotlib supported GUI backend to handle the live prediction plotting:
```bash
sudo apt-get install python3-tk
```

Pyshark requires tshark (Wireshark's command-line tool) to capture network packets:
```bash
sudo apt install tshark
```

Next, make sure your system is up to date:
```bash
sudo apt update
sudo apt upgrade
```
## 3. Python Virtual Environment

It is recommended to create a virtual environment to keep your Python dependencies isolated from the system.  
inside the project folder create the enviroment, activate it and install all Python packages needed:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --default-timeout=240 --retries 10 --no-cache-dir
```

## 4. Running the Project

Make sure you are inside the **`Networking`** folder.  

Start simulation using the provided script:

```bash
./utils/run.sh <topology-path>
```

For example:

```bash
./utils/run.sh topology/simple.dot
```

This will load and execute the specified topology inside ComNetsEmu, allowing you to simulate the network behavior defined in the `.dot` file.


