#!/bin/bash

echo "Installing dependencies for EZMonitorMode..."

# Core dependencies
echo "Installing Python3, Tkinter, Aircrack-ng, Wireless Tools, and IW..."
sudo apt update
sudo apt install -y python3 python3-tk aircrack-ng wireless-tools iw

# Optional tools
echo "Do you want to install the optional tools (wifite, wireshark, kismet)? [y/N]"
read -r install_tools
if [[ "$install_tools" =~ ^[yY]$ ]]; then
    sudo apt install -y wifite wireshark kismet
fi

# Make scripts executable in source dir
chmod +x src/ezmonitormode/monitor_mode.sh src/ezmonitormode/stop_monitor_mode.sh src/ezmonitormode/monitor_gui.py

echo "Installation complete."
echo "You can now run the GUI with: sudo -E python3 src/ezmonitormode/monitor_gui.py"
