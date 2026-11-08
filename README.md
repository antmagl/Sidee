<p align="center"><img src="assets/sidee-logo.png" width="180" alt="Sidee"></p>

# Sidee

**Your TV, your freedom.**

> **Fork:** this repository is [antmagl's fork](https://github.com/antmagl/Sidee) of
> [Empi9245/Sidee](https://github.com/Empi9245/Sidee). It adds Linux support and
> a built-in SmartTube preset for Hisense VIDAA TVs. Upstream remains the
> original project.

Sidee is a free, open-source tool that helps people make more of the TVs they already own. Its simple browser dashboard lets you connect to a compatible TV and manage additional web-app launcher tiles, without coding, command-line setup, or specialist knowledge.

Sidee is built around three principles:

- **Freedom and control:** Give people more choice over how they use their own devices.
- **Accessibility:** Make the process straightforward, even for first-time users.
- **Privacy and security:** Keep TV discovery and pairing on the local network, with authorization through the PIN shown on the TV.

## Requirements

- Windows 10/11, macOS 15+ (Apple Silicon or Intel), or Linux (x86_64 or aarch64)
- A compatible VIDAA TV and a computer on the same home Wi-Fi/Ethernet network
- Internet access for the initial Windows setup and any online experiences you choose to open on the TV

Compatibility varies by TV model and firmware. The primary tested firmware is U09.60 / V0000.09.60A.Q0707. Support for some other models is experimental; see the [compatibility notes](docs/toshiba-compatibility.md).

## Get started

### Windows

1. [Download Sidee for Windows](https://github.com/antmagl/Sidee/releases) and extract the ZIP.
2. Double-click `start-windows.bat` in the extracted folder.
3. Wait for the dashboard to open in your browser, then follow the on-screen steps.

On first launch, Sidee downloads a private, version-pinned Python runtime and its connection dependency from official sources, verifying the downloads using SHA-256. You do not need to install Python yourself, enter commands, or grant administrator rights. Later launches reuse the downloaded runtime.

Keep the launcher window open while using the dashboard. If the browser does not open automatically, use the full dashboard link shown in the launcher, including its access key. If Windows requests network access, allow it on your trusted home network.

### macOS

The macOS download includes Sidee.app and its required runtime, so no separate Python installation or Terminal commands are needed.

1. Get the package for your Mac from [Releases](https://github.com/antmagl/Sidee/releases) or a successful [build workflow](https://github.com/antmagl/Sidee/actions/workflows/build.yml). Choose `arm64` for Apple Silicon or `x64` for Intel.
2. Open the DMG, drag Sidee.app to Applications, and launch it.
3. Use **Open dashboard** in Sidee's control window.

**Important:** The current macOS builds are not signed or notarized. macOS may prevent them from opening automatically. If you trust the downloaded package, follow [Apple's instructions](https://support.apple.com/en-us/102445) for opening an unverified app. If prompted, grant local network access so Sidee can discover your TV. The builds are checked in CI but still require broader testing on physical Macs.

Sidee's control window must remain open while you use the dashboard; **Quit Sidee** stops the local dashboard service.

### Linux

The Linux download includes Sidee and its runtime, so no separate Python installation is needed.

1. Download `Sidee-linux-x86_64.tar.gz` or `Sidee-linux-aarch64.tar.gz` from [Releases](https://github.com/antmagl/Sidee/releases) or a successful [build workflow](https://github.com/antmagl/Sidee/actions/workflows/build.yml).
2. Extract it and run the `Sidee/sidee` executable.
3. Use **Open dashboard** in Sidee's window, or open the address shown in your browser.

Sidee uses a small Tk control window when Python's Tk bindings are available. If Tk is not installed it uses a desktop dialog instead, and still opens the same browser dashboard. Keep the Sidee window or dialog open; closing it stops the local dashboard service. On Wayland or X11 desktop sessions, no extra configuration is required for the dashboard itself.

For a source checkout, run `python sidee.py` as shown under [Development](#development), or use `python linux_launcher.py` for the desktop launcher window.

## Connect your TV

1. **Find TV:** Turn on your TV, put it on the same network as your computer, and select **Find TV**. Sidee uses the discovered address rather than assuming a fixed TV IP. If discovery fails, you can enter the address shown in the TV's network settings.
2. **Request code:** Select **Request code** and enter the four-digit PIN displayed on your TV, then choose **Confirm code**. Pairing requires this confirmation.
3. **Manage launcher tiles:** Choose an option offered in the dashboard and follow the confirmation steps. The available choices are maintained with Sidee. SmartTube is a hosted web build, so it is one-click like Nuvio; the Android APK cannot run on VIDAA.

Registered tiles remain in the TV launcher across restarts, even when Sidee is no longer running. The availability of the web experiences opened by those tiles depends on their own network requirements; SmartTube is hosted online and needs no computer or local server.

**Want to use your phone?** The dashboard provides a locally generated QR code so you can open its controls on a phone connected to the same home network. Keep Sidee running on the computer and keep dashboard access links private.

## SmartTube for VIDAA

This fork includes a SmartTube preset for the hosted SmartTube web client for
Hisense VIDAA TVs. SmartTube is not the Android app — VIDAA has no Android
runtime. It is a separate web build installed as a normal launcher tile.

- Hosted app: <https://antmagl.github.io/smarttube-vidaa/v16/index.html>
- Source, Worker and preset: <https://github.com/antmagl/smarttube-vidaa>

After pairing the TV, choose **SmartTube** in the dashboard or run:

```bash
python sidee.py install smarttube
```

Advanced users can host the built app themselves and point the preset at it:

```bash
python sidee.py install smarttube --url http://192.168.1.20:8090/
```

The TV caches launcher entries by app id. When the app's versioned URL
changes, install under the new id (the preset is updated with each release).

## How Sidee works

Sidee uses the TV's local control interface for network discovery, PIN-authorized pairing, and launcher management. The connection uses MQTT/TLS on port 36669. Sidee does not require an account or cloud service for discovery, pairing, or TV control.

Sidee is designed to use functions available to an authorized, paired TV client. It does not install native system software or modify the TV's operating system.

## Privacy and security

- **No Sidee telemetry:** TV discovery and control take place locally; Sidee does not require an account.
- **Consent-based pairing:** You must confirm the PIN shown on your TV.
- **Local credentials:** Saved pairing tokens remain in your user profile at `~/.sidee/session.json` (mode 600 on Unix; inherited user-profile permissions on Windows).
- **Protected dashboard access:** Treat dashboard links and saved pairing tokens as private. Only share access with people you trust on your home network.
- **Limited operations:** Sidee manages web launcher tiles through the TV's authorized control interface; it does not make system-level changes.

The first Windows setup downloads verified dependencies. Web experiences opened from the TV launcher may make their own network connections independently of Sidee.

## Troubleshooting

If **Find TV** cannot locate your TV, check that both devices share the same network and that a VPN, guest Wi-Fi, or firewall is not blocking local discovery. The manual IP option checks that the destination responds as a compatible TV and that port 36669 is reachable; it never bypasses PIN authorization.

Some TVs advertise themselves rather than replying directly to discovery. In that case, keep the TV on and retry **Find TV**. For known firmware-specific pairing limitations, see the [compatibility notes](docs/toshiba-compatibility.md).

On macOS, check **System Settings → Privacy & Security → Local Network** and, if needed, the firewall permissions for Sidee. Diagnostic logs are stored at `~/Library/Logs/Sidee/sidee.log`. On Linux, allow discovery and port 36669 through your firewall; diagnostic logs are stored at `~/.local/state/sidee/logs/sidee.log`. Keep logs containing private access data confidential.

## Development

With Python 3.9+ already installed, the dashboard can also be started from a source checkout:

```bash
python -m pip install -r requirements.txt
python sidee.py
```

Optional command-line interface:

```bash
python sidee.py discover
python sidee.py pair TV_IP
python sidee.py install PRESET_ID
python sidee.py install smarttube
python sidee.py install smarttube --url http://192.168.1.20:8090/  # optional self-hosted build
python sidee.py list
python sidee.py launch PRESET_ID
python sidee.py refresh
```

Replace `TV_IP` with your TV's LAN address and `PRESET_ID` with an available built-in option. Pairing always requires the TV's authorization.

On a Linux desktop, `python linux_launcher.py` opens the same dashboard in a small control window. If Tk is unavailable, install the distribution's Python Tk package (for example `python3-tk`) or let the launcher fall back to a browser/dialog session.

Run Python tests with `python -m unittest discover -s tests` and dashboard interaction tests with `node --test tests/test_dashboard_selection.js`.

Packaging information is in the [macOS build notes](docs/macos-build.md) and [Linux build notes](docs/linux-build.md). Automated Windows, macOS, and Linux builds are available through [GitHub Actions](https://github.com/antmagl/Sidee/actions/workflows/build.yml).

## Why Sidee exists

Sidee began with a simple idea: people should have more freedom to use technology they already own. After a lot of experimentation, that idea became a small tool designed to make everyday tasks easier and more approachable. If it helps you, please consider supporting continued development.

☕ [Support Sidee on Ko-fi](https://ko-fi.com/sidee)

## License

MIT — see [LICENSE](LICENSE). Sidee is an independent project and is not affiliated with TV manufacturers. Use it only with devices you own or are authorized to manage.
