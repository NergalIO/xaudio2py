"""ctypes bindings for XAudio2 structures and constants."""

from ctypes import (
    Structure,
    c_uint8,
    c_uint16,
    c_uint32,
    c_uint64,
    c_void_p,
    POINTER,
    c_float,
    c_char,
    sizeof,
)
from xaudio2py.backends.xaudio2.utils import hrcheck

# Constants
XAUDIO2_DEFAULT_PROCESSOR = 0x00000001
XAUDIO2_DEBUG_ENGINE = 0x00000001

XAUDIO2_END_OF_STREAM = 0x00000040
XAUDIO2_LOOP_INFINITE = 0xFFFFFFFF

# WAVEFORMATEX constants
WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_EXTENSIBLE = 0xFFFE

# GUID structure
class GUID(Structure):
    """GUID structure."""

    _fields_ = [
        ("Data1", c_uint32),
        ("Data2", c_uint16),
        ("Data3", c_uint16),
        ("Data4", c_uint8 * 8),
    ]


# WAVEFORMATEX
class WAVEFORMATEX(Structure):
    """WAVEFORMATEX structure."""

    _fields_ = [
        ("wFormatTag", c_uint16),
        ("nChannels", c_uint16),
        ("nSamplesPerSec", c_uint32),
        ("nAvgBytesPerSec", c_uint32),
        ("nBlockAlign", c_uint16),
        ("wBitsPerSample", c_uint16),
        ("cbSize", c_uint16),
    ]


# WAVEFORMATEXTENSIBLE (for future extensibility)
class WAVEFORMATEXTENSIBLE(Structure):
    """WAVEFORMATEXTENSIBLE structure."""

    _fields_ = [
        ("Format", WAVEFORMATEX),
        ("Samples", c_uint16),  # Union: wValidBitsPerSample or wSamplesPerBlock
        ("dwChannelMask", c_uint32),
        ("SubFormat", GUID),
    ]


# XAUDIO2_BUFFER
class XAUDIO2_BUFFER(Structure):
    """
    XAUDIO2_BUFFER structure.
    
    For x64, ensure proper alignment - pointers are 8 bytes.
    """
    _pack_ = 8  # Ensure 8-byte alignment for x64
    
    _fields_ = [
        ("Flags", c_uint32),
        ("AudioBytes", c_uint32),
        ("pAudioData", POINTER(c_uint8)),  # BYTE* - must be POINTER, not c_char_p
        ("PlayBegin", c_uint32),
        ("PlayLength", c_uint32),
        ("LoopBegin", c_uint32),
        ("LoopLength", c_uint32),
        ("LoopCount", c_uint32),
        ("pContext", c_void_p),
    ]


# XAUDIO2_VOICE_STATE
class XAUDIO2_VOICE_STATE(Structure):
    """XAUDIO2_VOICE_STATE structure."""

    _fields_ = [
        ("pCurrentBufferContext", c_void_p),
        ("BuffersQueued", c_uint32),
        ("SamplesPlayed", c_uint64),
    ]


def create_waveformatex(
    sample_rate: int, channels: int, bits_per_sample: int
) -> WAVEFORMATEX:
    """Create WAVEFORMATEX structure."""
    fmt = WAVEFORMATEX()
    fmt.wFormatTag = WAVE_FORMAT_PCM
    fmt.nChannels = channels
    fmt.nSamplesPerSec = sample_rate
    fmt.wBitsPerSample = bits_per_sample
    fmt.nBlockAlign = (channels * bits_per_sample) // 8
    fmt.nAvgBytesPerSec = sample_rate * fmt.nBlockAlign
    fmt.cbSize = 0
    return fmt

