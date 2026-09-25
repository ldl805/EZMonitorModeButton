#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import shutil
import sys
import logging
import threading
import time
import shlex
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
VERSION = "3.0.0"

AVAILABLE_CHANNELS = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14",
    "36", "40", "44", "48", "52", "56", "60", "64", "100", "104", "108", "112",
    "116", "120", "124", "128", "132", "136", "140", "144", "149", "153", "157", "161", "165"
]

HOP_PROFILES = {
    "1, 6, 11 (2.4GHz)": ["1", "6", "11"],
    "2.4GHz (1-14)": [str(c) for c in range(1, 15)],
    "5GHz UNII-1/3": ["36", "40", "44", "48", "149", "153", "157", "161", "165"],
    "All Channels": [str(c) for c in range(1, 15)] + ["36", "40", "44", "48", "149", "153", "157", "161", "165"]
}

def run_cmd(cmd_list, timeout=30):
    """
    Executes a system command with elevated privileges only if EUID != 0.
    Prevents redundant sudo PAM overhead on Raspberry Pi.
    """
    if os.geteuid() != 0 and (not cmd_list or cmd_list[0] != "sudo"):
        cmd_list = ["sudo"] + list(cmd_list)
    return subprocess.run(cmd_list, capture_output=True, timeout=timeout)

def get_default_gateway_interface():
    """
    Returns the network interface holding the system default gateway (0.0.0.0).
    Reads /proc/net/route directly without subprocess overhead (<0.1ms).
    """
    try:
        with open("/proc/net/route", "r") as f:
            for line in f.readlines()[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "00000000":
                    return parts[0]
    except Exception:
        pass
    return None

def get_device_driver_and_chipset(iface):
    """
    Extracts wireless driver and hardware chipset details directly via sysfs in <0.2ms.
    Returns dict: {'driver': str, 'chipset': str, 'operstate': str}
    """
    info = {"driver": "Unknown", "chipset": "", "operstate": "unknown"}
    if not iface:
        return info
    base = f"/sys/class/net/{iface}"
    try:
        driver_path = f"{base}/device/driver"
        if os.path.islink(driver_path):
            info["driver"] = os.path.basename(os.readlink(driver_path))
    except Exception:
        pass

    try:
        product_path = f"{base}/device/../product"
        if os.path.exists(product_path):
            with open(product_path, "r", errors="replace") as f:
                info["chipset"] = f.read().strip()
    except Exception:
        pass

    try:
        with open(f"{base}/operstate", "r", errors="replace") as f:
            info["operstate"] = f.read().strip()
    except Exception:
        pass

    return info

def get_interfaces_status():
    """Detects wireless interfaces and maps them to their mode ('managed', 'monitor')."""
    status = {}
    
    # Try 'iw dev' first (modern standard)
    try:
        output = subprocess.check_output(["iw", "dev"], stderr=subprocess.STDOUT, timeout=5).decode(errors='replace')
        current_iface = None
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("Interface "):
                current_iface = line.split()[1]
                status[current_iface] = "managed" # default fallback
            elif line.startswith("type ") and current_iface:
                status[current_iface] = line.split()[1]
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback to 'iwconfig'
        try:
            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT, timeout=5).decode(errors='replace')
            current_iface = None
            for line in output.split("\n"):
                if not line or "no wireless extensions" in line.lower():
                    continue
                parts = line.split()
                if len(parts) > 0 and not line.startswith(" "):
                    current_iface = parts[0]
                    status[current_iface] = "managed"
                if "Mode:Monitor" in line and current_iface:
                    status[current_iface] = "monitor"
        except Exception as e:
            logging.error(f"Failed to detect interface status: {e}")
            
    return status

def detect_interfaces():
    """Detects wireless base interfaces, prioritizing secondary/external adapters if connected to a network."""
    status = get_interfaces_status()
    interfaces = list(status.keys())
    
    # Clean up names (e.g. resolve 'wlan0mon' to base name 'wlan0')
    base_interfaces = []
    for iface in interfaces:
        if iface.endswith("mon"):
            base_interfaces.append(iface[:-3])
        elif iface.endswith(".mon"):
            base_interfaces.append(iface[:-4])
        elif iface.startswith("mon"):
            base_interfaces.append(iface[3:])
        else:
            base_interfaces.append(iface)
            
    unique_ifaces = sorted(list(set(base_interfaces)))
    
    # If multiple interfaces exist and one is the active default gateway, place secondary interfaces first
    default_route = get_default_gateway_interface()
    if len(unique_ifaces) > 1 and default_route in unique_ifaces:
        non_default = [i for i in unique_ifaces if i != default_route]
        return non_default + [default_route]
        
    return unique_ifaces

def get_interface_details(iface):
    """Returns a dict containing interface details: channel, freq, mac, txpower, mode, ssid, driver, chipset."""
    details = {
        "channel": "Unknown",
        "freq": "",
        "mac": "Unknown",
        "txpower": "",
        "mode": "Unknown",
        "ssid": "",
        "driver": "Unknown",
        "chipset": "",
        "operstate": "unknown"
    }
    if not iface:
        return details

    # Fast sysfs metadata (<0.2ms)
    sys_info = get_device_driver_and_chipset(iface)
    details["driver"] = sys_info["driver"]
    details["chipset"] = sys_info["chipset"]
    details["operstate"] = sys_info["operstate"]

    # Read MAC from sysfs (<0.1ms) fallback
    try:
        with open(f"/sys/class/net/{iface}/address", "r", errors="replace") as f:
            mac_val = f.read().strip()
            if mac_val:
                details["mac"] = mac_val
    except Exception:
        pass
        
    try:
        output = subprocess.check_output(["iw", "dev", iface, "info"], stderr=subprocess.STDOUT, timeout=3).decode(errors='replace')
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("addr "):
                details["mac"] = line.split()[1]
            elif line.startswith("type "):
                details["mode"] = line.split()[1]
            elif line.startswith("ssid "):
                details["ssid"] = " ".join(line.split()[1:])
            elif line.startswith("channel "):
                parts = line.split()
                details["channel"] = parts[1]
                if "(" in line and ")" in line:
                    details["freq"] = line.split("(")[1].split(")")[0]
            elif line.startswith("txpower "):
                parts = line.split()
                details["txpower"] = " ".join(parts[1:])
        return details
    except Exception:
        pass

    try:
        output = subprocess.check_output(["iwconfig", iface], stderr=subprocess.STDOUT, timeout=3).decode(errors='replace')
        for line in output.split("\n"):
            if "Mode:" in line:
                mode_part = line.split("Mode:")[1].split()[0]
                details["mode"] = mode_part
            if "ESSID:" in line:
                essid = line.split("ESSID:")[1].split()[0].replace('"', '')
                if essid and essid != "off/any":
                    details["ssid"] = essid
            if "Frequency:" in line:
                freq_part = line.split("Frequency:")[1].split()[0]
                details["freq"] = freq_part + " GHz"
            if "Channel=" in line:
                chan_part = line.split("Channel=")[1].split()[0]
                details["channel"] = chan_part
            if "Tx-Power=" in line:
                tx_part = line.split("Tx-Power=")[1].split()[0]
                details["txpower"] = tx_part + " dBm"
    except Exception:
        pass
        
    return details

def center_window(window, width, height):
    """Centers the window on the screen, safeguarding against off-screen placement."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, (screen_width // 2) - (width // 2))
    y = max(0, (screen_height // 2) - (height // 2))
    window.geometry(f'{width}x{height}+{x}+{y}')

class CanvasToggle(tk.Canvas):
    """A custom glowing Canvas-based sliding toggle switch."""
    def __init__(self, master, width=80, height=34, callback=None, **kwargs):
        super().__init__(master, width=width, height=height, bg="#1a1a1a", highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.callback = callback
        self.is_on = False
        self.is_hovered = False
        self.config(cursor="hand2")
        
        self.draw_widget()
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
    def draw_widget(self):
        self.delete("all")
        
        padding = 2
        x1, y1 = padding, padding
        x2, y2 = self.width - padding, self.height - padding
        radius = (y2 - y1) / 2
        
        if self.is_on:
            track_color = "#1b3a1e"  # dim green
            knob_color = "#39ff14"   # neon green
            knob_x = x2 - radius
        else:
            track_color = "#3a1c1c"  # dim red
            knob_color = "#ff1744"   # glowing red
            knob_x = x1 + radius
            
        # Draw pill-shaped track
        self.create_oval(x1, y1, x1 + 2*radius, y2, fill=track_color, outline="#3e3e3e")
        self.create_oval(x2 - 2*radius, y1, x2, y2, fill=track_color, outline="#3e3e3e")
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=track_color, outline="")
        self.create_line(x1 + radius, y1, x2 - radius, y1, fill="#3e3e3e")
        self.create_line(x1 + radius, y2, x2 - radius, y2, fill="#3e3e3e")
        
        # Draw circular knob
        knob_r = radius - 2
        outline_color = "#ffffff" if self.is_hovered else "#d0d0d0"
        outline_width = 2 if self.is_hovered else 1
        self.create_oval(knob_x - knob_r, y1 + 2, knob_x + knob_r, y2 - 2, fill=knob_color, outline=outline_color, width=outline_width)
        
    def set_state(self, is_on):
        if self.is_on != is_on:
            self.is_on = is_on
            self.draw_widget()
            
    def on_click(self, event):
        if self.callback:
            self.callback()

    def on_enter(self, event):
        self.is_hovered = True
        self.draw_widget()

    def on_leave(self, event):
        self.is_hovered = False
        self.draw_widget()

class MonitorGUI:
    def __init__(self, master, interfaces):
        self.master = master
        self.interfaces = interfaces
        self.interface = interfaces[0] if interfaces else "wlan1"
        
        master.title(f"EZ Monitor Mode {VERSION}")
        
        # Auto-detect small screen (e.g. Raspberry Pi 7" 800x480 touchscreen)
        screen_height = master.winfo_screenheight()
        self.is_small_screen = screen_height <= 600
        initial_height = 410 if self.is_small_screen else 640
        initial_width = 440
        center_window(master, initial_width, initial_height)
        master.minsize(410, 370)
        master.resizable(True, True)

        # Style Configuration
        self._setup_style()
        self.master.configure(bg="#1e1e1e")
        
        # State
        self.is_monitor_on = False
        self.is_transitioning = False
        self.is_channel_hopping = False
        self.airmon_ng_available = False
        self.airodump_available = False
        self.aireplay_available = False
        self.wifite_available = False
        self.wireshark_available = False
        self.kismet_available = False
        self.cached_mon_iface = None
        self.hopping_stop_event = threading.Event()
        self.hopping_thread = None
        self.available_channels = AVAILABLE_CHANNELS
        self.hop_profiles = HOP_PROFILES

        # --- Top: Interface Selection ---
        iface_frame = ttk.Frame(master)
        iface_frame.pack(fill="x", padx=20, pady=8)
        
        lbl_iface = ttk.Label(iface_frame, text="Interface:", font=("Helvetica", 10, "bold"))
        lbl_iface.pack(side="left", pady=5)
        
        self.iface_var = tk.StringVar()
        if self.interfaces:
            self.iface_var.set(self.interface)
            self.iface_menu = ttk.OptionMenu(
                iface_frame, 
                self.iface_var, 
                self.interface, 
                *self.interfaces, 
                command=self.update_interface
            )
        else:
            self.iface_var.set("None Found")
            self.iface_menu = ttk.OptionMenu(
                iface_frame,
                self.iface_var,
                "None Found",
                "None Found",
                command=self.update_interface
            )
            self.iface_menu.config(state="disabled")
            
        self.iface_menu.pack(side="left", fill="x", expand=True, padx=8)

        self.btn_refresh = ttk.Button(iface_frame, text="↻", width=3, command=self.refresh_interfaces)
        self.btn_refresh.pack(side="right")

        # --- Middle: Custom Glowing Toggle Switch Panel ---
        self.switch_frame = tk.Frame(master, height=84, bg="#1a1a1a", relief="groove", borderwidth=1)
        self.switch_frame.pack(fill="x", side="top", padx=20, pady=4)
        self.switch_frame.pack_propagate(False)

        toggle_container = tk.Frame(self.switch_frame, bg="#1a1a1a")
        toggle_container.pack(expand=True)

        self.lbl_off = tk.Label(
            toggle_container, 
            text="OFF", 
            font=("Helvetica", 16, "bold"),
            bg="#1a1a1a",
            cursor="hand2"
        )
        self.lbl_off.pack(side="left", padx=15)

        self.toggle_widget = CanvasToggle(
            toggle_container, 
            width=80, 
            height=34, 
            callback=self.toggle_monitor
        )
        self.toggle_widget.pack(side="left", padx=5)

        self.lbl_on = tk.Label(
            toggle_container, 
            text="ON", 
            font=("Helvetica", 16, "bold"),
            bg="#1a1a1a",
            cursor="hand2"
        )
        self.lbl_on.pack(side="left", padx=15)

        # Bind labels for clicking
        self.lbl_off.bind("<Button-1>", lambda e: self.toggle_monitor())
        self.lbl_on.bind("<Button-1>", lambda e: self.toggle_monitor())

        # --- Live Channel & Interface Details Panel ---
        self.channel_frame = tk.Frame(master, bg="#252525", relief="groove", borderwidth=1)
        self.channel_frame.pack(fill="x", padx=20, pady=4)

        lbl_details_header = ttk.Label(self.channel_frame, text="Telemetry & Channel Control", font=("Helvetica", 9, "bold"))
        lbl_details_header.pack(pady=(4, 1))

        self.lbl_hw_info = ttk.Label(self.channel_frame, text="Driver: --  |  Hardware: --", font=("Helvetica", 8))
        self.lbl_hw_info.pack(pady=1)

        self.lbl_mac_info = ttk.Label(self.channel_frame, text="MAC: --:--:--:--:--:--  |  TX: --", font=("Helvetica", 8))
        self.lbl_mac_info.pack(pady=1)

        self.lbl_chan_info = ttk.Label(self.channel_frame, text="Mode: --  |  Channel: --", font=("Helvetica", 9, "bold"))
        self.lbl_chan_info.pack(pady=1)

        # Manual Channel Row
        chan_ctrl_subframe = ttk.Frame(self.channel_frame)
        chan_ctrl_subframe.pack(pady=2)

        lbl_set_chan = ttk.Label(chan_ctrl_subframe, text="Manual Ch:", font=("Helvetica", 9))
        lbl_set_chan.pack(side="left", padx=2)

        self.chan_var = tk.StringVar(value="1")
        self.chan_spin = ttk.Spinbox(
            chan_ctrl_subframe,
            values=self.available_channels,
            textvariable=self.chan_var,
            width=5
        )
        self.chan_spin.pack(side="left", padx=2)

        self.btn_set_chan = ttk.Button(
            chan_ctrl_subframe,
            text="Set",
            width=5,
            command=self.set_channel_click
        )
        self.btn_set_chan.pack(side="left", padx=4)

        # Hopping Control Row
        hop_subframe = ttk.Frame(self.channel_frame)
        hop_subframe.pack(pady=(2, 5))

        self.hop_var = tk.BooleanVar(value=False)
        self.chk_hop = ttk.Checkbutton(
            hop_subframe,
            text="Auto Hop",
            variable=self.hop_var,
            command=self.toggle_channel_hopping
        )
        self.chk_hop.pack(side="left", padx=4)

        self.hop_profile_var = tk.StringVar(value="1, 6, 11 (2.4GHz)")
        self.profile_menu = ttk.OptionMenu(
            hop_subframe,
            self.hop_profile_var,
            "1, 6, 11 (2.4GHz)",
            *list(self.hop_profiles.keys())
        )
        self.profile_menu.pack(side="left", padx=4)

        # --- Bottom: Status and Tools ---
        
        # Status Label
        self.status_var = tk.StringVar(master=master)
        self.status_var.set("Ready")
        self.status_label = ttk.Label(
            master, 
            textvariable=self.status_var, 
            font=("Helvetica", 9, "italic"), 
            wraplength=380,
            justify="center"
        )
        self.status_label.pack(pady=4)

        # Toggle Tools Button
        self.tools_visible = not self.is_small_screen
        toggle_btn_text = "Hide Quick Tools ▲" if self.tools_visible else "Show Quick Tools ▼"
        self.btn_toggle_tools = ttk.Button(
            master, 
            text=toggle_btn_text, 
            command=self.toggle_tools_section,
            width=22
        )
        self.btn_toggle_tools.pack(pady=2)

        # Tools Container (collapsible)
        self.tools_container = ttk.Frame(master)
        if self.tools_visible:
            self.tools_container.pack(fill="x", pady=2)

        # Tools Section
        separator = ttk.Separator(self.tools_container, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=2)

        lbl_tools = ttk.Label(self.tools_container, text="Security Audit Tools", font=("Helvetica", 10, "bold"))
        lbl_tools.pack(pady=2)

        self.tools_frame = ttk.Frame(self.tools_container)
        self.tools_frame.pack(pady=2)

        # Grid of Quick Tools
        self.btn_airodump = ttk.Button(self.tools_frame, text="Launch Airodump-ng", width=19, command=self.run_airodump)
        self.btn_airodump.grid(row=0, column=0, padx=4, pady=3)

        self.btn_injection_test = ttk.Button(self.tools_frame, text="Test Injection", width=19, command=self.run_packet_injection_test)
        self.btn_injection_test.grid(row=0, column=1, padx=4, pady=3)

        self.btn_wifite = ttk.Button(self.tools_frame, text="Launch Wifite", width=19, command=self.run_wifite)
        self.btn_wifite.grid(row=1, column=0, padx=4, pady=3)

        self.btn_wireshark = ttk.Button(self.tools_frame, text="Launch Wireshark", width=19, command=self.run_wireshark)
        self.btn_wireshark.grid(row=1, column=1, padx=4, pady=3)

        self.btn_kismet = ttk.Button(self.tools_frame, text="Launch Kismet", width=40, command=self.run_kismet)
        self.btn_kismet.grid(row=2, column=0, columnspan=2, pady=3, sticky="ew")

        # Initial check & Tool configurations
        self.check_tools_availability()
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = "#1e1e1e"
        fg_color = "#f0f0f0"
        card_bg = "#2d2d2d"
        accent_color = "#3a7ebf"
        
        style.configure('.', background=bg_color, foreground=fg_color, fieldbackground=card_bg)
        
        # General configurations
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Helvetica', 10))
        style.configure('TFrame', background=bg_color)
        style.configure('TSeparator', background='#3e3e3e')
        style.configure('TCheckbutton', background=bg_color, foreground=fg_color)
        style.configure('TSpinbox', fieldbackground=card_bg, foreground=fg_color, arrowcolor=fg_color)
        
        # OptionMenu / Dropdown
        style.configure('TMenubutton', background=card_bg, foreground=fg_color, bordercolor='#3e3e3e', padding=5)
        style.map('TMenubutton',
            background=[('active', '#424242'), ('disabled', '#151515')],
            foreground=[('active', '#ffffff'), ('disabled', '#777777')]
        )
        
        # Standard Buttons
        style.configure('TButton', background=card_bg, foreground=fg_color, bordercolor='#3e3e3e', focuscolor=accent_color, padding=5)
        style.map('TButton',
            background=[('active', '#424242'), ('disabled', '#151515')],
            foreground=[('active', '#ffffff'), ('disabled', '#777777')],
            bordercolor=[('disabled', '#252525')]
        )

    def toggle_tools_section(self):
        """Toggles the visibility of the tools section and resizes the window."""
        if self.tools_visible:
            self.tools_container.pack_forget()
            self.btn_toggle_tools.config(text="Show Quick Tools ▼")
            self.tools_visible = False
            self.master.geometry("440x410")
        else:
            self.tools_container.pack(fill="x", pady=2)
            self.btn_toggle_tools.config(text="Hide Quick Tools ▲")
            self.tools_visible = True
            self.master.geometry("440x640")

    def check_tools_availability(self):
        """Verifies if the security utilities are installed on the system."""
        self.airmon_ng_available = shutil.which("airmon-ng") is not None
        self.airodump_available = shutil.which("airodump-ng") is not None
        self.aireplay_available = shutil.which("aireplay-ng") is not None
        self.wifite_available = shutil.which("wifite") is not None
        self.wireshark_available = shutil.which("wireshark") is not None
        self.kismet_available = shutil.which("kismet") is not None
        
        if self.airodump_available:
            self.btn_airodump.config(state="normal", text="Launch Airodump-ng")
        else:
            self.btn_airodump.config(state="disabled", text="Airodump (N/A)")

        if self.aireplay_available:
            self.btn_injection_test.config(state="normal", text="Test Injection")
        else:
            self.btn_injection_test.config(state="disabled", text="Injection Test (N/A)")

        if self.wifite_available:
            self.btn_wifite.config(state="normal", text="Launch Wifite")
        else:
            self.btn_wifite.config(state="disabled", text="Wifite (N/A)")
            
        if self.wireshark_available:
            self.btn_wireshark.config(state="normal", text="Launch Wireshark")
        else:
            self.btn_wireshark.config(state="disabled", text="Wireshark (N/A)")
            
        if self.kismet_available:
            self.btn_kismet.config(state="normal", text="Launch Kismet")
        else:
            self.btn_kismet.config(state="disabled", text="Kismet (N/A)")

    def refresh_interfaces(self):
        if self.is_transitioning:
            return
            
        self.interfaces = detect_interfaces()
        if not self.interfaces:
            self.status_var.set("No wireless interfaces found.")
            self.iface_var.set("None Found")
            self.iface_menu.config(state="disabled")
            return
        
        # Re-build OptionMenu menu items
        menu = self.iface_menu["menu"]
        menu.delete(0, "end")
        for iface in self.interfaces:
            menu.add_command(label=iface, command=lambda v=iface: self.update_interface(v))
        
        self.iface_menu.config(state="normal")
        if self.interface not in self.interfaces:
            self.interface = self.interfaces[0]
            self.iface_var.set(self.interface)
        else:
            self.iface_var.set(self.interface)
        
        self.cached_mon_iface = None
        self.status_var.set("Interfaces refreshed.")
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def update_interface(self, val):
        self.interface = val
        self.iface_var.set(val)
        self.cached_mon_iface = None
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def update_interface_details_ui(self):
        """Refreshes live MAC, channel, frequency, txpower, hardware, and active network in UI."""
        active_iface = self.get_active_monitor_interface() or self.interface
        details = get_interface_details(active_iface)
        
        # Hardware & Driver info
        drv_str = details.get("driver", "Unknown")
        chip_str = f" ({details['chipset']})" if details.get("chipset") else ""
        self.lbl_hw_info.config(text=f"Driver: {drv_str}{chip_str}")
        
        mac_str = details.get("mac", "Unknown") if details.get("mac") != "Unknown" else "--:--:--:--:--:--"
        tx_str = details.get("txpower", "N/A") if details.get("txpower") else "N/A"
        self.lbl_mac_info.config(text=f"MAC: {mac_str}  |  TX: {tx_str}")
        
        chan = details.get("channel", "Unknown")
        freq = f" ({details['freq']})" if details.get("freq") else ""
        mode = details.get("mode", "Unknown").upper()
        
        default_gw = get_default_gateway_interface()
        gw_note = " [Active Gateway]" if self.interface == default_gw else ""
        ssid_note = f" (SSID: {details['ssid']})" if details.get("ssid") else ""
        
        self.lbl_chan_info.config(text=f"Mode: {mode}{ssid_note}{gw_note}  |  Ch: {chan}{freq}")
        
        if chan != "Unknown" and not self.is_channel_hopping and isinstance(chan, str):
            self.chan_var.set(chan)

    def set_channel_click(self):
        """Handler for 'Set' channel button."""
        chan = self.chan_var.get().strip()
        if not chan.isdigit():
            messagebox.showwarning("Invalid Channel", "Please select or enter a valid numeric channel.")
            return
            
        active_iface = self.get_active_monitor_interface() or self.interface
        self.set_interface_channel(active_iface, chan)

    def set_interface_channel(self, iface, channel):
        """Sets the operating channel on the specified interface."""
        def _run():
            try:
                res = run_cmd(["iw", "dev", iface, "set", "channel", str(channel)], timeout=5)
                if res.returncode != 0:
                    run_cmd(["iwconfig", iface, "channel", str(channel)], timeout=5)
                self.master.after(0, self.update_interface_details_ui)
                self.master.after(0, lambda: self.status_var.set(f"Channel set to {channel} on {iface}"))
            except Exception as e:
                logging.error(f"Failed to set channel {channel} on {iface}: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def toggle_channel_hopping(self):
        """Enables or disables automatic channel hopping across selected profile."""
        if self.hop_var.get():
            if not self.is_monitor_on:
                messagebox.showwarning("Monitor Mode Required", "Channel hopping requires monitor mode to be active.")
                self.hop_var.set(False)
                return
            self.start_channel_hopping()
        else:
            self.stop_channel_hopping()

    def start_channel_hopping(self):
        self.is_channel_hopping = True
        self.hopping_stop_event.clear()
        self.btn_set_chan.config(state="disabled")
        self.chan_spin.config(state="disabled")
        self.profile_menu.config(state="disabled")
        
        self.hopping_thread = threading.Thread(target=self._channel_hopping_loop, daemon=True)
        self.hopping_thread.start()
        profile_name = self.hop_profile_var.get()
        self.status_var.set(f"Channel Hopping active ({profile_name})...")

    def stop_channel_hopping(self):
        self.is_channel_hopping = False
        self.hopping_stop_event.set()
        self.btn_set_chan.config(state="normal")
        self.chan_spin.config(state="normal")
        self.profile_menu.config(state="normal")
        self.hop_var.set(False)
        self.update_interface_details_ui()

    def _channel_hopping_loop(self):
        idx = 0
        active_iface = self.get_active_monitor_interface() or self.interface
        while not self.hopping_stop_event.is_set():
            if self.is_monitor_on:
                profile_name = self.hop_profile_var.get()
                hop_channels = self.hop_profiles.get(profile_name, ["1", "6", "11"])
                target_chan = hop_channels[idx % len(hop_channels)]
                try:
                    res = run_cmd(["iw", "dev", active_iface, "set", "channel", target_chan], timeout=2)
                    if res.returncode != 0:
                        run_cmd(["iwconfig", active_iface, "channel", target_chan], timeout=2)
                except Exception:
                    # In case monitor interface changed name, re-query once
                    active_iface = self.get_active_monitor_interface() or self.interface
                self.master.after(0, lambda c=target_chan: self.lbl_chan_info.config(text=f"Mode: MONITOR  |  Channel: {c} (Hopping...)"))
                idx += 1
            self.hopping_stop_event.wait(1.5)

    def check_monitor_mode(self):
        """Checks if the interface or its mon counterpart is in monitor mode."""
        if not self.airmon_ng_available:
            self.set_switch_state(False)
            self.status_var.set("Error: airmon-ng not found. Please install aircrack-ng.")
            return

        status = get_interfaces_status()
        
        if status.get(self.interface) == "monitor":
            self.cached_mon_iface = self.interface
            self.set_switch_state(True)
        elif status.get(f"{self.interface}mon") == "monitor":
            self.cached_mon_iface = f"{self.interface}mon"
            self.set_switch_state(True)
        elif status.get(f"{self.interface}.mon") == "monitor":
            self.cached_mon_iface = f"{self.interface}.mon"
            self.set_switch_state(True)
        else:
            self.cached_mon_iface = None
            self.set_switch_state(False)

    def get_active_monitor_interface(self):
        """Finds the actual interface name in monitor mode for the selected base interface."""
        if self.cached_mon_iface:
            return self.cached_mon_iface

        status = get_interfaces_status()
        if status.get(self.interface) == "monitor":
            self.cached_mon_iface = self.interface
            return self.interface
            
        possible_names = [
            f"{self.interface}mon",
            f"{self.interface}.mon",
            f"mon{self.interface}",
        ]
        for name in possible_names:
            if status.get(name) == "monitor":
                self.cached_mon_iface = name
                return name
                
        for iface, mode in status.items():
            if mode == "monitor" and (self.interface in iface or iface.startswith("mon")):
                self.cached_mon_iface = iface
                return iface
        return None

    def set_switch_state(self, is_on):
        self.is_monitor_on = is_on
        self.toggle_widget.set_state(is_on)
        
        if is_on:
            self.lbl_on.config(fg="#39ff14")     # Glowing neon green
            self.lbl_off.config(fg="#502020")    # Dim red
            self.status_var.set(f"Monitoring active on {self.interface}")
        else:
            self.lbl_off.config(fg="#ff1744")    # Glowing red
            self.lbl_on.config(fg="#204020")     # Dim green
            self.status_var.set(f"{self.interface} is in Managed Mode")
            self.stop_channel_hopping()
            
        self.update_interface_details_ui()

    def toggle_monitor(self):
        if self.is_transitioning:
            return
            
        if not self.airmon_ng_available:
            messagebox.showerror("Dependency Error", "airmon-ng is not installed.\n\nPlease install aircrack-ng:\nsudo apt install aircrack-ng")
            return
            
        if self.is_monitor_on:
            self.disable_monitor()
        else:
            self.enable_monitor()

    def enable_monitor(self):
        default_gw = get_default_gateway_interface()
        confirm_msg = f"Enable monitor mode on {self.interface}?\n\nThis will disconnect current WiFi connections."
        if default_gw == self.interface:
            confirm_msg = (
                f"⚠️ WARNING: {self.interface} is your ACTIVE network / default gateway connection!\n\n"
                f"Enabling monitor mode will terminate active SSH, VNC, and Internet sessions.\n\n"
                f"Do you want to proceed?"
            )
            
        if not messagebox.askyesno("Confirm Monitor Mode", confirm_msg):
            return
            
        self.is_transitioning = True
        self.btn_refresh.config(state="disabled")
        self.iface_menu.config(state="disabled")
        self.status_var.set("Transitioning: Starting...")
        
        thread = threading.Thread(target=self._run_enable_monitor)
        thread.start()

    def _run_enable_monitor(self):
        try:
            # Step 1: Kill conflicting processes
            self.run_command_in_thread(["sudo", "airmon-ng", "check", "kill"] if os.geteuid() != 0 else ["airmon-ng", "check", "kill"], "Kill conflicting processes")
            
            # Step 2: Start monitor mode
            self.run_command_in_thread(["sudo", "airmon-ng", "start", self.interface] if os.geteuid() != 0 else ["airmon-ng", "start", self.interface], f"Enable monitor mode on {self.interface}")
            
            self.cached_mon_iface = None
            self.master.after(0, lambda: messagebox.showinfo("Success", f"Monitor mode enabled successfully on {self.interface}."))
        except Exception as e:
            self.master.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to enable monitor mode:\n{err}"))
        finally:
            self.master.after(0, self._on_transition_finished)

    def disable_monitor(self):
        if not messagebox.askyesno("Confirm", "Disable monitor mode and restore networking?"):
            return
            
        self.is_transitioning = True
        self.btn_refresh.config(state="disabled")
        self.iface_menu.config(state="disabled")
        self.status_var.set("Transitioning: Stopping...")
        
        thread = threading.Thread(target=self._run_disable_monitor)
        thread.start()

    def _run_disable_monitor(self):
        try:
            self.stop_channel_hopping()
            active_mon = self.get_active_monitor_interface() or self.interface
            stop_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stop_monitor_mode.sh")
            self.run_command_in_thread(["sudo", "bash", stop_script, active_mon] if os.geteuid() != 0 else ["bash", stop_script, active_mon], "Disable monitor mode")
            
            self.cached_mon_iface = None
            self.master.after(0, lambda: messagebox.showinfo("Success", "Monitor mode disabled. Network services restored."))
        except Exception as e:
            self.master.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to disable monitor mode:\n{err}"))
        finally:
            self.master.after(0, self._on_transition_finished)

    def run_command_in_thread(self, cmd_list, description):
        logging.info(f"Running: {' '.join(cmd_list)}")
        self.master.after(0, lambda: self.status_var.set(f"Executing: {description}..."))
        
        try:
            result = subprocess.run(cmd_list, capture_output=True, timeout=30)
            if result.returncode != 0:
                err_msg = result.stderr.decode(errors='replace').strip() if result.stderr else "Unknown error"
                raise RuntimeError(f"{description} failed (Code {result.returncode}).\n{err_msg}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{description} timed out after 30 seconds.")
            
        self.master.after(0, lambda: self.status_var.set(f"Completed: {description}"))

    def _on_transition_finished(self):
        self.is_transitioning = False
        self.btn_refresh.config(state="normal")
        self.iface_menu.config(state="normal")
        self.cached_mon_iface = None
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def launch_in_terminal(self, cmd, title):
        term = None
        # Check comprehensive list of Linux & Raspberry Pi terminal emulators
        for t in [
            "lxterminal", "x-terminal-emulator", "gnome-terminal", "xfce4-terminal",
            "mate-terminal", "konsole", "terminator", "tilix", "alacritty",
            "kitty", "foot", "xterm"
        ]:
            if shutil.which(t):
                term = t
                break
        
        if not term:
            messagebox.showerror("Error", "No terminal emulator found. Please install lxterminal, xterm, or gnome-terminal.")
            return

        # Prepare shell command
        elevated_cmd = cmd if (os.geteuid() == 0 or cmd.startswith("sudo ")) else f"sudo {cmd}"
        # Keep window open for inspection if testing injection
        if "aireplay-ng" in cmd or title == "Packet Injection Test":
            shell_exec = f"{elevated_cmd}; echo; echo '[EZMonitorMode] Test finished.'; read -p 'Press Enter to close window...' dummy"
        else:
            shell_exec = f"{elevated_cmd}"
        
        user = os.environ.get("SUDO_USER")
        if not user and os.environ.get("PKEXEC_UID"):
            try:
                import pwd
                user = pwd.getpwuid(int(os.environ.get("PKEXEC_UID"))).pw_name
            except Exception:
                pass
                
        try:
            if term in ["gnome-terminal", "mate-terminal", "tilix", "konsole"]:
                term_cmd = [term, "--", "bash", "-c", shell_exec]
            elif term in ["alacritty", "foot"]:
                term_cmd = [term, "-e", "bash", "-c", shell_exec]
            elif term == "kitty":
                term_cmd = [term, "bash", "-c", shell_exec]
            else:
                # lxterminal, xterm, xfce4-terminal
                term_cmd = [term, "-e", f"bash -c {shlex.quote(shell_exec)}"]
                
            if user and os.geteuid() == 0:
                # Spawn terminal emulator as non-root user with desktop environments preserved
                display = os.environ.get("DISPLAY", ":0")
                xauth = os.environ.get("XAUTHORITY", "")
                wayland = os.environ.get("WAYLAND_DISPLAY", "")
                xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", "")
                env_args = [f"DISPLAY={display}"]
                if xauth:
                    env_args.append(f"XAUTHORITY={xauth}")
                if wayland:
                    env_args.append(f"WAYLAND_DISPLAY={wayland}")
                if xdg_runtime:
                    env_args.append(f"XDG_RUNTIME_DIR={xdg_runtime}")
                term_cmd = ["sudo", "-u", user, "env"] + env_args + term_cmd
                
            subprocess.Popen(term_cmd)
            self.status_var.set(f"Launched {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {title}:\n{e}")

    def run_airodump(self):
        mon_iface = self.get_active_monitor_interface()
        target = mon_iface or self.interface
        cmd = f"airodump-ng {target}"
        self.launch_in_terminal(cmd, "Airodump-ng")

    def run_packet_injection_test(self):
        mon_iface = self.get_active_monitor_interface()
        if not mon_iface and not self.is_monitor_on:
            messagebox.showwarning("Monitor Mode Required", "Please enable Monitor Mode before running the Packet Injection test.")
            return
        target = mon_iface or self.interface
        cmd = f"aireplay-ng --test {target}"
        self.launch_in_terminal(cmd, "Packet Injection Test")

    def run_wifite(self):
        mon_iface = self.get_active_monitor_interface()
        cmd = f"wifite -i {mon_iface}" if mon_iface else "wifite"
        self.launch_in_terminal(cmd, "Wifite")
 
    def run_kismet(self):
        mon_iface = self.get_active_monitor_interface()
        cmd = f"kismet -c {mon_iface}" if mon_iface else "kismet"
        self.launch_in_terminal(cmd, "Kismet")
 
    def run_wireshark(self):
        try:
            mon_iface = self.get_active_monitor_interface()
            cmd_args = ["wireshark", "-i", mon_iface] if mon_iface else ["wireshark"]
            if os.geteuid() != 0:
                cmd_args = ["sudo"] + cmd_args
            user = os.environ.get("SUDO_USER")
            if not user and os.environ.get("PKEXEC_UID"):
                try:
                    import pwd
                    user = pwd.getpwuid(int(os.environ.get("PKEXEC_UID"))).pw_name
                except Exception:
                    pass
            if user and os.geteuid() == 0:
                display = os.environ.get("DISPLAY", ":0")
                xauth = os.environ.get("XAUTHORITY", "")
                wayland = os.environ.get("WAYLAND_DISPLAY", "")
                xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", "")
                env_args = [f"DISPLAY={display}"]
                if xauth:
                    env_args.append(f"XAUTHORITY={xauth}")
                if wayland:
                    env_args.append(f"WAYLAND_DISPLAY={wayland}")
                if xdg_runtime:
                    env_args.append(f"XDG_RUNTIME_DIR={xdg_runtime}")
                cmd_args = ["sudo", "-u", user, "env"] + env_args + cmd_args
            subprocess.Popen(cmd_args)
            self.status_var.set("Launched Wireshark")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Wireshark:\n{e}")

def cli_main(args):
    """Headless CLI mode for SSH, headless Pi, and scripting environments."""
    interfaces = detect_interfaces()
    target_iface = args.iface or (interfaces[0] if interfaces else "wlan0")

    if args.status:
        print(f"\n==========================================")
        print(f" EZMonitorMode v{VERSION} - Telemetry Status")
        print(f"==========================================")
        status = get_interfaces_status()
        gw = get_default_gateway_interface()
        if not interfaces:
            print("No wireless interfaces detected.")
            return 1

        for iface in interfaces:
            details = get_interface_details(iface)
            is_gw = " [ACTIVE GATEWAY]" if iface == gw else ""
            mode = status.get(iface, details.get("mode", "unknown")).upper()
            driver = details.get("driver", "unknown")
            chipset = f" ({details['chipset']})" if details.get("chipset") else ""
            ssid = f" [SSID: {details['ssid']}]" if details.get("ssid") else ""
            print(f"Interface: {iface}{is_gw}")
            print(f"  Driver:   {driver}{chipset}")
            print(f"  Mode:     {mode}{ssid}")
            print(f"  MAC:      {details.get('mac', '--')}")
            print(f"  Channel:  {details.get('channel', '--')} {details.get('freq', '')}")
            print(f"  TX-Power: {details.get('txpower', '--')}")
            print(f"  Link:     {details.get('operstate', '--')}")
            print()
        return 0

    if args.channel:
        chan = args.channel.strip()
        print(f"Setting channel {chan} on {target_iface}...")
        res = run_cmd(["iw", "dev", target_iface, "set", "channel", chan])
        if res.returncode != 0:
            res = run_cmd(["iwconfig", target_iface, "channel", chan])
        if res.returncode == 0:
            print(f"Success: {target_iface} set to channel {chan}.")
            return 0
        else:
            print(f"Error setting channel on {target_iface}: {res.stderr.decode(errors='replace')}")
            return 1

    if args.test_injection:
        print(f"Running packet injection test on {target_iface}...")
        cmd = ["aireplay-ng", "--test", target_iface]
        if os.geteuid() != 0:
            cmd = ["sudo"] + cmd
        return subprocess.run(cmd).returncode

    if args.on:
        print(f"Enabling monitor mode on {target_iface}...")
        gw = get_default_gateway_interface()
        if gw == target_iface and not args.force:
            print(f"⚠️  WARNING: {target_iface} is your active network/default gateway interface!")
            print("Enabling monitor mode will disconnect your active connection.")
            print("To proceed anyway, re-run with --force (e.g. ezmonitormode --on --force)")
            return 1

        print("Killing conflicting processes with airmon-ng check kill...")
        run_cmd(["airmon-ng", "check", "kill"])
        print(f"Switching {target_iface} into monitor mode...")
        res = run_cmd(["airmon-ng", "start", target_iface])
        print(res.stdout.decode(errors='replace'))
        return res.returncode

    if args.off:
        print(f"Disabling monitor mode and restoring networking...")
        stop_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stop_monitor_mode.sh")
        res = run_cmd(["bash", stop_script, target_iface])
        print(res.stdout.decode(errors='replace'))
        return res.returncode

    return 0

def main():
    parser = argparse.ArgumentParser(
        description=f"EZMonitorMode v{VERSION} - Wireless Monitor Mode Manager for Raspberry Pi & Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--status", "-s", action="store_true", help="Display real-time interface status, driver, and telemetry")
    parser.add_argument("--on", "-e", action="store_true", help="Enable monitor mode on wireless interface")
    parser.add_argument("--off", "-d", action="store_true", help="Disable monitor mode and cleanly restore network services")
    parser.add_argument("--channel", "-c", metavar="CH", help="Set wireless channel (e.g. 1, 6, 11, 36, 153)")
    parser.add_argument("--test-injection", "-t", action="store_true", help="Run aireplay-ng frame injection test")
    parser.add_argument("--interface", "-i", dest="iface", metavar="IFACE", help="Target interface (defaults to auto-detected)")
    parser.add_argument("--force", "-f", action="store_true", help="Bypass safety warnings (e.g. active gateway check)")
    
    args, unknown = parser.parse_known_args()

    # If any CLI argument is passed, operate in headless CLI mode
    if args.status or args.on or args.off or args.channel or args.test_injection:
        sys.exit(cli_main(args))

    # Otherwise launch Tkinter GUI
    if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ:
        if os.path.exists("/tmp/.X11-unix/X0"):
            os.environ["DISPLAY"] = ":0"
        else:
            print(f"EZMonitorMode v{VERSION}")
            print("Notice: No graphical display detected.")
            print("For headless / SSH command-line usage, run with flags:")
            print("  ezmonitormode --status")
            print("  ezmonitormode --on [-i iface] [--force]")
            print("  ezmonitormode --off [-i iface]")
            print("  ezmonitormode --channel <ch> [-i iface]")
            print("  ezmonitormode --test-injection [-i iface]")
            sys.exit(1)

    try:
        root = tk.Tk()
        interfaces = detect_interfaces()
        app = MonitorGUI(root, interfaces)
        root.mainloop()
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
