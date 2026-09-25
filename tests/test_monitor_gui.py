#!/usr/bin/env python3
"""Tests for the monitor_gui module."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ezmonitormode.monitor_gui import (
    MonitorGUI, get_interface_details, VERSION,
    get_default_gateway_interface, get_device_driver_and_chipset,
    run_cmd, cli_main, detect_interfaces
)


class TestMonitorGUI(unittest.TestCase):
    """Test cases for the MonitorGUI class."""

    def setUp(self):
        """Set up test fixtures."""
        # Patch all of tkinter to avoid issues in headless environments
        self.tk_patcher = patch('ezmonitormode.monitor_gui.tk')
        self.mock_tk = self.tk_patcher.start()
        # Ensure separate calls to tk.Label return distinct mocks
        self.mock_tk.Label.side_effect = lambda *args, **kwargs: MagicMock()
        
        self.ttk_patcher = patch('ezmonitormode.monitor_gui.ttk')
        self.mock_ttk = self.ttk_patcher.start()
        
        self.msgbox_patcher = patch('ezmonitormode.monitor_gui.messagebox')
        self.mock_msgbox = self.msgbox_patcher.start()
        
        self.mock_root = MagicMock()
        # Mock winfo_screenwidth/height for center_window
        self.mock_root.winfo_screenwidth.return_value = 1920
        self.mock_root.winfo_screenheight.return_value = 1080
        
        # Patch check_monitor_mode to avoid subprocess call in __init__
        with patch.object(MonitorGUI, 'check_monitor_mode'), \
             patch.object(MonitorGUI, 'update_interface_details_ui'):
            self.gui = MonitorGUI(self.mock_root, ["wlan0", "wlan1"])
            self.gui.airmon_ng_available = True

    def tearDown(self):
        """Clean up test fixtures."""
        self.tk_patcher.stop()
        self.ttk_patcher.stop()
        self.msgbox_patcher.stop()

    def test_gui_initialization(self):
        """Test that MonitorGUI initializes correctly."""
        self.assertIsNotNone(self.gui)
        self.assertEqual(self.gui.master, self.mock_root)
        self.assertEqual(self.gui.interface, "wlan0") # First interface
        self.assertFalse(self.gui.is_monitor_on)

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    @patch('ezmonitormode.monitor_gui.get_interface_details')
    def test_gui_initialization_full_unpatched(self, mock_details, mock_status):
        """Test that MonitorGUI initializes without error when unpatched."""
        mock_status.return_value = {"wlan0": "managed"}
        mock_details.return_value = {"channel": "1", "freq": "2412 MHz", "mac": "00:11:22:33:44:55", "txpower": "20 dBm", "mode": "managed"}
        app = MonitorGUI(self.mock_root, ["wlan0"])
        self.assertIsNotNone(app)
        self.assertTrue(hasattr(app, 'airmon_ng_available'))

    def test_gui_creates_widgets(self):
        """Test that GUI creates expected widgets."""
        self.mock_root.title.assert_called_with(f"EZ Monitor Mode {VERSION}")
        # Check that geometry was set via center_window
        self.mock_root.geometry.assert_called()

    def test_get_terminal_not_needed(self):
        """Test launch_in_terminal handles missing terminal."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None
            self.gui.launch_in_terminal("cmd", "Title")
            self.mock_msgbox.showerror.assert_called()

    def test_get_terminal_lxterminal(self):
        """Test launch_in_terminal uses lxterminal when available."""
        with patch('shutil.which') as mock_which, patch('subprocess.Popen') as mock_popen:
            mock_which.side_effect = lambda t: t == "lxterminal"
            self.gui.launch_in_terminal("airodump-ng wlan0mon", "Airodump-ng")
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertEqual(args[0], "lxterminal")
            self.assertIn("airodump-ng wlan0mon", args[2])

    def test_run_airodump(self):
        """Test run_airodump launches terminal with active monitor interface."""
        with patch.object(self.gui, 'get_active_monitor_interface', return_value="wlan0mon"), \
             patch.object(self.gui, 'launch_in_terminal') as mock_launch:
            self.gui.run_airodump()
            mock_launch.assert_called_once_with("airodump-ng wlan0mon", "Airodump-ng")

    def test_run_packet_injection_test_when_active(self):
        """Test packet injection test launches when monitor mode is active."""
        self.gui.is_monitor_on = True
        with patch.object(self.gui, 'get_active_monitor_interface', return_value="wlan0mon"), \
             patch.object(self.gui, 'launch_in_terminal') as mock_launch:
            self.gui.run_packet_injection_test()
            mock_launch.assert_called_once_with("aireplay-ng --test wlan0mon", "Packet Injection Test")

    def test_run_packet_injection_test_when_off(self):
        """Test packet injection test warns when monitor mode is not active."""
        self.gui.is_monitor_on = False
        with patch.object(self.gui, 'get_active_monitor_interface', return_value=None), \
             patch.object(self.gui, 'launch_in_terminal') as mock_launch:
            self.gui.run_packet_injection_test()
            mock_launch.assert_not_called()
            self.mock_msgbox.showwarning.assert_called_once_with(
                "Monitor Mode Required",
                "Please enable Monitor Mode before running the Packet Injection test."
            )

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test run_command_in_thread with successful execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        self.gui.run_command_in_thread(['echo', 'test'], 'Test Command')
        mock_run.assert_called_once_with(['echo', 'test'], capture_output=True, timeout=30)

    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run):
        """Test run_command_in_thread handles subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['echo', 'test'], timeout=30)
        
        with self.assertRaises(RuntimeError) as ctx:
            self.gui.run_command_in_thread(['echo', 'test'], 'Test Command')
        
        self.assertIn("timed out after 30 seconds", str(ctx.exception))

    def test_set_switch_state_on(self):
        """Test UI updates when monitor mode is ON."""
        with patch.object(self.gui, 'update_interface_details_ui'):
            self.gui.set_switch_state(True)
            self.assertTrue(self.gui.is_monitor_on)
            self.assertTrue(self.gui.toggle_widget.is_on)
            self.gui.lbl_on.config.assert_called_with(fg="#39ff14")
            self.gui.lbl_off.config.assert_called_with(fg="#502020")

    def test_set_switch_state_off(self):
        """Test UI updates when monitor mode is OFF."""
        with patch.object(self.gui, 'update_interface_details_ui'):
            self.gui.set_switch_state(False)
            self.assertFalse(self.gui.is_monitor_on)
            self.assertFalse(self.gui.toggle_widget.is_on)
            self.gui.lbl_off.config.assert_called_with(fg="#ff1744")
            self.gui.lbl_on.config.assert_called_with(fg="#204020")

    def test_toggle_monitor_calls_enable(self):
        """Test toggle calls enable when off."""
        self.gui.is_monitor_on = False
        with patch.object(self.gui, 'enable_monitor') as mock_enable:
            self.gui.toggle_monitor()
            mock_enable.assert_called_once()

    def test_toggle_monitor_calls_disable(self):
        """Test toggle calls disable when on."""
        self.gui.is_monitor_on = True
        self.gui.airmon_ng_available = True
        with patch.object(self.gui, 'disable_monitor') as mock_disable:
            self.gui.toggle_monitor()
            mock_disable.assert_called_once()

    def test_toggle_monitor_no_airmon_ng(self):
        """Test toggle monitor fails gracefully when airmon-ng is not installed."""
        self.gui.airmon_ng_available = False
        with patch.object(self.gui, 'enable_monitor') as mock_enable, \
             patch.object(self.gui, 'disable_monitor') as mock_disable:
            self.gui.toggle_monitor()
            mock_enable.assert_not_called()
            mock_disable.assert_not_called()
            self.mock_msgbox.showerror.assert_called_once_with(
                "Dependency Error",
                "airmon-ng is not installed.\n\nPlease install aircrack-ng:\nsudo apt install aircrack-ng"
            )

    def test_check_monitor_mode_no_airmon_ng(self):
        """Test check_monitor_mode sets status warning when airmon-ng is missing."""
        self.gui.airmon_ng_available = False
        with patch.object(self.gui, 'update_interface_details_ui'):
            self.gui.check_monitor_mode()
            self.gui.status_var.set.assert_called_with("Error: airmon-ng not found. Please install aircrack-ng.")
            self.assertFalse(self.gui.is_monitor_on)

    def test_toggle_tools_section(self):
        """Test toggling the tools section visibility and geometry."""
        self.assertTrue(self.gui.tools_visible)
        
        # Collapse tools
        self.gui.toggle_tools_section()
        self.assertFalse(self.gui.tools_visible)
        self.gui.tools_container.pack_forget.assert_called_once()
        self.gui.btn_toggle_tools.config.assert_called_with(text="Show Quick Tools ▼")
        self.mock_root.geometry.assert_called_with("440x410")
        
        # Expand tools
        self.gui.toggle_tools_section()
        self.assertTrue(self.gui.tools_visible)
        self.gui.tools_container.pack.assert_called_with(fill="x", pady=2)
        self.gui.btn_toggle_tools.config.assert_called_with(text="Hide Quick Tools ▲")
        self.mock_root.geometry.assert_called_with("440x640")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    def test_get_active_monitor_interface_direct(self, mock_status):
        """Test get_active_monitor_interface when the base interface itself is in monitor mode."""
        self.gui.interface = "wlan0"
        mock_status.return_value = {"wlan0": "monitor"}
        self.assertEqual(self.gui.get_active_monitor_interface(), "wlan0")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    def test_get_active_monitor_interface_suffix(self, mock_status):
        """Test get_active_monitor_interface when suffix interface (e.g. wlan0mon) is in monitor mode."""
        self.gui.interface = "wlan0"
        mock_status.return_value = {"wlan0": "managed", "wlan0mon": "monitor"}
        self.assertEqual(self.gui.get_active_monitor_interface(), "wlan0mon")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    def test_get_active_monitor_interface_none(self, mock_status):
        """Test get_active_monitor_interface when no interface is in monitor mode."""
        self.gui.interface = "wlan0"
        mock_status.return_value = {"wlan0": "managed", "wlan1": "managed"}
        self.assertIsNone(self.gui.get_active_monitor_interface())

    @patch('subprocess.check_output')
    def test_get_interface_details_iw(self, mock_check_output):
        """Test parsing iw dev info output for interface details."""
        mock_check_output.return_value = b"""Interface wlan0
\taddr 11:22:33:44:55:66
\ttype monitor
\tchannel 6 (2437 MHz), width: 20 MHz
\ttxpower 20.00 dBm
"""
        details = get_interface_details("wlan0")
        self.assertEqual(details["mac"], "11:22:33:44:55:66")
        self.assertEqual(details["mode"], "monitor")
        self.assertEqual(details["channel"], "6")
        self.assertEqual(details["freq"], "2437 MHz")
        self.assertEqual(details["txpower"], "20.00 dBm")

    def test_channel_hopping_toggle_requires_monitor_mode(self):
        """Test enabling channel hopping when monitor mode is OFF shows warning."""
        self.gui.is_monitor_on = False
        self.gui.hop_var.get.return_value = True
        self.gui.toggle_channel_hopping()
        self.mock_msgbox.showwarning.assert_called_with(
            "Monitor Mode Required",
            "Channel hopping requires monitor mode to be active."
        )

    def test_channel_hopping_starts_and_stops(self):
        """Test starting and stopping channel hopping."""
        self.gui.is_monitor_on = True
        self.gui.hop_var.get.return_value = True
        self.gui.toggle_channel_hopping()
        self.assertTrue(self.gui.is_channel_hopping)
        
        self.gui.stop_channel_hopping()
        self.assertFalse(self.gui.is_channel_hopping)

    @patch('subprocess.check_output')
    def test_iwconfig_fallback_ignores_no_wireless_extensions(self, mock_output):
        """Test that iwconfig fallback ignores non-wireless interfaces."""
        from ezmonitormode.monitor_gui import get_interfaces_status
        # Force iw dev to fail so iwconfig is called
        def side_effect(cmd, **kwargs):
            if cmd[0] == "iw":
                raise FileNotFoundError("iw not found")
            elif cmd[0] == "iwconfig":
                return b"""eth0      no wireless extensions.
lo        no wireless extensions.
wlan0     IEEE 802.11  Mode:Managed  Frequency:2.412 GHz
"""
            return b""
        mock_output.side_effect = side_effect
        status = get_interfaces_status()
        self.assertIn("wlan0", status)
        self.assertNotIn("eth0", status)
        self.assertNotIn("lo", status)

    @patch('builtins.open')
    def test_get_default_gateway_interface(self, mock_open):
        """Test reading default gateway interface from /proc/net/route."""
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\n",
            "wlan0\t00000000\t0101A8C0\t0003\t0\t0\t600\t00000000\t0\t0\t0\n",
            "eth0\t0001A8C0\t00000000\t0001\t0\t0\t100\t00FFFFFF\t0\t0\t0\n"
        ]
        mock_open.return_value.__enter__.return_value = mock_file
        gw = get_default_gateway_interface()
        self.assertEqual(gw, "wlan0")

    @patch('os.path.islink')
    @patch('os.readlink')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_get_device_driver_and_chipset(self, mock_open, mock_exists, mock_readlink, mock_islink):
        """Test fast sysfs extraction of driver and product chipset."""
        mock_islink.return_value = True
        mock_readlink.return_value = "../../../bus/usb/drivers/rtl88x2bu"
        mock_exists.return_value = True
        
        mock_f = MagicMock()
        mock_f.read.side_effect = ["802.11ac NIC", "up"]
        mock_open.return_value.__enter__.return_value = mock_f
        
        info = get_device_driver_and_chipset("wlan0")
        self.assertEqual(info["driver"], "rtl88x2bu")
        self.assertEqual(info["chipset"], "802.11ac NIC")
        self.assertEqual(info["operstate"], "up")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    @patch('ezmonitormode.monitor_gui.get_default_gateway_interface')
    def test_detect_interfaces_prioritizes_secondary(self, mock_gw, mock_status):
        """Test that secondary/external adapter is ordered before active gateway interface."""
        mock_status.return_value = {"wlan0": "managed", "wlan1": "managed"}
        mock_gw.return_value = "wlan0"
        ifaces = detect_interfaces()
        self.assertEqual(ifaces, ["wlan1", "wlan0"])

    def test_enable_monitor_warns_on_active_gateway(self):
        """Test that enabling monitor on active gateway shows high-priority warning."""
        self.gui.interface = "wlan0"
        with patch('ezmonitormode.monitor_gui.get_default_gateway_interface', return_value="wlan0"):
            self.mock_msgbox.askyesno.return_value = False
            self.gui.enable_monitor()
            self.mock_msgbox.askyesno.assert_called_once()
            args = self.mock_msgbox.askyesno.call_args[0]
            self.assertIn("ACTIVE network", args[1])

    @patch('shutil.which')
    @patch('subprocess.Popen')
    def test_launch_in_terminal_alacritty_bash_c(self, mock_popen, mock_which):
        """Test terminal launch uses bash -c on modern terminals like alacritty."""
        mock_which.side_effect = lambda t: t == "alacritty"
        self.gui.launch_in_terminal("airodump-ng wlan0mon", "Airodump-ng")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "alacritty")
        self.assertEqual(args[1], "-e")
        self.assertEqual(args[2], "bash")
        self.assertEqual(args[3], "-c")

    @patch('shutil.which')
    @patch('subprocess.Popen')
    def test_launch_in_terminal_injection_test_pauses(self, mock_popen, mock_which):
        """Test packet injection test appends pause prompt so terminal stays visible."""
        mock_which.side_effect = lambda t: t == "lxterminal"
        self.gui.launch_in_terminal("aireplay-ng --test wlan0mon", "Packet Injection Test")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "lxterminal")
        self.assertIn("Press Enter to close window", args[2])

    @patch('ezmonitormode.monitor_gui.detect_interfaces', return_value=["wlan0"])
    @patch('ezmonitormode.monitor_gui.get_interfaces_status', return_value={"wlan0": "managed"})
    @patch('ezmonitormode.monitor_gui.get_default_gateway_interface', return_value="wlan0")
    @patch('ezmonitormode.monitor_gui.get_interface_details')
    def test_cli_main_status(self, mock_details, mock_gw, mock_status, mock_ifaces):
        """Test headless CLI --status output."""
        mock_details.return_value = {
            "driver": "rtl88x2bu", "chipset": "802.11ac NIC", "mode": "managed",
            "ssid": "Skynet", "mac": "00:11:22:33:44:55", "channel": "153",
            "freq": "5765 MHz", "txpower": "18.00 dBm", "operstate": "up"
        }
        args = MagicMock()
        args.status = True
        args.channel = None
        args.test_injection = False
        args.on = False
        args.off = False
        args.iface = None
        ret = cli_main(args)
        self.assertEqual(ret, 0)

    @patch('ezmonitormode.monitor_gui.detect_interfaces', return_value=["wlan0"])
    @patch('ezmonitormode.monitor_gui.get_default_gateway_interface', return_value="wlan0")
    def test_cli_main_on_refuses_active_gateway_without_force(self, mock_gw, mock_ifaces):
        """Test that CLI --on blocks toggling default gateway without --force."""
        args = MagicMock()
        args.status = False
        args.channel = None
        args.test_injection = False
        args.on = True
        args.off = False
        args.iface = "wlan0"
        args.force = False
        ret = cli_main(args)
        self.assertEqual(ret, 1)


if __name__ == '__main__':
    unittest.main()
