"""Preset catalog: apps ready to install with one click."""
from __future__ import annotations

import re
import ipaddress
from urllib.parse import quote, urlsplit, urlunsplit

PRESETS: dict[str, dict] = {
    "nuvio": {
        "name": "Nuvio",
        "app_id": "nuviodebug",
        "url": "https://nuviotvsmart.vercel.app/vidaa.html",
        # VIDAA launcher icons are square; the horizontal wordmark is stretched.
        "image": "https://nuviotvsmart.vercel.app/assets/images/tizenIcon.png",
        "icon": "assets/nuvio-wordmark.png",
        "description": "Browse and stream your library",
    },
    "stremio": {
        "name": "Stremio",
        # Keep the existing Sidee app id so reinstalling replaces the old
        # web.stremio.com tile instead of leaving a duplicate behind.
        "app_id": "stremiodebug",
        "url": "https://noobygains.github.io/stremio-vidaa-tv/?install_source=sidee",
        "server_builder": "stremio",
        "server_optional": True,
        "server_placeholder": "Streaming server URL (optional)",
        "image": "https://noobygains.github.io/stremio-vidaa-tv/icon.png",
        "description": "Full Stremio TV for VIDAA with D-pad navigation",
    },
    "jellyfin": {
        "name": "Jellyfin",
        "app_id": "jellyfin",
        "url": "",  # built from the user's server address
        "needs_server": True,
        "server_placeholder": "Your server's IP or URL",
        "image": "https://raw.githubusercontent.com/Empi9245/Sidee/main/assets/jellyfin-tile-bold.png",
        "icon": "assets/jellyfin.png",
        "description": "Your media from your Jellyfin server",
    },
    "smarttube": {
        "name": "SmartTube",
        "app_id": "smarttube16",
        # No default host: each user must supply their own self-hosted build.
        "needs_url": True,
        "supports_custom_url": True,
        "url": "",
        "url_placeholder": "https://… or http://192.168.…:8090/",
        "image": "https://raw.githubusercontent.com/antmagl/smarttube-vidaa/main/vidaa/icon.png",
        "icon": "assets/smarttube.png",
        "description": "Ad-free YouTube for VIDAA with SponsorBlock",
    },
}


def get(key: str) -> dict | None:
    return PRESETS.get(key.lower())


def is_private_host(server: str) -> bool:
    """True for local/private network (LAN) hosts: HTTP is allowed only there."""
    host = (urlsplit(server if "://" in server else "//" + server).hostname or "").rstrip(".")
    if host.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(network) for network in
               ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))


def build_server_url(server: str) -> str:
    """Server address -> web client URL, including scheme and path."""
    server = server.strip().rstrip("/")
    has_scheme = "://" in server
    parsed = urlsplit(server if has_scheme else "//" + server)
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        raise ValueError("Enter your Jellyfin server's LAN IP or full URL.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if (host == "localhost" or host.endswith(".localhost") or
            (address and (address.is_loopback or address.is_unspecified))):
        raise ValueError("Use your Jellyfin server's LAN IP or URL; localhost "
                         "and loopback addresses refer to the TV itself.")
    port = parsed.port  # also rejects malformed or out-of-range ports
    scheme = parsed.scheme if has_scheme else ("http" if is_private_host(server) else "https")
    authority = parsed.netloc
    if not has_scheme and port is None:
        authority += ":8096"  # default Jellyfin port
    path = parsed.path.rstrip("/")
    if not re.search(r"/web(/index\.html)?$", path):
        path += "/web/index.html"
    return urlunsplit((scheme, authority, path, parsed.query, parsed.fragment))


def build_stremio_url(server: str = "") -> str:
    """Build the VIDAA-optimised full Stremio TV URL.

    This community TV build uses the Stremio Theater interface with a modern
    stremio-core-web engine and VIDAA-specific focus, keyboard and viewport
    fixes. Its server query parameter can point to a LAN Stremio server or
    to the Remote HTTPS URL exposed by Stremio Service/Desktop. Loopback
    addresses would point back to the TV.
    """
    base = "https://noobygains.github.io/stremio-vidaa-tv/?install_source=sidee"
    server = server.strip().rstrip("/")
    if not server:
        return base
    parsed = urlsplit(server)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            "Paste the full Stremio streaming server URL, including http:// or https://.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if (host == "localhost" or host.endswith(".localhost") or
            (address and (address.is_loopback or address.is_unspecified))):
        raise ValueError(
            "Use the Stremio server address reachable by your TV; localhost points to the TV itself.")
    normalized = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path or "", parsed.query, parsed.fragment))
    return base + "&server=" + quote(normalized, safe="")


def build_app_url(value: str) -> str:
    """Address of a user-hosted web app -> a validated launcher-tile URL.

    SmartTube is a static web app, so Sidee only needs to know where the TV
    can reach it. HTTP is allowed only on a LAN host; public hosts must use
    HTTPS. Loopback would point at the TV itself and is rejected.
    """
    value = value.strip()
    if not value:
        raise ValueError("Enter the address where SmartTube is hosted.")
    if "://" not in value:
        value = ("http://" if is_private_host(value) else "https://") + value
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Use the full address of the hosted SmartTube app.")
    if parsed.username or parsed.password:
        raise ValueError("The app address must not contain a username or password.")
    if parsed.query or parsed.fragment:
        raise ValueError("Remove the query string or fragment from the app address.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if (host == "localhost" or host.endswith(".localhost") or
            (address and (address.is_loopback or address.is_unspecified
                          or address.is_link_local or address.is_multicast))):
        raise ValueError("Use the address your TV can reach; localhost points "
                         "at the TV itself.")
    path = parsed.path or "/"
    # Use an explicit index.html so the TV reports back exactly the address
    # Sidee sent. Some launchers normalise a bare "/" and then the install
    # confirmation cannot find the tile.
    if path.endswith("/"):
        path += "index.html"
    elif not path.rsplit("/", 1)[-1].endswith(".html"):
        path += "/index.html"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
