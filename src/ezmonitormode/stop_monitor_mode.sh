#!/bin/bash

# Script to disable monitor mode and restore network services.

echo "Attempting to disable monitor mode..."

# Helper function to test if an interface is in monitor mode
is_monitor_mode() {
    local iface="$1"
    [ -z "$iface" ] && return 1
    if command -v iw >/dev/null 2>&1; then
        iw dev "$iface" info 2>/dev/null | grep -q "type monitor" && return 0
    fi
    if command -v iwconfig >/dev/null 2>&1; then
        iwconfig "$iface" 2>/dev/null | grep -q "Mode:Monitor" && return 0
    fi
    return 1
}

# Helper function to auto-detect any active monitor mode interface
find_any_monitor_iface() {
    if command -v iw >/dev/null 2>&1; then
        local mon_if
        mon_if=$(iw dev 2>/dev/null | awk '/Interface/ {iface=$2} /type monitor/ {print iface}')
        if [ -n "$mon_if" ]; then
            echo "$mon_if" | head -n 1
            return 0
        fi
    fi
    if command -v iwconfig >/dev/null 2>&1; then
        local mon_if
        mon_if=$(iwconfig 2>/dev/null | grep "Mode:Monitor" | awk '{print $1}' | head -n 1)
        if [ -n "$mon_if" ]; then
            echo "$mon_if"
            return 0
        fi
    fi
    return 1
}

# Detect target interface from argument or auto-detect first monitor mode interface
TARGET_IFACE="$1"

if [ -n "$TARGET_IFACE" ]; then
    if is_monitor_mode "$TARGET_IFACE"; then
        MON_IFACE="$TARGET_IFACE"
    elif is_monitor_mode "${TARGET_IFACE}mon"; then
        MON_IFACE="${TARGET_IFACE}mon"
    elif is_monitor_mode "mon${TARGET_IFACE}"; then
        MON_IFACE="mon${TARGET_IFACE}"
    else
        MON_IFACE="$TARGET_IFACE"
    fi
else
    MON_IFACE=$(find_any_monitor_iface)
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
    echo "No interface in monitor mode detected."
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
