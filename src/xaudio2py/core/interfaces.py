"""Protocol interfaces for audio backend abstraction."""

from typing import Protocol, Optional
from xaudio2py.core.models import AudioFormat, SoundData, VoiceParams, PlaybackState


class IVoice(Protocol):
    """Interface for an audio voice (playback instance)."""

    def start(self) -> None:
        """Start playback."""
        ...

    def stop(self) -> None:
        """Stop playback and flush buffers."""
        ...

    def pause(self) -> None:
        """Pause playback (can be resumed)."""
        ...

    def resume(self) -> None:
        """Resume playback."""
        ...

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        ...

    def set_pan(self, pan: float) -> None:
        """Set pan (-1.0 left, 0.0 center, 1.0 right)."""
        ...

    def get_state(self) -> PlaybackState:
        """Get current playback state."""
        ...

    def destroy(self) -> None:
        """Destroy the voice and free resources."""
        ...


class IAudioBackend(Protocol):
    """Interface for audio backend implementation."""

    def initialize(self) -> None:
        """Initialize the backend (called in worker thread)."""
        ...

    def create_source_voice(
        self, format: AudioFormat, data: bytes, params: VoiceParams
    ) -> IVoice:
        """Create a source voice for playback."""
        ...

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        ...

    def shutdown(self) -> None:
        """Shutdown the backend and free all resources."""
        ...


class IBackendWorker(Protocol):
    """Interface for backend worker thread communication."""

    def start(self) -> None:
        """Start the worker thread."""
        ...

    def stop(self) -> None:
        """Stop the worker thread (blocks until done)."""
        ...

    def execute(self, command, timeout: Optional[float] = None):
        """Execute a command in the worker thread and return result."""
        ...


class IAudioFormat(Protocol):
    """Interface for audio format parsers."""

    @property
    def extensions(self) -> tuple[str, ...]:
        """
        File extensions supported by this format (e.g., ('.wav', '.wave')).
        
        Returns:
            Tuple of supported file extensions (lowercase, with dot).
        """
        ...

    def can_load(self, path: str) -> bool:
        """
        Check if this format can load the given file.
        
        Args:
            path: Path to audio file.
            
        Returns:
            True if this format can load the file, False otherwise.
        """
        ...

    def load(self, path: str) -> SoundData:
        """
        Load an audio file and return SoundData.
        
        Args:
            path: Path to audio file.
            
        Returns:
            SoundData with format and PCM data.
            
        Raises:
            InvalidAudioFormat: If format is not supported.
            FileNotFoundError: If file does not exist.
            IOError: If file cannot be read.
        """
        ...
