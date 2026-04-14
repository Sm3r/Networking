if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    printf "Usage: $0 [topology.dot] [--live]\n"
    exit 0
fi

clear

net_folder=network
ryu_log=ryu-output.log
dotfile=$1
live_prediction_flag=""

# Check for optional --live parameter
if [ "$#" -eq 2 ]; then
    if [ "$2" = "--live" ]; then
        live_prediction_flag="--live"
    else
        printf "Error: Unknown parameter '$2'. Use '--live' or omit for default simulation.\n"
        exit 1
    fi
fi

PURPLE="\033[1;35m"
RESET="\033[0m"
BOLD="\033[1m"

printf "${PURPLE} *** [SHELL   ]:${RESET} Starting Ryu Manager...\n"

# Start controller
./venv/bin/ryu-manager $net_folder/controller.py &> "$ryu_log" &
printf "${PURPLE} *** [SHELL   ]:${RESET} ${BOLD}Ryu Manager Started!${RESET}\n"
printf "  ┗  Logging to ${BOLD}$ryu_log${RESET}...\n"

wait_time_s=3
printf "${PURPLE} *** [SHELL   ]:${RESET} Wait for the controller to start.mininet..\n"
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

if command -v xhost >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    xhost +SI:localuser:root >/dev/null 2>&1 || true
fi

# Ensure stale interfaces/bridges from previous runs are removed
sudo mn -c > /dev/null 2>&1

# Create network
sudo -E ./venv/bin/python $net_folder/network.py "$dotfile" $live_prediction_flag

printf "${PURPLE} *** [SHELL   ]:${RESET} Clearing everything...\n"

# Clear everything
sudo mn -c
pkill ryu-manager

if command -v xhost >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    xhost -SI:localuser:root >/dev/null 2>&1 || true
fi

printf "${PURPLE} *** [SHELL   ]:${RESET} Goodbye!!! (;_;)\n"
