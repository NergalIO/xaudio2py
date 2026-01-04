"""COM initialization helpers."""

import ctypes
from ctypes import wintypes
from xaudio2py.backends.xaudio2.utils import hrcheck
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)

# COM constants
COINIT_MULTITHREADED = 0x0
COINIT_APARTMENTTHREADED = 0x2

# Load ole32.dll for COM functions
try:
    ole32 = ctypes.WinDLL("ole32.dll")
except OSError:
    ole32 = None
    logger.warning("ole32.dll not available, COM initialization may fail")


def CoInitializeEx(dwCoInit: int) -> None:
    """
    Initialize COM library.

    Args:
        dwCoInit: Initialization flags (COINIT_MULTITHREADED or COINIT_APARTMENTTHREADED).

    Raises:
        XAudio2Error: If initialization fails.
    """
    if ole32 is None:
        raise RuntimeError("COM library not available")

    hresult = ole32.CoInitializeEx(None, dwCoInit)
    hrcheck(hresult, "CoInitializeEx failed")


def CoUninitialize() -> None:
    """Uninitialize COM library."""
    if ole32 is not None:
        ole32.CoUninitialize()


class COMInitializer:
    """Context manager for COM initialization."""

    def __init__(self, dwCoInit: int = COINIT_MULTITHREADED):
        self.dwCoInit = dwCoInit
        self._initialized = False

    def __enter__(self):
        CoInitializeEx(self.dwCoInit)
        self._initialized = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._initialized:
            CoUninitialize()
            self._initialized = False

