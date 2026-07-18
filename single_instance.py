import os
import sys

from app_paths import config_dir


class SingleInstance:
    def __init__(self, name="AirMouse.Remote"):
        self.name = name
        self._handle = None
        self._file = None

    def acquire(self):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            self._handle = kernel32.CreateMutexW(None, False, f"Local\\{self.name}")
            if not self._handle:
                raise ctypes.WinError()
            if kernel32.GetLastError() == 183:
                kernel32.CloseHandle(self._handle)
                self._handle = None
                return False
            return True

        import fcntl

        lock_path = config_dir() / f"{self.name}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._file.close()
            self._file = None
            return False
        self._file.seek(0)
        self._file.truncate()
        self._file.write(str(os.getpid()))
        self._file.flush()
        return True

    def release(self):
        if sys.platform == "win32" and self._handle:
            import ctypes
            from ctypes import wintypes

            ctypes.windll.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            ctypes.windll.kernel32.CloseHandle.restype = wintypes.BOOL
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None
        elif self._file:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._file.close()
            self._file = None

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("AirMouse 已经在运行")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
