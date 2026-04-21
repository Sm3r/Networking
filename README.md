# Networking

Project for the University of Trento course: Softwarized and virtualized mobile networks (Networking 2nd module).

This project implements a network simulation and traffic prediction system built on Mininet with a Ryu SDN controller.
It enables users to define and simulate custom network topologies using DOT format specifications, it uses **real traffic** then capture and analyze packets in real-time using pyshark.

The system incorporates a lightweight LSTM deep learning model wich can also be used for real-time network traffic prediction, allowing live forecasting of network behavior during simulations.

## Project Structure

```
Networking/
├── README.md
├── requirements.txt
├── model_LSTM.pth
├── network/                     # Core network simulation and SDN controller
│   ├── controller.py
│   ├── logger.py
│   ├── network.py
│   ├── topology.py
│   ├── capture/                 # Packet capture utilities
│   │   ├── packetlogger.py
│   │   ├── packetsniffer.py
│   │   └── packetwrapper.py
│   └── simulation/              # Network simulation modules
│       ├── simulation.py
│       └── traffic.py
├── train/                       # LSTM model training and prediction
│   ├── constants.py
│   ├── data_loader.py
│   ├── network.py
│   ├── plot_results.py
│   ├── preprocessing.py
│   ├── realtime_predict.py
│   └── train.py
├── resources/                   # Configuration and resource files
│   ├── distributions/           # Predefined traffic distribution patterns
│   ├── file-list.json
│   └── website-list.json
├── topology/                    # Network topology definitions
│   ├── simple.dot
│   ├── star.dot
│   ├── complex.dot
│   └── tree.dot
├── data/                        # Training data and scaler models
│   └── scaler.joblib
├── utils/                       # Utility scripts and helpers
│   ├── plot.py
│   ├── run.sh
│   ├── traffic_distribution_gen.py
│   └── traffic-distribution-gen.html
├── plots/                       # Generated plot images and graphs (output)
├── captures/                    # Packet captures from network simulations (output)
└── debug/                       # Debug logs and diagnostic outputs (output)
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
sudo apt install build-essential python3-dev python3-venv libffi-dev libssl-dev zlib1g-dev libjpeg-dev libpng-dev pkg-config
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

## 4. Running the simulation

Make sure you are inside the **`Networking`** folder.

*{Note that the model and the scaler are set with a BIN_SIZE = 5, changing it will require retraining the model and preprocessing the data, wich can be easily done as explained beneath.}*

Start simulation using the provided script:

```bash
./utils/run.sh <topology-path>
```

For example:

```bash
./utils/run.sh topology/simple.dot
```

#### Live prediction:
To run the simultaion with the live network traffic prediction toggled on add the `--live` parameter like so:
```bash
./utils/run.sh topology/simple.dot --live
```


#### Using specific distribution
By default a new pseudo-randomly generated distribution is generated and used at each simulation.
Optionally one of the distribution on wich the model was trained on can be used like so:
```bash
./utils/run.sh topology/star.dot --live resources/distributions/peek.csv
```

## 5. Running the LSTM model

Optionally you can run the LSTM standalone:

Note that you will need some network traffic simulation data to feed to the model:
- You can either run your own simulations and then move the generated CSVs into the data folder.
- Or download the dataset used to train the model_LSTM at [this](https://drive.google.com/drive/folders/1jQ0py1bsn74VH1jnlxRzxm7YL6LfjC0d?usp=sharing) link and then move the datasets into the data folder.

To run the training just execute the training script:
```bash
python train/train.py
```

To rebuild the dataset using new data or different BIN_SIZE when some data is present you have to run the preprocessing script:
```bash
python train/preprocessing.py
```

To see the plot of the prediction results over the test set run:
```bash
python train/plot_results.py
```

(Note that the BIN_SIZE influences the prediction so it must be consistent with the Numpy arrays generated by the preprocessing scritp and the model itself)
