if [ "$#" -ne 1 ]; then
    printf "Usage: $0 [topology.dot]\n"
    exit 0
fi

clear

net_folder=network
ryu_log=ryu-output.log
dotfile=$1

PURPLE="\033[1;35m"
RESET="\033[0m"
BOLD="\033[1m"

printf "${PURPLE} *** [SHELL]:${RESET} Starting Ryu Manager...\n"

# Start controller
ryu-manager $net_folder/controller.py &> "$ryu_log" &
printf "${PURPLE} *** [SHELL]:${RESET} ${BOLD}Ryu Manager Started!${RESET}\n"
printf "  ┗  Logging to ${BOLD}$ryu_log${RESET}...\n"

wait_time_s=3
printf "${PURPLE} *** [SHELL]:${RESET} Wait for the controller to start.mininet..\n"
# Simple loading animation
for ((i = 0; i <= $wait_time_s; i++)); do
    remaining=$(( $wait_time_s - $i ))
    if [ $remaining -eq 0 ]; then
        printf "\r  ┣  $remaining "
    else
        printf "\r  ┗  $remaining "
    fi

    # Print loading bar
    for j in $(seq $i); do
        printf "████"
    done
    for j in $(seq $remaining); do
        printf "░░░░"
    done

    # Wait one second
    if [ $remaining -gt 0 ]; then
        sleep 1
    fi
done
printf "\n  ┗  Starting mininet...\n"

# Create network
sudo python3 $net_folder/network.py "$dotfile"

printf "${PURPLE} *** [SHELL]:${RESET} Clearing everything...\n"

# Clear everything
sudo mn -c
pkill ryu-manager

printf "${PURPLE} *** [SHELL]:${RESET} Goodbye!!! (;_;)\n"
