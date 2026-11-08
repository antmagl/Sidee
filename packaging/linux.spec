# Build on Linux; PyInstaller does not cross-compile this bundle.
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "linux_launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "core" / "dashboard.html"), "core"),
        (str(root / "core" / "tv-client.bundle"), "core"),
        (str(root / "assets" / "sidee-logo.png"), "assets"),
        (str(root / "assets" / "nuvio-wordmark.png"), "assets"),
        (str(root / "assets" / "jellyfin.png"), "assets"),
        (str(root / "README.md"), "."),
        (str(root / "LICENSE"), "."),
    ],
    hiddenimports=["tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.font"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="sidee",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Sidee",
)
