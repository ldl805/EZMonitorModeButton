#!/usr/bin/env python3
"""Tests for the monitor_gui module."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ezmonitormode.monitor_gui import MonitorGUI


class TestMonitorGUI(unittest.TestCase):
    """Test cases for the MonitorGUI class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('tkinter.Tk'):
            self.mock_root = MagicMock()
            self.gui = MonitorGUI(self.mock_root)

    def test_gui_initialization(self):
        """Test that MonitorGUI initializes correctly."""
        self.assertIsNotNone(self.gui)
        self.assertEqual(self.gui.master, self.mock_root)

    def test_gui_creates_widgets(self):
        """Test that GUI creates expected widgets."""
        # Check that title was set
        self.mock_root.title.assert_called_with("Monitor Mode Control")
        # Check that geometry was set
        self.mock_root.geometry.assert_called_with("400x350")

    def test_get_terminal_with_valid_terminal(self):
        """Test get_terminal returns a terminal when available."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/x-terminal-emulator'
            terminal = self.gui.get_terminal()
            self.assertEqual(terminal, '/usr/bin/x-terminal-emulator')

    def test_get_terminal_fallback_to_gnome(self):
        """Test get_terminal falls back to gnome-terminal."""
        def which_side_effect(cmd):
            if cmd == 'x-terminal-emulator':
                return None
            elif cmd == 'gnome-terminal':
                return '/usr/bin/gnome-terminal'
            return None

        with patch('shutil.which', side_effect=which_side_effect):
            terminal = self.gui.get_terminal()
            self.assertEqual(terminal, '/usr/bin/gnome-terminal')

    def test_get_terminal_no_terminal(self):
        """Test get_terminal returns None when no terminal found."""
        with patch('shutil.which', return_value=None):
            terminal = self.gui.get_terminal()
            self.assertIsNone(terminal)

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test run_command with successful execution."""
        result = self.gui.run_command(['echo', 'test'], 'Test Command')
        self.assertTrue(result)
        mock_run.assert_called_once_with(['echo', 'test'], check=True)

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test run_command handles command failure."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'test')
        
        with patch.object(self.gui, 'master') as mock_master:
            result = self.gui.run_command(['false'], 'Failing Command')
            self.assertFalse(result)

    def test_status_var_initialization(self):
        """Test that status variable is properly initialized."""
        self.assertEqual(self.gui.status_var.get(), "Ready")


def test_module_imports():
    """Test that the monitor_gui module can be imported."""
    try:
        import ezmonitormode.monitor_gui
        assert True
    except ImportError:
        assert False, "Failed to import monitor_gui module"


if __name__ == '__main__':
    unittest.main()
