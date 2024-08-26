#!/bin/bash

clear

BASE_DIR=$(dirname "$0")

chmod +w "$BASE_DIR"

chmod +x "$BASE_DIR/main.py"

CONFIG_FILE="$BASE_DIR/application_config.txt"

if [ -f "$CONFIG_FILE" ]; then
    chmod +w "$CONFIG_FILE"
fi

install_dependencies() {
    echo "Upgrading and reinstalling dependencies..."
    if pip install --upgrade --force-reinstall -r "$BASE_DIR/requirements.txt" > /dev/null 2>&1; then
        echo "Dependencies installed/upgraded successfully."
    else
        echo "Dependency installation failed. Attempting to fix..."
        echo "Purging pip cache and retrying..."
        pip cache purge > /dev/null 2>&1
        if pip install --upgrade --force-reinstall -r "$BASE_DIR/requirements.txt" > /dev/null 2>&1; then
            echo "Dependencies installed successfully after cache purge."
        else
            echo "ERROR: Dependency installation failed even after cache purge."
            exit 1
        fi
    fi
}

trap 'echo "Terminating..."; exit 0' SIGINT

install_dependencies

echo "NOTE: If you get errors in the app, check if your OpenAI account has enough credits or whether the API key is valid. Also, terminating and relaunching dalle3mwp.sh, might solve some issues sometimes like BadRequestErrors from OpenAI."
if ! python3 "$BASE_DIR/main.py" 2> error.log; then
    echo "ERROR: An error occurred while running the app."
    grep -E "^[^:]+Error: " error.log
    rm error.log
    exit 1
fi

echo "Press [Enter] to exit the terminal..."
read -r

exit 0
