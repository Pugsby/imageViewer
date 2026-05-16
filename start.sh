#!/bin/bash
# check if the user is running linux (mac and bsd support does NOT exist)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Starting with Linux."
else
    echo "This script is only supported on Linux. Exiting."
    exit 1
fi
if [[ "$EUID" -eq 0 ]]; then
    echo "Running as root is not recommended as malicious scrapers and plugins can fuck up your system."
fi
python ./startLogic/start.py --linux