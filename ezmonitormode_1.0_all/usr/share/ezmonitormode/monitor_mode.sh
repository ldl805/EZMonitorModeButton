#!/bin/bash

# Script to switch a wireless interface into monitor mode.

INTERFACE="wlan1" # The wireless interface to put into monitor mode

echo "This script will prepare your system for monitor mode by killing conflicting processes"
echo "and then attempt to switch $INTERFACE into monitor mode."
echo "Root privileges (sudo) will be required."

read -p "Do you want to proceed? (y/N): " confirm
if [[ ! "$confirm" =~ ^[yY]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

echo "Step 1: Killing conflicting processes with airmon-ng check kill..."
if sudo airmon-ng check kill; then
    echo "Conflicting processes killed successfully (or none were running)."
else
    echo "Error: Failed to kill conflicting processes. Please check the output above."
    read -p "Do you want to continue attempting to put $INTERFACE into monitor mode anyway? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[yY]$ ]]; then
        echo "Operation cancelled."
        exit 1
    fi
fi

echo "Step 2: Switching $INTERFACE into monitor mode..."
# airmon-ng start usually renames the interface, often adding "mon" or changing it.
# The output will tell us the new monitor interface name.
MON_INTERFACE_OUTPUT=$(sudo airmon-ng start "$INTERFACE" 2>&1)
EXIT_CODE=$?

echo "$MON_INTERFACE_OUTPUT"

if [ "$EXIT_CODE" -eq 0 ]; then
    # Try to extract the new monitor interface name
    NEW_MON_INTERFACE=$(echo "$MON_INTERFACE_OUTPUT" | grep -oP '\s\K\w+mon(?=\s+)' | tail -n 1)
    if [ -z "$NEW_MON_INTERFACE" ]; then
        NEW_MON_INTERFACE=$(echo "$MON_INTERFACE_OUTPUT" | grep -oP '\(monitor mode enabled on \)\K\w+' | tail -n 1)
    fi

    if [ -n "$NEW_MON_INTERFACE" ]; then
        echo "Success: $INTERFACE is now in monitor mode as $NEW_MON_INTERFACE."
        echo "You can now use tools like airodump-ng or Wireshark on $NEW_MON_INTERFACE."
    else
        echo "Success: $INTERFACE should now be in monitor mode, but could not determine new interface name."
        echo "Please check 'iwconfig' or 'ip a' to find the new monitor interface name (e.g., 'wlan1mon')."
    fi
else
    echo "Error: Failed to switch $INTERFACE into monitor mode. Please check the output above."
    exit 1
fi

echo "Script finished."