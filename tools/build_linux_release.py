"""Build and verify a self-contained Linux application tarball."""
import argparse
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tarfile
import tempfile

if __package__:
    from .public_release_guard import check_public_source
else:
    from public_release_guard import check_public_source

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = (
    "core/dashboard.html", "core/tv-client.bundle",
    "assets/sidee-logo.png", "assets/nuvio-wordmark.png", "assets/jellyfin.png",
    "README.md", "LICENSE",
)


def run(*arguments, **kwargs):
    return subprocess.run([str(value) for value in arguments], check=True, **kwargs)


def normalized_architecture(value):
    aliases = {"x86_64": "x86_64", "amd64": "x86_64", "x64": "x86_64",
               "aarch64": "aarch64", "arm64": "aarch64"}
    try:
        return aliases[value.lower()]
    except KeyError:
        raise ValueError(f"Unsupported Linux architecture: {value}") from None


def validate_version(value):
    value = value.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", value):
        raise ValueError("The release version must use X.Y.Z or X.Y.Z.N.")
    return value


def verify_bundle(bundle, architecture=None):
    """Check the real PyInstaller output before packaging it for users."""
    bundle = Path(bundle)
    executable = bundle / "sidee"
    if not executable.is_file():
        raise RuntimeError("The Linux executable is missing.")
    if not os.access(executable, os.X_OK):
        raise RuntimeError("The Linux executable is not executable.")
    for relative in RESOURCES:
        # PyInstaller 6 places bundled data under _internal on Linux.
        candidates = (bundle / relative, bundle / "_internal" / relative)
        if not any(candidate.is_file() for candidate in candidates):
            raise RuntimeError(f"The Linux build is missing {relative}.")
    with executable.open("rb") as stream:
        magic = stream.read(4)
    if magic != b"\x7fELF":
        raise RuntimeError("The Linux executable is not a native ELF binary.")
    if architecture:
        machine = run("file", "-b", executable, capture_output=True, text=True).stdout
        expected = {"x86_64": "x86-64", "aarch64": "aarch64"}[architecture]
        if expected not in machine.lower():
            raise RuntimeError(f"The Linux executable is not {architecture}: {machine.strip()}")
    print(f"Verified Sidee Linux bundle for {architecture or platform.machine()}.")
    return executable


def package_bundle(bundle, architecture):
    distribution = ROOT / "dist"
    distribution.mkdir(parents=True, exist_ok=True)
    destination = distribution / f"Sidee-linux-{architecture}.tar.gz"
    fd, temporary = tempfile.mkstemp(prefix=".sidee-linux-", suffix=".tar.gz",
                                     dir=distribution)
    os.close(fd)
    temporary = Path(temporary)
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            archive.add(bundle, arcname="Sidee")
            for name in ("README.md", "LICENSE"):
                archive.add(ROOT / name, arcname=f"Sidee/{name}")
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(destination)
    return destination


def build(architecture=None, version="0.1.4.2", package_only=False):
    if not sys.platform.startswith("linux"):
        raise RuntimeError("Linux bundles must be built on Linux; use the GitHub Actions workflow.")
    architecture = normalized_architecture(architecture or platform.machine())
    validate_version(version)
    check_public_source(ROOT)
    bundle = ROOT / "dist" / "Sidee"
    if not package_only:
        run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--distpath", ROOT / "dist", "--workpath", ROOT / "build" / "linux" / "pyinstaller",
            ROOT / "packaging" / "linux.spec", cwd=ROOT)
    verify_bundle(bundle, architecture)
    return package_bundle(bundle, architecture)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture", choices=("x86_64", "aarch64"),
                        default=normalized_architecture(platform.machine()))
    parser.add_argument("--version", default=os.environ.get("SIDEE_BUILD_VERSION", "0.1.4.2"))
    parser.add_argument("--package-only", action="store_true",
                        help="Package an existing dist/Sidee without rebuilding it.")
    arguments = parser.parse_args()
    print(build(arguments.architecture, arguments.version, arguments.package_only))


if __name__ == "__main__":
    main()
