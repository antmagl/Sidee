"""Small Linux desktop launcher for Sidee's existing browser dashboard.

The launcher never talks to the TV itself. It starts the same local dashboard
used on Windows and macOS, optionally shows a small control window, and stops
the server cleanly when that window closes.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import traceback


def _state_root() -> Path:
    override = os.environ.get("SIDEE_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    value = os.environ.get("XDG_STATE_HOME", "").strip()
    if value:
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate / "sidee"
    return Path(os.path.expanduser("~")) / ".local" / "state" / "sidee"


def _log_error() -> Path:
    folder = _state_root() / "logs"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / "sidee.log"
    with path.open("a", encoding="utf-8") as output:
        os.chmod(path, 0o600)
        traceback.print_exc(file=output)
    return path


def _dialog(message: str, *, error: bool = False) -> None:
    """Use a desktop dialog when available; never require a specific toolkit."""
    title = "Sidee could not start" if error else "Sidee"
    commands = [
        (["zenity", "--error" if error else "--info", "--title", title,
          "--text", message], "zenity"),
        (["kdialog", "--title", title, "--error" if error else "--msgbox", message],
         "kdialog"),
        (["xmessage", "-center", message], "xmessage"),
    ]
    for command, program in commands:
        if shutil.which(program):
            try:
                subprocess.run(command, timeout=60, check=False)
                return
            except (OSError, subprocess.TimeoutExpired):
                continue
    print(message, file=sys.stderr)


def _fallback_error(message: str) -> None:
    _dialog(message, error=True)


def _write(message: str) -> None:
    if sys.stdout is not None:
        print(message, flush=True)


def _ensure_streams() -> None:
    """A windowed PyInstaller build may not have console streams."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _install_signal_handlers(stop) -> dict:
    previous = {}
    if threading.current_thread() is not threading.main_thread():
        return previous
    for number in (signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.signal(number, lambda *_: stop.set())
    return previous


def _restore_signal_handlers(previous: dict) -> None:
    for number, handler in previous.items():
        signal.signal(number, handler)


def _run_browser_mode() -> int:
    """Control the dashboard with a small desktop dialog when Tk is absent."""
    from core import webui

    if webui._reopen_dashboard(True):
        return 0
    dashboard = webui.Dashboard()
    previous = {}
    try:
        dashboard.start()
        previous = _install_signal_handlers(dashboard.stop_event)
        _write(f"Sidee (this computer): {dashboard.url}")
        _write(f"Sidee (from your phone, same network): "
               f"http://{webui._local_ip()}:{dashboard.port}/?key={webui.ACCESS_KEY}")
        _write("Keep the Sidee window open. Close it to stop the dashboard.")
        if not dashboard.open():
            _dialog("Open this complete address in your browser:\n\n"
                    + dashboard.url)
        if shutil.which("zenity"):
            process = subprocess.Popen([
                "zenity", "--info", "--title", "Sidee",
                "--text", "Sidee is running.\n\nClose this window to stop Sidee.",
                "--ok-label", "Stop Sidee",
            ])
            try:
                while process.poll() is None:
                    if dashboard.stop_event.wait(0.2):
                        break
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
        else:
            dashboard.stop_event.wait()
        if dashboard.error:
            raise dashboard.error
        return 0
    finally:
        _restore_signal_handlers(previous)
        dashboard.close()


def run_gui() -> int:
    """Open a native Tk control window, or fall back to a desktop dialog."""
    try:
        import tkinter as tk
        from tkinter import font as tkfont
        from tkinter import messagebox, ttk
        from core import webui
    except Exception:
        return _run_browser_mode()

    window = dashboard = None
    previous_signals = {}
    try:
        if webui._reopen_dashboard(True):
            return 0
        try:
            window = tk.Tk()
        except Exception:
            return _run_browser_mode()
        window.title("Sidee")
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill="both", expand=True)
        heading = tkfont.nametofont("TkDefaultFont").copy()
        heading.configure(size=22, weight="bold")
        ttk.Label(frame, text="Sidee", font=heading).pack()
        ttk.Label(frame, text="Use Sidee in your browser.\nKeep this window open "
                  "while pairing your TV.", justify="center").pack(pady=14)
        dashboard = webui.Dashboard()
        dashboard.start()

        def open_dashboard(*_):
            try:
                if not dashboard.open():
                    messagebox.showinfo("Open Sidee", "Open this complete address "
                        "in your browser:\n\n" + dashboard.url, parent=window)
            except Exception:
                messagebox.showinfo("Open Sidee", "Open this complete address "
                    "in your browser:\n\n" + dashboard.url, parent=window)

        def quit_sidee(*_):
            dashboard.stop_event.set()
            window.quit()

        def check_server():
            if dashboard.error:
                raise_error(dashboard.error)
                return
            if dashboard.stop_event.is_set():
                window.quit()
                return
            window.after(200, check_server)

        def raise_error(error):
            try:
                raise error
            except Exception:
                path = _log_error()
            messagebox.showerror("Sidee stopped", "The dashboard stopped. Quit "
                "and reopen Sidee. Details were saved to:\n" + str(path), parent=window)
            quit_sidee()

        ttk.Button(frame, text="Open dashboard", command=open_dashboard).pack(fill="x")
        ttk.Button(frame, text="Quit Sidee", command=quit_sidee).pack(fill="x", pady=(8, 0))
        window.protocol("WM_DELETE_WINDOW", quit_sidee)
        window.bind("<Control-q>", quit_sidee)
        previous_signals = _install_signal_handlers(dashboard.stop_event)
        window.after(200, check_server)
        window.after(100, open_dashboard)
        window.mainloop()
        return 1 if dashboard.error else 0
    except Exception:
        try:
            path = _log_error()
            message = ("Quit and reopen Sidee. Details were saved to:\n" + str(path))
        except OSError:
            message = "Sidee could not start. Check your Python and desktop installation."
        if window:
            from tkinter import messagebox
            messagebox.showerror("Sidee could not start", message, parent=window)
        else:
            _fallback_error(message)
        return 1
    finally:
        _restore_signal_handlers(previous_signals)
        if dashboard:
            dashboard.close()
        if window:
            window.destroy()


def main() -> int:
    _ensure_streams()
    if len(sys.argv) > 1 or os.environ.get("SIDEE_CI") == "1":
        try:
            import sidee
            return sidee.main()
        except Exception:
            # A packaged windowed app must not show a traceback dialog in CI.
            try:
                path = _log_error()
                if sys.stderr:
                    print("Sidee startup failed. Details: " + str(path), file=sys.stderr)
            except OSError:
                pass
            return 1
    try:
        return run_gui()
    except Exception:
        try:
            path = _log_error()
            _fallback_error("Sidee could not start. Details were saved to:\n"
                            + str(path))
        except OSError:
            _fallback_error("Sidee could not start. Check your installation.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
