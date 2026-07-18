import os
import shutil
import sys
from pathlib import Path


APP_NAME = "AirMouse"


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def resource_root():
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


def resource_path(*parts):
    return resource_root().joinpath(*parts)


def executable_path():
    if is_frozen():
        return Path(sys.executable).resolve()
    return Path(sys.executable).resolve()


def config_dir():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def log_dir():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / APP_NAME / "logs"
    return config_dir() / "logs"


def config_path(filename):
    return config_dir() / filename


def ensure_user_config(filename):
    destination = config_path(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        source = resource_path(filename)
        if source.exists():
            shutil.copy2(source, destination)
    return destination
