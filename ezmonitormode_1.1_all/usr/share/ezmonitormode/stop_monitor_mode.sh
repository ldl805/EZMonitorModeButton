#!/bin/bash

# Script to disable monitor mode on wlan1 and restore network services.
# This script is intended to be the counterpart to monitor_mode.sh

# The interface usually becomes wlan1mon after airmon-ng start.
# We will attempt to stop that, or wlan1 if wlan1mon doesn't exist.

MON_INTERFACE="wlan1mon"
ORIG_INTERFACE="wlan1"

echo "Attempting to disable monitor mode..."

# Try stopping wlan1mon first
if ip link show "$MON_INTERFACE" > /dev/null 2>&1; then
    echo "Stopping $MON_INTERFACE..."
    sudo airmon-ng stop "$MON_INTERFACE"
else
    echo "$MON_INTERFACE not found. Checking for $ORIG_INTERFACE in monitor mode..."
    # If wlan1 is in monitor mode (sometimes airmon-ng doesn't rename it)
    sudo airmon-ng stop "$ORIG_INTERFACE"
fi

echo "Restarting network services..."

# Restart NetworkManager (manages connections)
if systemctl list-unit-files | grep -q NetworkManager; then
    echo "Restarting NetworkManager..."
    sudo systemctl restart NetworkManager
fi

# Restart wpa_supplicant (often handled by NM, but good to ensure)
if systemctl list-unit-files | grep -q wpa_supplicant; then
    echo "Restarting wpa_supplicant..."
    sudo systemctl restart wpa_supplicant
fi

# Restart avahi-daemon (mDNS)
if systemctl list-unit-files | grep -q avahi-daemon; then
    echo "Restarting avahi-daemon..."
    sudo systemctl restart avahi-daemon
fi

echo "Monitor mode disabled and services restoration requested."
echo "Please wait a few seconds for network to reconnect."
