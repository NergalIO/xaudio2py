"""Data models and configuration classes."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlaybackState(Enum):
    """Playback state enumeration."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class EngineConfig:
    """Configuration for AudioEngine."""

    sample_rate: int = 48000
    """Target sample rate (Hz). Default: 48000."""

    channels: int = 2
    """Number of output channels. Default: 2 (stereo)."""

    bits_per_sample: int = 16
    """Bits per sample. Default: 16."""


@dataclass
class AudioFormat:
    """Audio format specification."""

    sample_rate: int
    """Sample rate in Hz."""

    channels: int
    """Number of channels (1=mono, 2=stereo)."""

    bits_per_sample: int
    """Bits per sample (typically 16)."""

    block_align: int
    """Block alignment in bytes."""

    avg_bytes_per_sec: int
    """Average bytes per second."""

    @property
    def frame_size(self) -> int:
        """Frame size in bytes."""
        return self.block_align

    @property
    def bytes_per_sample(self) -> int:
        """Bytes per sample."""
        return self.bits_per_sample // 8


@dataclass
class SoundData:
    """Loaded audio data."""

    format: AudioFormat
    """Audio format specification."""

    data: bytes
    """Raw PCM audio data."""

    duration_seconds: float
    """Duration in seconds."""

    @property
    def num_frames(self) -> int:
        """Number of audio frames."""
        return len(self.data) // self.format.frame_size


@dataclass
class VoiceParams:
    """Parameters for voice creation."""

    volume: float = 1.0
    """Volume (0.0 to 1.0)."""

    pan: float = 0.0
    """Pan (-1.0 left, 0.0 center, 1.0 right)."""

    loop: bool = False
    """Whether to loop playback."""

