from pathlib import Path


project_dir = Path(SPECPATH).parent
icon_file = project_dir / "build" / "AirMouse.ico"
version_file = project_dir / "build" / "version_info.txt"

datas = [
    (str(project_dir / "templates"), "templates"),
    (str(project_dir / "static"), "static"),
    (str(project_dir / "cert.pem"), "."),
    (str(project_dir / "key.pem"), "."),
    (str(project_dir / "macro_configs.json"), "."),
    (str(project_dir / "gamepad_configs.json"), "."),
]

hiddenimports = [
    "engineio.async_drivers.threading",
    "pystray._win32",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
]

a = Analysis(
    [str(project_dir / "server.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="AirMouse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_file) if icon_file.exists() else None,
    version=str(version_file) if version_file.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AirMouse",
)
