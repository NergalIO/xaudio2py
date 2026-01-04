"""DLL loader and function resolution for XAudio2."""

import os
import sys
from ctypes import WinDLL, c_void_p, POINTER, Structure
from pathlib import Path
from typing import Optional, Tuple
from xaudio2py.core.exceptions import XAudio2Error
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)

# DLL search order
DLL_NAMES = [
    "xaudio2_9redist.dll",
    "xaudio2_9.dll",
    "xaudio2_8.dll",
    "xaudio2_7.dll",
]


class XAudio2DLL:
    """XAudio2 DLL loader and function resolver."""

    def __init__(self):
        self._dll: Optional[WinDLL] = None
        self._dll_path: Optional[str] = None
        self._XAudio2Create = None

    def load(self) -> Tuple[WinDLL, str]:
        """
        Load XAudio2 DLL and resolve functions.

        Returns:
            Tuple of (WinDLL instance, DLL path).

        Raises:
            XAudio2Error: If DLL cannot be loaded or functions not found.
        """
        if self._dll is not None:
            return self._dll, self._dll_path

        # Try to find DLL
        dll_path = self._find_dll()
        if dll_path is None:
            raise XAudio2Error(
                0x80070002,  # ERROR_FILE_NOT_FOUND
                f"XAudio2 DLL not found. Tried: {', '.join(DLL_NAMES)}",
            )

        # Load DLL
        try:
            dll = WinDLL(dll_path)
        except OSError as e:
            raise XAudio2Error(
                0x80070005,  # ERROR_ACCESS_DENIED
                f"Failed to load {dll_path}: {e}",
            )

        # Resolve XAudio2Create
        try:
            XAudio2Create = dll.XAudio2Create
        except AttributeError:
            raise XAudio2Error(
                0x80070002,  # ERROR_FILE_NOT_FOUND
                f"XAudio2Create not found in {dll_path}",
            )

        # Set function signature
        # XAudio2Create(ppXAudio2: POINTER(c_void_p), Flags: UINT32, XAudio2Processor: UINT32)
        from ctypes import c_uint32
        XAudio2Create.argtypes = [POINTER(c_void_p), c_uint32, c_uint32]
        XAudio2Create.restype = c_uint32  # HRESULT

        self._dll = dll
        self._dll_path = dll_path
        self._XAudio2Create = XAudio2Create

        logger.info(f"Loaded XAudio2 DLL: {dll_path}")
        return dll, dll_path

    def get_XAudio2Create(self):
        """Get XAudio2Create function."""
        if self._XAudio2Create is None:
            self.load()
        return self._XAudio2Create

    def _find_dll(self) -> Optional[str]:
        """Find XAudio2 DLL in search paths."""
        # Search paths:
        # 1. Current directory
        # 2. bin/ directory (project structure)
        # 3. System PATH
        search_paths = [
            Path.cwd(),
            Path(__file__).parent.parent.parent.parent.parent / "bin",  # repo/bin
            Path(sys.executable).parent,  # Python directory
        ]

        # Also check system directories
        system_dirs = [
            Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32",
            Path(os.environ.get("SystemRoot", "C:\\Windows")) / "SysWOW64",
        ]
        search_paths.extend(system_dirs)

        for dll_name in DLL_NAMES:
            for search_path in search_paths:
                dll_path = search_path / dll_name
                if dll_path.exists():
                    return str(dll_path)

        return None


# Global instance
_dll_loader = XAudio2DLL()


def get_dll() -> Tuple[WinDLL, str]:
    """Get loaded XAudio2 DLL."""
    return _dll_loader.load()


def get_XAudio2Create():
    """Get XAudio2Create function."""
    return _dll_loader.get_XAudio2Create()

