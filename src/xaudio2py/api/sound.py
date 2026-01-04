"""Sound and PlaybackHandle classes."""

import uuid
from dataclasses import dataclass
from xaudio2py.core.models import SoundData, PlaybackState


@dataclass
class PlaybackHandle:
    """Handle for a playback instance."""

    id: str
    """Unique identifier for this playback."""

    def __str__(self) -> str:
        return f"PlaybackHandle({self.id})"


class Sound:
    """Represents a loaded audio file."""

    def __init__(self, data: SoundData, path: str):
        """
        Initialize Sound.

        Args:
            data: Loaded audio data.
            path: Path to the source file.
        """
        self._data = data
        self._path = path

    @property
    def data(self) -> SoundData:
        """Get audio data."""
        return self._data

    @property
    def path(self) -> str:
        """Get source file path."""
        return self._path

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        return self._data.duration_seconds

