#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import shutil

# Configuration
INTERFACE = "wlan1"
# Look for script in the same directory as the python script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOP_SCRIPT = os.path.join(BASE_DIR, "stop_monitor_mode.sh")

class MonitorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Monitor Mode Control")
        master.geometry("400x350")
        master.resizable(False, False)

        # Title Label
        self.label = tk.Label(master, text="Monitor Mode Switch", font=("Helvetica", 16, "bold"))
        self.label.pack(pady=10)

        # Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = tk.Label(master, textvariable=self.status_var, fg="blue")
        self.status_label.pack(pady=5)

        # Monitor Mode Controls Frame
        self.control_frame = tk.Frame(master, borderwidth=2, relief="groove")
        self.control_frame.pack(pady=10, padx=20, fill="x")

        # ON Button (Enable)
        self.btn_on = tk.Button(self.control_frame, text="ENABLE Monitor Mode", 
                                bg="#90ee90", activebackground="#32cd32", # Light Green -> Lime Green
                                font=("Helvetica", 12, "bold"),
                                command=self.enable_monitor)
        self.btn_on.pack(pady=10, fill="x", padx=10)

        # OFF Button (Disable)
        self.btn_off = tk.Button(self.control_frame, text="DISABLE Monitor Mode", 
                                 bg="#ffcccb", activebackground="#ff6347", # Light Red -> Tomato
                                 font=("Helvetica", 12, "bold"),
                                 command=self.disable_monitor)
        self.btn_off.pack(pady=10, fill="x", padx=10)

        # Tools Label
        self.tools_label = tk.Label(master, text="Tools Shortcuts", font=("Helvetica", 12, "bold"))
        self.tools_label.pack(pady=(15, 5))

        # Tools Frame
        self.tools_frame = tk.Frame(master)
        self.tools_frame.pack(pady=5)

        # Tool Buttons
        self.btn_wifite = tk.Button(self.tools_frame, text="Wifite", width=10, command=self.run_wifite)
        self.btn_wifite.grid(row=0, column=0, padx=5)

        self.btn_wireshark = tk.Button(self.tools_frame, text="Wireshark", width=10, command=self.run_wireshark)
        self.btn_wireshark.grid(row=0, column=1, padx=5)

        self.btn_kismet = tk.Button(self.tools_frame, text="Kismet", width=10, command=self.run_kismet)
        self.btn_kismet.grid(row=0, column=2, padx=5)

    def run_command(self, cmd_list, description):
        """Helper to run commands and update status."""
        self.status_var.set(f"Running: {description}...")
        self.master.update()
        try:
            # check=True will raise CalledProcessError on non-zero exit
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
        """Enables monitor mode (logic from monitor_mode.sh without prompts)."""
        if not messagebox.askyesno("Confirm", f"Enable monitor mode on {INTERFACE}?\nThis will kill network processes."):
            return

        # Step 1: Kill conflicting processes
        if not self.run_command(["sudo", "airmon-ng", "check", "kill"], "Kill processes"):
            if not messagebox.askyesno("Warning", "Failed to kill processes. Continue anyway?"):
                return

        # Step 2: Start monitor mode
        if self.run_command(["sudo", "airmon-ng", "start", INTERFACE], "Start Monitor Mode"):
            messagebox.showinfo("Success", f"Monitor mode enabled on {INTERFACE}.")

    def disable_monitor(self):
        """Disables monitor mode using the stop_monitor_mode.sh script."""
        if not messagebox.askyesno("Confirm", "Disable monitor mode and restore networks?"):
            return
        
        # Call the bash script we created
        if self.run_command(["sudo", "bash", STOP_SCRIPT], "Disable Monitor & Restore"):
            messagebox.showinfo("Success", "Monitor mode disabled. Network restarting...")

    def get_terminal(self):
        """Finds a suitable terminal emulator."""
        term = shutil.which("x-terminal-emulator")
        if not term:
            term = shutil.which("gnome-terminal")
        if not term:
            term = shutil.which("konsole")
        if not term:
            term = shutil.which("xterm")
        return term

    def launch_in_terminal(self, cmd, title):
        term = self.get_terminal()
        if not term:
            messagebox.showerror("Error", "No terminal emulator found (x-terminal-emulator, gnome-terminal, etc).")
            return
        
        # Construct command based on terminal.
        # most accept -e
        full_cmd = [term, "-e", f"sudo {cmd}"]
        # specialized handling if needed, but -e is standard for xterm/gnome-terminal/x-terminal-emulator
        
        try:
            subprocess.Popen(full_cmd) # Non-blocking
            self.status_var.set(f"Launched {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {title}:\n{e}")

    def run_wifite(self):
        self.launch_in_terminal("wifite", "Wifite")

    def run_kismet(self):
        self.launch_in_terminal("kismet", "Kismet")

    def run_wireshark(self):
        try:
            subprocess.Popen(["sudo", "wireshark"]) # Wireshark is GUI
            self.status_var.set("Launched Wireshark")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Wireshark:\n{e}")

def main():
    root = tk.Tk()
    app = MonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
