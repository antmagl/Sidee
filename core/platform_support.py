"""Small platform boundary for resources, private state, and LAN discovery."""
from __future__ import annotations

import errno
import ipaddress
import os
from pathlib import Path
import re
import socket
import subprocess
import sys


def resource_root(module_file: str | None = None) -> Path:
    """Return packaged data without relying on the launcher's working folder."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    parent = Path(module_file or __file__).resolve().parent
    return parent.parent if parent.name == "core" else parent


def _state_override() -> Path | None:
    value = os.environ.get("SIDEE_STATE_DIR", "").strip()
    return Path(value).expanduser().resolve() if value else None


def profile_dir() -> Path:
    """Preserve existing pairings; explicit test state never reads the profile."""
    base = _state_override()
    if base is None:
        home = Path(os.path.expanduser("~"))
        base, legacy = home / ".sidee", home / ".vidaa-tile"
        if not (base / "session.json").is_file() and (legacy / "session.json").is_file():
            base = legacy
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    return base


def xdg_state_home() -> Path:
    """Return the per-user state directory on Linux-like desktops."""
    value = os.environ.get("XDG_STATE_HOME", "").strip()
    if value:
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate
    return Path(os.path.expanduser("~")) / ".local" / "state"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def dashboard_state_path(project_root: str | Path) -> Path:
    """Keep writable runtime files outside a frozen application bundle."""
    override = _state_override()
    if override is not None:
        return override / "runtime" / "dashboard.json"
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        return (Path(os.path.expanduser("~")) / "Library" / "Application Support"
                / "Sidee" / "runtime" / "dashboard.json")
    if is_linux() and getattr(sys, "frozen", False):
        return xdg_state_home() / "sidee" / "runtime" / "dashboard.json"
    return Path(project_root) / ".runtime" / "dashboard.json"


def allow_reuse_address() -> bool:
    """Unix can reuse closed listeners; Windows must reserve its own port."""
    return os.name != "nt"


def configure_exclusive_tcp_socket(sock: socket.socket) -> None:
    if os.name == "nt":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)


def address_in_use(error: OSError) -> bool:
    return (error.errno == errno.EADDRINUSE
            or getattr(error, "winerror", None) in (10013, 10048))


def _broadcast(host: str, mask: str) -> str | None:
    try:
        address = ipaddress.IPv4Address(host)
        network = ipaddress.IPv4Network(f"{address}/{mask}", strict=False)
        if network.is_loopback or network.prefixlen >= 31:
            return None
        return str(network.broadcast_address)
    except ValueError:
        return None


def _interfaces_from_ipconfig(output: str) -> list[tuple[str, str]]:
    """Parse Windows IPv4 + mask pairs in ipconfig output.

    The Windows output is line-oriented: IPv4 appears on a line, then the mask on
    the immediately following line. Keep the parser stateful instead of searching
    for arbitrary IPv4-looking strings on every line, which breaks when multiple
    adapters are present.
    """
    interfaces: set[tuple[str, str]] = set()
    pending_ip = None
    ip_match = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if "ipv4" in lower:
            match = ip_match.search(line)
            pending_ip = match.group(1) if match else None
            continue
        if pending_ip and ("mask" in lower or "subnet" in lower or "netmask" in lower):
            match = ip_match.search(line)
            if match:
                mask = match.group(1)
                target = _broadcast(pending_ip, mask)
                if target:
                    interfaces.add((pending_ip, target))
            pending_ip = None
    return sorted(interfaces)


def broadcasts_from_ipconfig(output: str) -> list[str]:
    return sorted({target for _, target in _interfaces_from_ipconfig(output)})


def _interfaces_from_ifconfig(output: str) -> list[tuple[str, str]]:
    """Parse active macOS broadcast interfaces, including hexadecimal masks."""
    interfaces = set()
    active = False
    pending = set()
    for line in output.splitlines():
        if line and not line[0].isspace():
            if active:
                interfaces.update(pending)
            pending = set()
            flags = re.search(r"<([^>]+)>", line)
            names = set(flags.group(1).split(",")) if flags else set()
            active = {"UP", "BROADCAST"}.issubset(names) and not names.intersection(
                {"LOOPBACK", "POINTOPOINT"})
        elif re.search(r"\bstatus:\s+inactive\b", line):
            active = False
        if not active:
            continue
        match = re.search(r"\binet\s+(\d{1,3}(?:\.\d{1,3}){3})\s+netmask\s+(\S+)", line)
        if not match:
            continue
        try:
            address = ipaddress.IPv4Address(match.group(1))
        except ValueError:
            continue
        if (address.is_unspecified or address.is_multicast or address.is_link_local):
            continue
        mask = match.group(2)
        if mask.lower().startswith("0x"):
            try:
                mask = str(ipaddress.IPv4Address(int(mask, 16)))
            except (ValueError, ipaddress.AddressValueError):
                continue
        target = _broadcast(match.group(1), mask)
        if target:
            pending.add((str(address), target))
    if active:
        interfaces.update(pending)
    return sorted(interfaces)


def broadcasts_from_ifconfig(output: str) -> list[str]:
    return sorted({target for _, target in _interfaces_from_ifconfig(output)})


_IP_ADDR_INET = re.compile(
    r"^\s*\d+:\s+(?P<name>\S+)\s+inet\s+"
    r"(?P<host>\d{1,3}(?:\.\d{1,3}){3})/(?P<prefix>\d{1,2})\b"
    r"(?P<rest>.*)$")
# These interfaces are host-only bridges/tunnels, not the user's home LAN.
_VIRTUAL_INTERFACE_PREFIXES = (
    "docker", "veth", "br-", "virbr", "tun", "tap", "wg", "zt",
    "tailscale", "podman", "cni", "flannel", "kube", "dummy",
)


def _is_virtual_interface(name: str) -> bool:
    name = name.split("@", 1)[0].lower()
    return name == "lo" or name.startswith(_VIRTUAL_INTERFACE_PREFIXES)


def _interfaces_from_ip_addr(output: str) -> list[tuple[str, str]]:
    """Parse `ip -o -4 addr show`, which is available on modern Linux.

    Prefer the broadcast address reported by the kernel. Compute one from the
    prefix when an interface does not print it, but ignore point-to-point and
    host/link-scope addresses (VPN tunnels, loopback and link-local only).
    """
    interfaces: set[tuple[str, str]] = set()
    for line in output.splitlines():
        match = _IP_ADDR_INET.match(line)
        if not match or _is_virtual_interface(match.group("name")):
            continue
        rest = match.group("rest")
        lowered = rest.lower()
        if " peer " in f" {lowered} " or "scope host" in lowered:
            continue
        try:
            address = ipaddress.IPv4Address(match.group("host"))
            prefix = int(match.group("prefix"))
        except (ValueError, ipaddress.AddressValueError):
            continue
        if (prefix > 32 or address.is_loopback or address.is_unspecified
                or address.is_multicast or address.is_link_local):
            continue
        broadcast = re.search(r"\bbrd\s+(\d{1,3}(?:\.\d{1,3}){3})\b", rest)
        if broadcast:
            try:
                target = str(ipaddress.IPv4Address(broadcast.group(1)))
            except ipaddress.AddressValueError:
                target = None
        else:
            target = _broadcast(match.group("host"), str(prefix))
        if target:
            interfaces.add((str(address), target))
    return sorted(interfaces)


def broadcasts_from_ip_addr(output: str) -> list[str]:
    return sorted({target for _, target in _interfaces_from_ip_addr(output)})


def _run_interface_command(command: list[str], parser, **kwargs):
    try:
        result = subprocess.run(command, **kwargs)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parser(result.stdout) if result.returncode == 0 else None


def local_ipv4_interfaces() -> list[tuple[str, str]]:
    """Inspect native LAN interfaces, returning their IPv4/broadcast pairs."""
    kwargs = dict(capture_output=True, text=True, errors="replace", timeout=3)
    if sys.platform == "darwin":
        commands = [(["/sbin/ifconfig"], _interfaces_from_ifconfig)]
    elif os.name == "nt":
        commands = [(["ipconfig"], _interfaces_from_ipconfig)]
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    elif is_linux():
        # `ip` is part of iproute2 and is present on current distributions.
        # Keep net-tools' ifconfig as a fallback for minimal/older systems.
        commands = [(["ip", "-o", "-4", "addr", "show"], _interfaces_from_ip_addr),
                    (["/sbin/ifconfig"], _interfaces_from_ifconfig),
                    (["ifconfig"], _interfaces_from_ifconfig)]
    else:
        return []
    for command, parser in commands:
        interfaces = _run_interface_command(command, parser, **kwargs)
        if interfaces is not None:
            return interfaces
    return []


def local_broadcasts() -> list[str]:
    """Use only native interface inspection, with global/multicast fallback."""
    return sorted({target for _, target in local_ipv4_interfaces()})
