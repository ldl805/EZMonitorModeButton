#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import shutil

# Configuration
INTERFACE = "wlan1"
MON_INTERFACE = "wlan1mon"
# Look for script in the same directory as the python script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOP_SCRIPT = os.path.join(BASE_DIR, "stop_monitor_mode.sh")

class MonitorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Monitor Mode Control")
        master.geometry("400x450")
        master.resizable(False, False)

        # Monitor Mode State
        self.is_monitor_on = False

        # --- Top Half: The "Light Switch" ---
        self.switch_frame = tk.Frame(master, height=200)
        self.switch_frame.pack(fill="x", side="top", padx=10, pady=10)
        self.switch_frame.pack_propagate(False) # Keep height

        self.btn_switch = tk.Button(
            self.switch_frame, 
            text="MONITOR MODE\nOFF", 
            font=("Helvetica", 20, "bold"),
            bg="#ff4444", 
            fg="white",
            activebackground="#cc0000",
            activeforeground="white",
            command=self.toggle_monitor
        )
        self.btn_switch.pack(fill="both", expand=True)

        # --- Bottom Half: Status and Tools ---
        
        # Status Label
        self.status_var = tk.StringVar(master=master)
        self.status_var.set("Ready")
        self.status_label = tk.Label(master, textvariable=self.status_var, font=("Helvetica", 10, "italic"))
        self.status_label.pack(pady=5)

        # Tools Label
        self.tools_label = tk.Label(master, text="Quick Tools", font=("Helvetica", 12, "bold"))
        self.tools_label.pack(pady=(10, 5))

        # Tools Frame
        self.tools_frame = tk.Frame(master)
        self.tools_frame.pack(pady=5)

        # Tool Buttons
        self.btn_wifite = tk.Button(self.tools_frame, text="Wifite", width=12, height=2, command=self.run_wifite)
        self.btn_wifite.grid(row=0, column=0, padx=5, pady=5)

        self.btn_wireshark = tk.Button(self.tools_frame, text="Wireshark", width=12, height=2, command=self.run_wireshark)
        self.btn_wireshark.grid(row=0, column=1, padx=5, pady=5)

        self.btn_kismet = tk.Button(self.tools_frame, text="Kismet", width=12, height=2, command=self.run_kismet)
        self.btn_kismet.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        # Initial check
        self.check_monitor_mode()

    def check_monitor_mode(self):
        """Checks if any interface is in monitor mode."""
        try:
            # Check for common monitor interface names or 'Mode:Monitor' in iwconfig
            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()
            if "Mode:Monitor" in output:
                self.set_switch_state(True)
            else:
                self.set_switch_state(False)
        except Exception:
            # Fallback if iwconfig fails
            self.set_switch_state(False)

    def set_switch_state(self, is_on):
        self.is_monitor_on = is_on
        if is_on:
            self.btn_switch.config(
                text="MONITOR MODE\nON", 
                bg="#44ff44", 
                activebackground="#00cc00",
                fg="black",
                activeforeground="black"
            )
            self.status_var.set("Status: Monitor Mode Enabled")
        else:
            self.btn_switch.config(
                text="MONITOR MODE\nOFF", 
                bg="#ff4444", 
                activebackground="#cc0000",
                fg="white",
                activeforeground="white"
            )
            self.status_var.set("Status: Managed Mode (Monitor Off)")

    def toggle_monitor(self):
        if self.is_monitor_on:
            self.disable_monitor()
        else:
            self.enable_monitor()

    def run_command(self, cmd_list, description):
        """Helper to run commands and update status."""
        self.status_var.set(f"Running: {description}...")
        self.master.update()
        try:
            subprocess.run(cmd_list, check=True)
            self.status_var.set(f"Success: {description}")
            return True
        except subprocess.CalledProcessError as e:
            self.status_var.set(f"Error: {description}")
            messagebox.showerror("Error", f"Failed to run {description}.\nExit code: {e.returncode}")
            return False
        except Exception as e:
            self.status_var.set(f"Error: {description}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            return False

    def enable_monitor(self):
        """Enables monitor mode."""
        if not messagebox.askyesno("Confirm", f"Enable monitor mode on {INTERFACE}?\nThis will kill network processes."):
            return

        # Step 1: Kill conflicting processes
        if not self.run_command(["sudo", "airmon-ng", "check", "kill"], "Kill processes"):
            if not messagebox.askyesno("Warning", "Failed to kill processes. Continue anyway?"):
                return

        # Step 2: Start monitor mode
        if self.run_command(["sudo", "airmon-ng", "start", INTERFACE], "Start Monitor Mode"):
            self.set_switch_state(True)
            messagebox.showinfo("Success", f"Monitor mode enabled.")

    def disable_monitor(self):
        """Disables monitor mode."""
        if not messagebox.askyesno("Confirm", "Disable monitor mode and restore networks?"):
            return
        
        if self.run_command(["sudo", "bash", STOP_SCRIPT], "Disable Monitor & Restore"):
            self.set_switch_state(False)
            messagebox.showinfo("Success", "Monitor mode disabled. Network restarting...")

    def get_terminal(self):
        """Finds a suitable terminal emulator."""
        for t in ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]:
            term = shutil.which(t)
            if term: return term
        return None

    def launch_in_terminal(self, cmd, title):
        term = self.get_terminal()
        if not term:
            messagebox.showerror("Error", "No terminal emulator found.")
            return
        
        full_cmd = [term, "-e", f"sudo {cmd}"]
        try:
            subprocess.Popen(full_cmd)
            self.status_var.set(f"Launched {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {title}:\n{e}")

    def run_wifite(self):
        self.launch_in_terminal("wifite", "Wifite")

    def run_kismet(self):
        self.launch_in_terminal("kismet", "Kismet")

    def run_wireshark(self):
        try:
            subprocess.Popen(["sudo", "wireshark"])
            self.status_var.set("Launched Wireshark")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Wireshark:\n{e}")

def main():
    root = tk.Tk()
    app = MonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
