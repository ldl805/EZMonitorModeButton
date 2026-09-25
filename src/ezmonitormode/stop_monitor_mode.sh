#!/bin/bash

# Script to disable monitor mode and restore network services.
# Optimized for Raspberry Pi / ARM Linux environments (v3.0.0).

echo "Attempting to disable monitor mode..."

# Helper to run commands with elevated privileges only when needed
run_elevated() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Helper to check if a systemd unit exists (<15ms vs 1100ms for list-unit-files)
unit_exists() {
    local unit="$1"
    systemctl cat "$unit" >/dev/null 2>&1
}

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
    run_elevated airmon-ng stop "$MON_IFACE"
else
    echo "No interface in monitor mode detected."
    # Only stop common names if they are actually active in monitor mode
    for candidate in wlan0mon wlan1mon wlan0 wlan1; do
        if is_monitor_mode "$candidate"; then
            echo "Stopping monitor candidate $candidate..."
            run_elevated airmon-ng stop "$candidate" >/dev/null 2>&1
        fi
    done
fi

# Determine base restored interface name (e.g. wlan0mon -> wlan0)
BASE_IFACE=""
if [ -n "$TARGET_IFACE" ]; then
    BASE_IFACE="$TARGET_IFACE"
elif [ -n "$MON_IFACE" ]; then
    BASE_IFACE=$(echo "$MON_IFACE" | sed -E 's/mon$//; s/^mon//')
fi

# Ensure Wi-Fi is not left soft-blocked by driver kernel transitions
if command -v rfkill >/dev/null 2>&1; then
    echo "Ensuring wireless interfaces are unblocked (rfkill unblock wifi)..."
    run_elevated rfkill unblock wifi 2>/dev/null || run_elevated rfkill unblock all 2>/dev/null
fi

# Bring base interface UP if it was left down after driver monitor tear-down
if [ -n "$BASE_IFACE" ] && [ -d "/sys/class/net/$BASE_IFACE" ]; then
    echo "Bringing interface $BASE_IFACE UP..."
    run_elevated ip link set "$BASE_IFACE" up 2>/dev/null
fi

echo "Restarting network services..."

# Restart NetworkManager (manages connections on modern Pi OS / Debian / Ubuntu)
if unit_exists NetworkManager; then
    echo "Restarting NetworkManager..."
    run_elevated systemctl restart NetworkManager
fi

# Restart wpa_supplicant (if installed and managed independently)
if unit_exists wpa_supplicant; then
    echo "Restarting wpa_supplicant..."
    run_elevated systemctl restart wpa_supplicant
fi

# Restart avahi-daemon (mDNS)
if unit_exists avahi-daemon; then
    echo "Restarting avahi-daemon..."
    run_elevated systemctl restart avahi-daemon
fi

# Restart dhcpcd if present (for legacy/alternative Raspberry Pi installations)
if unit_exists dhcpcd; then
    echo "Restarting dhcpcd..."
    run_elevated systemctl restart dhcpcd
fi

echo "Monitor mode disabled and services restoration requested."
echo "Please wait a few seconds for network to reconnect."
