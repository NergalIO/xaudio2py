"""
xaudio2py - Python wrapper for XAudio2 using ctypes.

This package provides a high-level Python API for audio playback on Windows
using XAudio2, with support for WAV files, multiple simultaneous playbacks,
volume control, panning, and looping.
"""

from xaudio2py.api.engine import AudioEngine
from xaudio2py.api.sound import Sound, PlaybackHandle
from xaudio2py.core.models import EngineConfig, PlaybackState
from xaudio2py.core.exceptions import (
    XAudio2Error,
    InvalidAudioFormat,
    EngineNotStarted,
    PlaybackNotFound,
)

__version__ = "0.1.0"

__all__ = [
    "AudioEngine",
    "Sound",
    "PlaybackHandle",
    "EngineConfig",
    "PlaybackState",
    "XAudio2Error",
    "InvalidAudioFormat",
    "EngineNotStarted",
    "PlaybackNotFound",
]

