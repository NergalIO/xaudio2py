"""Exception classes for xaudio2py."""


def hr_to_hex(hr: int) -> str:
    """Convert HRESULT to readable hex string (unsigned 32-bit)."""
    return f"0x{(hr & 0xFFFFFFFF):08X}"


class XAudio2Error(Exception):
    """Base exception for XAudio2-related errors."""

    def __init__(self, hresult: int, message: str = ""):
        self.hresult = hresult
        self.message = message
        super().__init__(f"XAudio2 error (HRESULT: {hr_to_hex(hresult)}): {message}")


class InvalidAudioFormat(Exception):
    """Raised when audio format is not supported."""

    pass


class EngineNotStarted(Exception):
    """Raised when engine operations are attempted before start()."""

    pass


class PlaybackNotFound(Exception):
    """Raised when a playback handle is invalid or not found."""

    pass

