# Linux build and validation

Sidee uses the same Python core, browser dashboard, SSDP discovery and
MQTT/TLS TV protocol on Linux. The Linux port adds only the platform boundary:
LAN interface inspection, user-state paths, a small desktop launcher, and a
PyInstaller bundle. It does not change pairing, token, certificate or tile
installation code.

## Run from a source checkout

Python 3.9+ is enough:

```bash
python3 -m pip install -r requirements.txt
python3 sidee.py
```

Use `python3 linux_launcher.py` for the desktop control window. Tk is optional;
when it is not installed the launcher uses `zenity`/`kdialog` (if present) and
opens the same browser dashboard. On a headless machine, `python3 sidee.py
--headless --port 0` keeps the dashboard local and prints its authenticated
address.

Linux discovery reads `ip -o -4 addr show` (iproute2) and falls back to
`ifconfig`. It uses each LAN interface's directed broadcast, then the global
broadcast and SSDP multicast group. Loopback, link-local, point-to-point,
Docker/libvirt bridges and common VPN interfaces are excluded, so VPN traffic
is not used for TV discovery. If discovery is blocked, the dashboard still
accepts a manually entered TV IPv4 address without bypassing PIN pairing.

## Build a bundle

Install the runtime and packaging dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install PyInstaller==6.22.3
sudo apt install python3-tk   # optional, gives the Tk control window
python3 tools/build_linux_release.py --architecture x86_64
```

On aarch64 use `--architecture aarch64`. Outputs are `dist/Sidee/` and
`dist/Sidee-linux-<architecture>.tar.gz`. The builder refuses to cross-compile,
checks the native ELF executable and required dashboard/certificate resources,
and packages one predictable `Sidee/` top-level folder.

Extract and run:

```bash
tar -xzf Sidee-linux-x86_64.tar.gz
./Sidee/sidee
```

## User state and logs

| Data | Path |
| --- | --- |
| Pairing session and client certificate bundle | `~/.sidee/` |
| Dashboard runtime state (packaged builds) | `$XDG_STATE_HOME/sidee/runtime/` (default `~/.local/state/sidee/runtime/`) |
| Launcher error log | `$XDG_STATE_HOME/sidee/logs/sidee.log` (default `~/.local/state/sidee/logs/sidee.log`) |
| Source-checkout dashboard state | `.runtime/dashboard.json` |

`SIDEE_STATE_DIR` overrides the state location for tests and isolated runs.
Pairing tokens remain mode 600 on Unix.

## Automated checks

The shared Python suite includes Linux interface parsing and launcher fallback
tests. The packaged bundle can be checked without a GUI or a TV:

```bash
dist/Sidee/sidee --self-test
python3 tools/smoke_test.py --executable dist/Sidee/sidee
```

These checks start and stop the real dashboard, exercise its authenticated
HTTP endpoints, and verify clean shutdown. They do not discover, pair with, or
install anything on a TV. A physical TV test is still required for first-time
PIN pairing and tile registration on the target network.
