"""Linux launcher checks that never open a desktop, browser, or TV connection."""
import builtins
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import linux_launcher as launcher
import sidee


class TestLinuxState(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name).resolve()

    def test_explicit_state_override_keeps_logs_with_other_state(self):
        with patch.dict(os.environ, {"SIDEE_STATE_DIR": str(self.folder)}):
            self.assertEqual(launcher._state_root(), self.folder)

    def test_xdg_state_home_keeps_launcher_logs_private(self):
        xdg = self.folder / "xdg"
        with patch.dict(os.environ, {"SIDEE_STATE_DIR": "",
                                     "XDG_STATE_HOME": str(xdg)}):
            try:
                raise RuntimeError("synthetic launcher failure")
            except RuntimeError:
                path = launcher._log_error()
        self.assertEqual(path, xdg / "sidee" / "logs" / "sidee.log")
        self.assertIn("synthetic launcher failure", path.read_text(encoding="utf-8"))
        if os.name != "nt":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class TestLinuxEntrypoint(unittest.TestCase):
    def test_arguments_are_delegated_to_the_shared_cli(self):
        with patch.object(sidee, "main", return_value=3) as main, \
                patch.object(launcher.sys, "argv", ["linux_launcher.py", "--self-test"]):
            self.assertEqual(launcher.main(), 3)
        main.assert_called_once_with()

    def test_missing_tkinter_falls_back_without_crashing(self):
        original = builtins.__import__

        def import_without_tk(name, *args, **kwargs):
            if name == "tkinter" or name.startswith("tkinter."):
                raise ImportError("Tk is not installed")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_without_tk), \
                patch.object(launcher, "_run_browser_mode", return_value=7) as fallback:
            self.assertEqual(launcher.run_gui(), 7)
        fallback.assert_called_once_with()

    def test_windowed_build_gets_safe_output_streams(self):
        with patch.object(launcher.sys, "stdout", None), \
                patch.object(launcher.sys, "stderr", None):
            launcher._ensure_streams()
            self.assertIsNotNone(launcher.sys.stdout)
            self.assertIsNotNone(launcher.sys.stderr)
            launcher.sys.stdout.close()
            launcher.sys.stderr.close()


if __name__ == "__main__":
    unittest.main()
