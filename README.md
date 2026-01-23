# Monitor Mode Manager

A simple GUI and set of scripts to easily toggle Monitor Mode on `wlan1` (or your specified interface) and launch common wireless auditing tools.

## Features

- **GUI Control**: Toggle Monitor Mode ON and OFF with a simple click.
- **Smart Restoration**: When disabling Monitor Mode, it attempts to restart networking services (`NetworkManager`, `avahi`, `wpa_supplicant`) to restore internet connectivity.
- **Tool Shortcuts**: Quick launch buttons for `Wifite`, `Wireshark`, and `Kismet`.

## Prerequisites / Dependencies

This tool requires the following packages to be installed:

- `python3`
- `python3-tk` (for the GUI)
- `aircrack-ng` (provides `airmon-ng`)
- `wireless-tools` (usually installed by default)
- `sudo` access

Optional (but recommended for the shortcuts to work):
- `wifite`
- `wireshark`
- `kismet`

## Installation

1.  Clone this repository (or download the folder).
2.  Run the installation script to ensure dependencies are met (Debian/Ubuntu/Kali):
    ```bash
    sudo ./install.sh
    ```

## Usage

Run the GUI with root privileges:

```bash
sudo ./monitor_gui.py
```

### Manual Usage

You can also use the scripts directly:

- **Enable Monitor Mode:**
  ```bash
  sudo ./monitor_mode.sh
  ```

- **Disable Monitor Mode:**
  ```bash
  sudo ./stop_monitor_mode.sh
  ```

## Configuration

To change the default interface from `wlan1` to something else (e.g., `wlan0`), edit the `INTERFACE` variable at the top of:
- `monitor_gui.py`
- `monitor_mode.sh`
- `stop_monitor_mode.sh`

## License

MIT
