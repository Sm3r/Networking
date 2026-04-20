if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
    printf "Usage: $0 [topology.dot] [--live] [distribution.csv]\n"
    exit 0
fi

clear

net_folder=network
utils_folder=utils
ryu_log=debug/$$-ryu-output.log
dotfile=$1
live_prediction_flag=""
distribution_file=""

# Check for optional parameters
for arg in "${@:2}"; do
    if [ "$arg" = "--live" ]; then
        live_prediction_flag="--live"
    elif [[ "$arg" == *.csv ]]; then
        # Check if the CSV file exists
        if [ ! -f "$arg" ]; then
            printf "Error: Distribution file not found: '$arg'\n"
            printf "Available distributions in resources/distributions/:\n"
            if [ -d "resources/distributions" ]; then
                ls -1 resources/distributions/*.csv 2>/dev/null | sed 's/^/  /'
            fi
            exit 1
        fi
        distribution_file="$arg"
    else
        printf "Error: Unknown parameter '$arg'. Use '--live' or provide a CSV file path.\n"
        exit 1
    fi
done

# If no distribution file specified, generate one at runtime
if [ -z "$distribution_file" ]; then
    printf "${PURPLE} *** [SHELL   ]:${RESET} Generating traffic distribution...\n"
    python3 $utils_folder/traffic_distribution_gen.py
    if [ $? -ne 0 ]; then
        printf "Error: Failed to generate traffic distribution\n"
        exit 1
    fi
    distribution_file="resources/distributions/traffic_signal.csv"
    printf "${PURPLE} *** [SHELL   ]:${RESET} Traffic distribution generated!\n"
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

# Create network with optional distribution file
if [ -n "$distribution_file" ]; then
    sudo -E ./venv/bin/python $net_folder/network.py "$dotfile" $live_prediction_flag "$distribution_file"
else
    sudo -E ./venv/bin/python $net_folder/network.py "$dotfile" $live_prediction_flag
fi

printf "${PURPLE} *** [SHELL   ]:${RESET} Clearing everything...\n"

# Clear everything
sudo mn -c
pkill ryu-manager

if command -v xhost >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    xhost -SI:localuser:root >/dev/null 2>&1 || true
fi

printf "${PURPLE} *** [SHELL   ]:${RESET} Goodbye!!! (;_;)\n"
