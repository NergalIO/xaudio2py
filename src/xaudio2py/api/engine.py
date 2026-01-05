"""AudioEngine - main public API facade."""

from typing import Optional
from xaudio2py.api.sound import PlaybackHandle, Sound
from xaudio2py.core.exceptions import EngineNotStartedError
from xaudio2py.core.interfaces import IAudioBackend
from xaudio2py.core.models import EngineConfig
from xaudio2py.formats import load_audio
from xaudio2py.services.engine_lifecycle import EngineLifecycleService
from xaudio2py.services.playback import PlaybackService
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


class AudioEngine:
    """
    Main audio engine facade.
    
    This class provides a high-level API for audio playback and acts as a facade
    that delegates all operations to specialized services:
    - EngineLifecycleService: Manages engine lifecycle
    - PlaybackService: Manages playback operations
    
    Responsibilities:
    - Provide simple, unified API
    - Delegate to services
    - Maintain backward compatibility
    
    This class does NOT:
    - Manage threads directly
    - Store playback state
    - Execute backend operations
    """

    def __init__(
        self,
        config: EngineConfig = EngineConfig(),
        backend: Optional[IAudioBackend] = None,
    ):
        """
        Initialize AudioEngine.

        Args:
            config: Engine configuration.
            backend: Optional backend implementation (default: XAudio2Backend).
        """
        self._config = config
        
        # Initialize backend if not provided
        if backend is None:
            # Lazy import to avoid loading XAudio2 DLL on import
            from xaudio2py.backends.xaudio2.backend import XAudio2Backend
            backend = XAudio2Backend()
        
        # Initialize services
        self._lifecycle_service = EngineLifecycleService(backend, config)
        self._playback_service: Optional[PlaybackService] = None

    def start(self) -> None:
        """
        Start the audio engine.
        
        Raises:
            RuntimeError: If engine fails to start.
        """
        self._lifecycle_service.start()
        
        # Initialize playback service after lifecycle is started
        worker = self._lifecycle_service.worker
        backend = self._lifecycle_service.backend
        self._playback_service = PlaybackService(worker, backend)
        
        logger.info("AudioEngine started")

    def shutdown(self) -> None:
        """
        Shutdown the audio engine and free all resources.
        
        This method is idempotent and safe to call multiple times.
        """
        # Stop all playbacks first
        if self._playback_service is not None:
            try:
                self._playback_service.stop_all()
            except Exception as e:
                logger.warning(f"Error stopping all playbacks during shutdown: {e}")
        
        # Shutdown lifecycle service
        self._lifecycle_service.shutdown()
        self._playback_service = None
        
        logger.info("AudioEngine shut down")

    def load(self, path: str) -> Sound:
        """
        Automatically detect and load an audio file.

        Supports all registered audio formats (WAV, MP3, etc.).
        The format is automatically detected based on file extension
        and file header.

        Args:
            path: Path to audio file.

        Returns:
            Sound object.

        Raises:
            FileNotFoundError: If file does not exist.
            AudioFormatError: If format is not supported or cannot be decoded.
        """
        data = load_audio(path)
        return Sound(data, path)

    def play(
        self,
        sound: Sound,
        *,
        volume: float = 1.0,
        pan: float = 0.0,
        loop: bool = False,
    ) -> PlaybackHandle:
        """
        Start playback of a sound.

        Args:
            sound: Sound to play.
            volume: Volume (0.0 to 1.0). Default: 1.0.
            pan: Pan (-1.0 left, 0.0 center, 1.0 right). Default: 0.0.
            loop: Whether to loop playback. Default: False.

        Returns:
            PlaybackHandle for controlling playback.

        Raises:
            EngineNotStartedError: If engine is not started.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine must be started before playing sounds")
        
        return self._playback_service.start_playback(sound, volume=volume, pan=pan, loop=loop)

    def stop(self, handle: PlaybackHandle) -> None:
        """
        Stop playback.

        Args:
            handle: Playback handle.

        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine not started")
        
        self._playback_service.stop_playback(handle)

    def pause(self, handle: PlaybackHandle) -> None:
        """
        Pause playback.

        Args:
            handle: Playback handle.

        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine not started")
        
        self._playback_service.pause_playback(handle)

    def resume(self, handle: PlaybackHandle) -> None:
        """
        Resume playback.

        Args:
            handle: Playback handle.

        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine not started")
        
        self._playback_service.resume_playback(handle)

    def set_volume(self, handle: PlaybackHandle, volume: float) -> None:
        """
        Set volume for a playback.

        Args:
            handle: Playback handle.
            volume: Volume (0.0 to 1.0).

        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine not started")
        
        self._playback_service.set_volume(handle, volume)

    def set_pan(self, handle: PlaybackHandle, pan: float) -> None:
        """
        Set pan for a playback.

        Args:
            handle: Playback handle.
            pan: Pan (-1.0 left, 0.0 center, 1.0 right).

        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine not started")
        
        self._playback_service.set_pan(handle, pan)

    def set_master_volume(self, volume: float) -> None:
        """
        Set master volume.

        Args:
            volume: Volume (0.0 to 1.0).

        Raises:
            EngineNotStartedError: If engine is not started.
        """
        if not self._lifecycle_service.is_started:
            raise EngineNotStartedError("Engine not started")
        
        from xaudio2py.utils.validate import validate_volume
        volume = validate_volume(volume)
        
        worker = self._lifecycle_service.worker
        backend = self._lifecycle_service.backend
        worker.execute(lambda: backend.set_master_volume(volume))

    def is_playing(self, handle: PlaybackHandle) -> bool:
        """
        Check if playback is currently playing.

        Args:
            handle: Playback handle.

        Returns:
            True if playing, False otherwise.

        Raises:
            EngineNotStartedError: If engine is not started.
        """
        if self._playback_service is None:
            raise EngineNotStartedError("Engine not started")
        
        return self._playback_service.is_playing(handle)

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
