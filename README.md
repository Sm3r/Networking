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

# Project Setup Guide

This guide will help you set up your environment and run the project step by step.  
It assumes that you are using the **(mettere info)** virtual machine, which provides a suitable environment for network simulation and experimentation.

## 1. ComNetsEmu Environment

First, install the **(stesso nome di prima)** virtual machine.  
Once it is running, clone this repository **inside the virtual machine** and move into the project directory:

```bash
cd Networking
```

This directory contains all the scripts and topologies required to run the network simulations.

---


## 2. Install Dependencies

Before running the project, make sure the required system packages are installed.  
You can do so by running:

```bash
sudo apt install python3-venv graphviz graphviz-dev ifupdown vsftpd wireshark
```

These packages include tools for Python environments, graph visualization, network interfaces, file transfer, and packet inspection.

---

## 3. Python Virtual Environment

It is recommended to create a virtual environment to keep your Python dependencies isolated from the system.  
Run the following commands:

```bash
python3 -m venv venv
source venv/bin/activate
```

Once the virtual environment is activated, update `pip` and install all required Python packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This ensures that all Python dependencies are properly installed and up to date.

---

## 4. System Update and Wireshark Configuration

Next, make sure your system is up to date:

```bash
sudo apt update
sudo apt upgrade
```

Wireshark needs special permissions to capture network traffic.  
Add your user to the Wireshark group with:

```bash
sudo usermod -aG wireshark $USER
```

If the `wireshark` group does not exist, reboot the system and try the command again.

Then reconfigure Wireshark permissions:

```bash
sudo dpkg-reconfigure wireshark-common
```

Finally, reboot your machine to apply all changes:

```bash
sudo reboot now
```

---
## 5. Running the Project

Once the setup is complete, make sure you are inside the **`Networking`** folder.  
You can then start a network topology using the provided script:

```bash
./utils/run.sh <topology-path>
```

For example:

```bash
./utils/run.sh topology/simple.dot
```

This will load and execute the specified topology inside ComNetsEmu, allowing you to simulate the network behavior defined in the `.dot` file.

---

-------------------------------------------------------------------------------------------------

## Dependency Installation

### System Dependencies
Make sure you have Mininet installed.

```bash
sudo apt install graphviz graphviz-dev mininet ifupdown vsftpd libxml2-dev libxslt1-dev
sudo apt install build-essential python3-dev libffi-dev libssl-dev zlib1g-dev libjpeg-dev libpng-dev pkg-config
```

