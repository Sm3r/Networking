clear

net_folder=network

# Start controller
ryu-manager $net_folder/controller.py &> /dev/null &

sleep 5

# Create network
sudo python3 $net_folder/network.py

# Clear everything
sudo mn -c
