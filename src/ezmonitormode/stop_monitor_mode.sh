#!/bin/bash

# Script to disable monitor mode and restore network services.

echo "Attempting to disable monitor mode..."

# Detect target interface from argument or auto-detect first monitor mode interface
TARGET_IFACE="$1"

if [ -n "$TARGET_IFACE" ]; then
    MON_IFACE="$TARGET_IFACE"
    # If the user passed wlan0 but only wlan0mon exists, help resolve it
    if ! iwconfig "$MON_IFACE" 2>/dev/null | grep -q "Mode:Monitor" && iwconfig "${MON_IFACE}mon" 2>/dev/null | grep -q "Mode:Monitor"; then
        MON_IFACE="${MON_IFACE}mon"
    fi
else
    MON_IFACE=$(iwconfig 2>/dev/null | grep "Mode:Monitor" | awk '{print $1}' | head -n 1)
fi

# Check if airmon-ng exists
if ! command -v airmon-ng >/dev/null 2>&1; then
    echo "Error: airmon-ng not found. Is aircrack-ng installed?"
    exit 1
fi

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

# Restart dhcpcd if present (for legacy/alternative Raspberry Pi installations)
if systemctl list-unit-files | grep -q dhcpcd; then
    echo "Restarting dhcpcd..."
    sudo systemctl restart dhcpcd
fi

echo "Monitor mode disabled and services restoration requested."
echo "Please wait a few seconds for network to reconnect."
