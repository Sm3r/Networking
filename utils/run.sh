if [ "$#" -ne 1 ]; then
    printf "Usage: $0 <topology.dot>\n"
    exit 0
fi

clear

net_folder=network
ryu_log=ryu-output.log
dotfile=$1

printf "*** Starting Ryu Manager...\n"

# Start controller
ryu-manager $net_folder/controller.py &> "$ryu_log" &
printf "*** Ryu Manager Started: logging to $ryu_log!!!\n"

printf "*** Starting mininet in "
for i in {5..1}; do
    printf "$i..."
    sleep 1
done
printf "\n"

# Create network
sudo python3 $net_folder/network.py "$dotfile"

printf "*** Clearing everything...\n"

# Clear everything
sudo mn -c

printf "*** Goodbye!!! (;_;)\n"
