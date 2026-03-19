# EZMonitorModeButton

A simple Python GUI for the Raspberry Pi to easily enable and disable monitor mode on a wireless interface (default: `wlan1`).

## Features
- **One-click Enable:** Kills conflicting processes and enables monitor mode.
- **One-click Disable:** Stops monitor mode and restores network services.
- **Shortcuts:** Quick buttons to launch common security tools like Wifite, Wireshark, and Kismet.

## Installation (Recommended)

### Option 1: Debian Package (Pi/Ubuntu/Debian)

Download the latest `.deb` file from the [Releases](https://github.com/ldl805/EZMonitorModeButton/releases) page and install it using:

```bash
sudo apt update
sudo apt install ./ezmonitormode_1.0_all.deb
```

Once installed, you can launch it from your application menu or by running `ezmonitormode` in the terminal.

### Option 2: Running from Source

1.  **Clone this repository:**
    ```bash
    git clone https://github.com/ldl805/EZMonitorModeButton.git
    cd EZMonitorModeButton
    ```
2.  **Run the installation script** to install dependencies:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```
3.  **Run the application:**
    ```bash
    sudo python3 monitor_gui.py
    ```

## License
MIT License
