#!/bin/bash

# Script to disable monitor mode and restore network services.

echo "Attempting to disable monitor mode..."

# Detect which interface is currently in monitor mode
MON_IFACE=$(iwconfig 2>/dev/null | grep "Mode:Monitor" | awk '{print $1}' | head -n 1)

if [ -n "$MON_IFACE" ]; then
    echo "Found monitor interface: $MON_IFACE"
    echo "Stopping $MON_IFACE..."
    sudo airmon-ng stop "$MON_IFACE"
else
    echo "No interface in monitor mode detected via iwconfig."
    echo "Attempting fallback airmon-ng stop on common names..."
    sudo airmon-ng stop wlan0mon >/dev/null 2>&1
    sudo airmon-ng stop wlan1mon >/dev/null 2>&1
    sudo airmon-ng stop wlan0 >/dev/null 2>&1
    sudo airmon-ng stop wlan1 >/dev/null 2>&1
fi

echo "Restarting network services..."
...
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
