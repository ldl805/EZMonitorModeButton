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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
VERSION = "1.5.0"

def get_interfaces_status():
    """Detects wireless interfaces and maps them to their mode ('managed', 'monitor')."""
    status = {}
    
    # Try 'iw dev' first (modern standard)
    try:
        output = subprocess.check_output(["iw", "dev"], stderr=subprocess.STDOUT, timeout=5).decode()
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
            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT, timeout=5).decode()
            current_iface = None
            for line in output.split("\n"):
                if not line:
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
    """Detects wireless base interfaces and returns a sorted unique list."""
    status = get_interfaces_status()
    interfaces = list(status.keys())
    
    # Clean up names (e.g. resolve 'wlan0mon' to base name 'wlan0')
    base_interfaces = []
    for iface in interfaces:
        if iface.endswith("mon"):
            base_interfaces.append(iface[:-3])
        else:
            base_interfaces.append(iface)
            
    return sorted(list(set(base_interfaces)))

def get_interface_details(iface):
    """Returns a dict containing interface details: channel, freq, mac, txpower, mode."""
    details = {
        "channel": "Unknown",
        "freq": "",
        "mac": "Unknown",
        "txpower": "",
        "mode": "Unknown"
    }
    if not iface:
        return details
        
    try:
        output = subprocess.check_output(["iw", "dev", iface, "info"], stderr=subprocess.STDOUT, timeout=3).decode()
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("addr "):
                details["mac"] = line.split()[1]
            elif line.startswith("type "):
                details["mode"] = line.split()[1]
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
        output = subprocess.check_output(["iwconfig", iface], stderr=subprocess.STDOUT, timeout=3).decode()
        for line in output.split("\n"):
            if "Mode:" in line:
                mode_part = line.split("Mode:")[1].split()[0]
                details["mode"] = mode_part
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
    """Centers the window on the screen."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
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
        center_window(master, 420, 580)
        master.resizable(False, False)

        # Style Configuration
        self._setup_style()
        self.master.configure(bg="#1e1e1e")
        
        # State
        self.is_monitor_on = False
        self.is_transitioning = False
        self.is_channel_hopping = False
        self.airmon_ng_available = False
        self.wifite_available = False
        self.wireshark_available = False
        self.kismet_available = False
        self.hopping_stop_event = threading.Event()
        self.hopping_thread = None
        self.available_channels = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14",
            "36", "40", "44", "48", "149", "153", "157", "161", "165"
        ]

        # --- Top: Interface Selection ---
        iface_frame = ttk.Frame(master)
        iface_frame.pack(fill="x", padx=20, pady=12)
        
        lbl_iface = ttk.Label(iface_frame, text="Wireless Interface:", font=("Helvetica", 10, "bold"))
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
        self.switch_frame = tk.Frame(master, height=95, bg="#1a1a1a", relief="groove", borderwidth=1)
        self.switch_frame.pack(fill="x", side="top", padx=20, pady=5)
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

        # --- Live Channel & Interface Details Panel (Usability Upgrade) ---
        self.channel_frame = tk.Frame(master, bg="#252525", relief="groove", borderwidth=1)
        self.channel_frame.pack(fill="x", padx=20, pady=5)

        lbl_details_header = ttk.Label(self.channel_frame, text="Interface Status & Channel Control", font=("Helvetica", 9, "bold"))
        lbl_details_header.pack(pady=(4, 2))

        self.lbl_mac_info = ttk.Label(self.channel_frame, text="MAC: --:--:--:--:--:--  |  TX: --", font=("Helvetica", 8))
        self.lbl_mac_info.pack(pady=1)

        self.lbl_chan_info = ttk.Label(self.channel_frame, text="Mode: --  |  Channel: --", font=("Helvetica", 9, "bold"))
        self.lbl_chan_info.pack(pady=1)

        chan_ctrl_subframe = ttk.Frame(self.channel_frame)
        chan_ctrl_subframe.pack(pady=5)

        lbl_set_chan = ttk.Label(chan_ctrl_subframe, text="Ch:", font=("Helvetica", 9))
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

        self.hop_var = tk.BooleanVar(value=False)
        self.chk_hop = ttk.Checkbutton(
            chan_ctrl_subframe,
            text="Auto Hop (1,6,11)",
            variable=self.hop_var,
            command=self.toggle_channel_hopping
        )
        self.chk_hop.pack(side="left", padx=6)

        # --- Bottom: Status and Tools ---
        
        # Status Label
        self.status_var = tk.StringVar(master=master)
        self.status_var.set("Ready")
        self.status_label = ttk.Label(
            master, 
            textvariable=self.status_var, 
            font=("Helvetica", 10, "italic"), 
            wraplength=350,
            justify="center"
        )
        self.status_label.pack(pady=8)

        # Toggle Tools Button
        self.tools_visible = True
        self.btn_toggle_tools = ttk.Button(
            master, 
            text="Hide Quick Tools ▲", 
            command=self.toggle_tools_section,
            width=20
        )
        self.btn_toggle_tools.pack(pady=4)

        # Tools Container (collapsible)
        self.tools_container = ttk.Frame(master)
        self.tools_container.pack(fill="x", pady=4)

        # Tools Section
        separator = ttk.Separator(self.tools_container, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=4)

        lbl_tools = ttk.Label(self.tools_container, text="Quick Tools", font=("Helvetica", 11, "bold"))
        lbl_tools.pack(pady=2)

        self.tools_frame = ttk.Frame(self.tools_container)
        self.tools_frame.pack(pady=4)

        self.btn_wifite = ttk.Button(self.tools_frame, text="Launch Wifite", width=18, command=self.run_wifite)
        self.btn_wifite.grid(row=0, column=0, padx=6, pady=4)

        self.btn_wireshark = ttk.Button(self.tools_frame, text="Launch Wireshark", width=18, command=self.run_wireshark)
        self.btn_wireshark.grid(row=0, column=1, padx=6, pady=4)

        self.btn_kismet = ttk.Button(self.tools_frame, text="Launch Kismet", width=38, command=self.run_kismet)
        self.btn_kismet.grid(row=1, column=0, columnspan=2, pady=6, sticky="ew")

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
            self.master.geometry("420x370")
        else:
            self.tools_container.pack(fill="x", pady=5)
            self.btn_toggle_tools.config(text="Hide Quick Tools ▲")
            self.tools_visible = True
            self.master.geometry("420x580")

    def check_tools_availability(self):
        """Verifies if the security utilities are installed on the system."""
        self.wifite_available = shutil.which("wifite") is not None
        self.wireshark_available = shutil.which("wireshark") is not None
        self.kismet_available = shutil.which("kismet") is not None
        self.airmon_ng_available = shutil.which("airmon-ng") is not None
        
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
        
        self.status_var.set("Interfaces refreshed.")
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def update_interface(self, val):
        self.interface = val
        self.iface_var.set(val)
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def update_interface_details_ui(self):
        """Refreshes live MAC, channel, frequency, and txpower in UI."""
        active_iface = self.get_active_monitor_interface() or self.interface
        details = get_interface_details(active_iface)
        
        mac_str = details["mac"] if details["mac"] != "Unknown" else "--:--:--:--:--:--"
        tx_str = details["txpower"] if details["txpower"] else "N/A"
        self.lbl_mac_info.config(text=f"MAC: {mac_str}  |  TX: {tx_str}")
        
        chan = details["channel"]
        freq = f" ({details['freq']})" if details["freq"] else ""
        mode = details["mode"].upper()
        self.lbl_chan_info.config(text=f"Mode: {mode}  |  Channel: {chan}{freq}")
        
        if chan != "Unknown" and not self.is_channel_hopping:
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
                res = subprocess.run(["sudo", "iw", "dev", iface, "set", "channel", str(channel)], capture_output=True, timeout=5)
                if res.returncode != 0:
                    subprocess.run(["sudo", "iwconfig", iface, "channel", str(channel)], capture_output=True, timeout=5)
                self.master.after(0, self.update_interface_details_ui)
                self.master.after(0, lambda: self.status_var.set(f"Channel set to {channel} on {iface}"))
            except Exception as e:
                logging.error(f"Failed to set channel {channel} on {iface}: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def toggle_channel_hopping(self):
        """Enables or disables automatic channel hopping across channels 1, 6, 11."""
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
        
        self.hopping_thread = threading.Thread(target=self._channel_hopping_loop, daemon=True)
        self.hopping_thread.start()
        self.status_var.set("Channel Hopping active (1, 6, 11)...")

    def stop_channel_hopping(self):
        self.is_channel_hopping = False
        self.hopping_stop_event.set()
        self.btn_set_chan.config(state="normal")
        self.chan_spin.config(state="normal")
        self.hop_var.set(False)
        self.update_interface_details_ui()

    def _channel_hopping_loop(self):
        hop_channels = ["1", "6", "11"]
        idx = 0
        while not self.hopping_stop_event.is_set():
            if self.is_monitor_on:
                active_iface = self.get_active_monitor_interface() or self.interface
                target_chan = hop_channels[idx % len(hop_channels)]
                try:
                    res = subprocess.run(["sudo", "iw", "dev", active_iface, "set", "channel", target_chan], capture_output=True, timeout=2)
                    if res.returncode != 0:
                        subprocess.run(["sudo", "iwconfig", active_iface, "channel", target_chan], capture_output=True, timeout=2)
                except Exception:
                    pass
                self.master.after(0, lambda c=target_chan: self.lbl_chan_info.config(text=f"Mode: MONITOR  |  Channel: {c} (Hopping...)"))
                idx += 1
            self.hopping_stop_event.wait(2.0)

    def check_monitor_mode(self):
        """Checks if the interface or its mon counterpart is in monitor mode."""
        if not self.airmon_ng_available:
            self.set_switch_state(False)
            self.status_var.set("Error: airmon-ng not found. Please install aircrack-ng.")
            return

        status = get_interfaces_status()
        
        if status.get(self.interface) == "monitor":
            self.set_switch_state(True)
        elif status.get(f"{self.interface}mon") == "monitor":
            self.set_switch_state(True)
        else:
            self.set_switch_state(False)

    def get_active_monitor_interface(self):
        """Finds the actual interface name in monitor mode for the selected base interface."""
        status = get_interfaces_status()
        if status.get(self.interface) == "monitor":
            return self.interface
            
        possible_names = [
            f"{self.interface}mon",
            f"{self.interface}.mon",
            f"mon{self.interface}",
        ]
        for name in possible_names:
            if status.get(name) == "monitor":
                return name
                
        for iface, mode in status.items():
            if mode == "monitor" and (self.interface in iface or iface.startswith("mon")):
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
        if not messagebox.askyesno("Confirm", f"Enable monitor mode on {self.interface}?\n\nThis will disconnect current WiFi connections."):
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
            self.run_command_in_thread(["sudo", "airmon-ng", "check", "kill"], "Kill conflicting processes")
            
            # Step 2: Start monitor mode
            self.run_command_in_thread(["sudo", "airmon-ng", "start", self.interface], f"Enable monitor mode on {self.interface}")
            
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
            self.run_command_in_thread(["sudo", "bash", stop_script, active_mon], "Disable monitor mode")
            
            self.master.after(0, lambda: messagebox.showinfo("Success", "Monitor mode disabled. Network services restarted."))
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
        self.check_monitor_mode()
        self.update_interface_details_ui()

    def launch_in_terminal(self, cmd, title):
        term = None
        for t in ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]:
            if shutil.which(t):
                term = t
                break
        
        if not term:
            messagebox.showerror("Error", "No terminal emulator found. Please install xterm or gnome-terminal.")
            return
        
        # Identify original non-root user if running elevated via sudo/pkexec
        user = os.environ.get("SUDO_USER")
        if not user and os.environ.get("PKEXEC_UID"):
            try:
                import pwd
                user = pwd.getpwuid(int(os.environ.get("PKEXEC_UID"))).pw_name
            except Exception:
                pass
                
        try:
            if term in ["gnome-terminal", "konsole"]:
                term_cmd = [term, "--", "sudo", cmd]
            else:
                term_cmd = [term, "-e", f"sudo {cmd}"]
                
            if user and os.geteuid() == 0:
                # Spawn terminal emulator as non-root user with desktop environments preserved
                display = os.environ.get("DISPLAY", ":0")
                xauth = os.environ.get("XAUTHORITY", "")
                env_args = [f"DISPLAY={display}"]
                if xauth:
                    env_args.append(f"XAUTHORITY={xauth}")
                term_cmd = ["sudo", "-u", user, "env"] + env_args + term_cmd
                
            subprocess.Popen(term_cmd)
            self.status_var.set(f"Launched {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {title}:\n{e}")

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
            cmd_args = ["sudo", "wireshark", "-i", mon_iface] if mon_iface else ["sudo", "wireshark"]
            subprocess.Popen(cmd_args)
            self.status_var.set("Launched Wireshark")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Wireshark:\n{e}")

def main():
    if "DISPLAY" not in os.environ:
        if os.path.exists("/tmp/.X11-unix/X0"):
            os.environ["DISPLAY"] = ":0"
        else:
            print("Error: No graphical display detected. EZMonitorMode requires a desktop environment.")
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
