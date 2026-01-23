#!/bin/bash

echo "Installing dependencies for Monitor Mode Manager..."

# Update package list
# sudo apt update

# Install core dependencies
echo "Installing Python3, Tkinter, and Aircrack-ng..."
sudo apt install -y python3 python3-tk aircrack-ng wireless-tools

# Install optional tools
echo "Do you want to install the optional tools (wifite, wireshark, kismet)? [y/N]"
read -r install_tools
if [[ "$install_tools" =~ ^[yY]$ ]]; then
    sudo apt install -y wifite wireshark kismet
fi

# Make scripts executable
chmod +x monitor_mode.sh stop_monitor_mode.sh monitor_gui.py

echo "Installation complete."
echo "You can now run the GUI with: sudo ./monitor_gui.py"
