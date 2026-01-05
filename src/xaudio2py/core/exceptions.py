"""Exception classes for xaudio2py."""


def hr_to_hex(hr: int) -> str:
    """Convert HRESULT to readable hex string (unsigned 32-bit)."""
    return f"0x{(hr & 0xFFFFFFFF):08X}"


class AudioEngineError(Exception):
    """Base exception for audio engine errors."""
    pass


class EngineNotStartedError(AudioEngineError):
    """Raised when engine operations are attempted before start()."""
    pass


class PlaybackNotFoundError(AudioEngineError):
    """Raised when a playback handle is invalid or not found."""
    pass


class BackendError(AudioEngineError):
    """Raised when backend operation fails."""
    
    def __init__(self, message: str, hresult: int = 0):
        self.hresult = hresult
        self.message = message
        if hresult != 0:
            super().__init__(f"Backend error (HRESULT: {hr_to_hex(hresult)}): {message}")
        else:
            super().__init__(f"Backend error: {message}")


class AudioFormatError(AudioEngineError):
    """Raised when audio format is not supported or cannot be decoded."""
    pass


# Backward compatibility aliases
XAudio2Error = BackendError
InvalidAudioFormat = AudioFormatError
EngineNotStarted = EngineNotStartedError
PlaybackNotFound = PlaybackNotFoundError
