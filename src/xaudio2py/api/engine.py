"""AudioEngine - main public API."""

import time
import uuid
from typing import Dict, Optional
from xaudio2py.api.sound import Sound, PlaybackHandle
from xaudio2py.backends.null_backend import NullBackend
from xaudio2py.core.exceptions import EngineNotStarted, PlaybackNotFound
from xaudio2py.core.interfaces import IAudioBackend
from xaudio2py.core.models import EngineConfig, PlaybackState, VoiceParams
from xaudio2py.core.thread import BackendWorker
from xaudio2py.formats.wav import load_wav
from xaudio2py.formats.mp3 import load_mp3
from xaudio2py.utils.log import get_logger
from xaudio2py.utils.validate import validate_pan, validate_volume

logger = get_logger(__name__)


class AudioEngine:
    """
    Main audio engine facade.

    Provides a high-level API for audio playback with thread-safe operations.
    All XAudio2 operations are executed in a dedicated worker thread.
    """

    def __init__(
        self, config: EngineConfig = EngineConfig(), backend: Optional[IAudioBackend] = None
    ):
        """
        Initialize AudioEngine.

        Args:
            config: Engine configuration.
            backend: Optional backend implementation (default: XAudio2Backend).
        """
        self._config = config
        self._backend = backend
        if self._backend is None:
            # Lazy import to avoid loading XAudio2 DLL on import
            from xaudio2py.backends.xaudio2.backend import XAudio2Backend
            self._backend = XAudio2Backend()

        self._worker: Optional[BackendWorker] = None
        self._started = False
        self._playbacks: Dict[str, PlaybackInfo] = {}

    def start(self) -> None:
        """Start the audio engine."""
        if self._started:
            return

        self._worker = BackendWorker(self._backend)
        self._worker.start()
        self._started = True
        logger.info("AudioEngine started")

    def shutdown(self) -> None:
        """Shutdown the audio engine and free all resources."""
        if not self._started:
            return

        logger.info("Shutting down AudioEngine...")

        # Stop all playbacks
        for handle_id in list(self._playbacks.keys()):
            try:
                self.stop(PlaybackHandle(handle_id))
            except Exception as e:
                logger.warning(f"Error stopping playback {handle_id}: {e}")

        # Shutdown backend
        if self._worker is not None:
            self._worker.execute(self._backend.shutdown)
            self._worker.stop()
            self._worker = None

        self._playbacks.clear()
        self._started = False
        logger.info("AudioEngine shut down")

    def load_wav(self, path: str) -> Sound:
        """
        Load a WAV file.

        Args:
            path: Path to WAV file.

        Returns:
            Sound object.

        Raises:
            FileNotFoundError: If file does not exist.
            InvalidAudioFormat: If format is not supported.
        """
        data = load_wav(path)
        return Sound(data, path)

    def load_mp3(self, path: str) -> Sound:
        """
        Load an MP3 file.

        MP3 files are automatically converted to 16-bit PCM format
        compatible with XAudio2. Supports automatic resampling to
        44100 or 48000 Hz if needed.

        Args:
            path: Path to MP3 file.

        Returns:
            Sound object.

        Raises:
            FileNotFoundError: If file does not exist.
            InvalidAudioFormat: If format cannot be decoded.
            ImportError: If pydub is not installed.
        """
        data = load_mp3(path)
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
            EngineNotStarted: If engine is not started.
        """
        if not self._started:
            raise EngineNotStarted("Engine must be started before playing sounds")

        volume = validate_volume(volume)
        pan = validate_pan(pan)

        # Create voice in worker thread
        params = VoiceParams(volume=volume, pan=pan, loop=loop)
        # Create voice and start playback (start is called inside create_source_voice)
        voice = self._worker.execute(
            lambda: self._backend.create_source_voice(
                sound.data.format, sound.data.data, params
            )
        )

        # Create handle and track playback
        handle_id = str(uuid.uuid4())
        handle = PlaybackHandle(handle_id)
        playback_info = PlaybackInfo(
            handle=handle,
            voice=voice,
            sound=sound,
            params=params,
            start_time=time.monotonic(),
        )
        self._playbacks[handle_id] = playback_info

        logger.debug(f"Started playback {handle_id}")
        return handle

    def stop(self, handle: PlaybackHandle) -> None:
        """
        Stop playback.

        Args:
            handle: Playback handle.

        Raises:
            EngineNotStarted: If engine is not started.
            PlaybackNotFound: If handle is invalid.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        playback_info = self._playbacks.get(handle.id)
        if playback_info is None:
            raise PlaybackNotFound(f"Playback handle not found: {handle.id}")

        self._worker.execute(playback_info.voice.stop)
        del self._playbacks[handle.id]
        logger.debug(f"Stopped playback {handle.id}")

    def pause(self, handle: PlaybackHandle) -> None:
        """
        Pause playback.

        Args:
            handle: Playback handle.

        Raises:
            EngineNotStarted: If engine is not started.
            PlaybackNotFound: If handle is invalid.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        playback_info = self._playbacks.get(handle.id)
        if playback_info is None:
            raise PlaybackNotFound(f"Playback handle not found: {handle.id}")

        self._worker.execute(playback_info.voice.pause)
        logger.debug(f"Paused playback {handle.id}")

    def resume(self, handle: PlaybackHandle) -> None:
        """
        Resume playback.

        Args:
            handle: Playback handle.

        Raises:
            EngineNotStarted: If engine is not started.
            PlaybackNotFound: If handle is invalid.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        playback_info = self._playbacks.get(handle.id)
        if playback_info is None:
            raise PlaybackNotFound(f"Playback handle not found: {handle.id}")

        self._worker.execute(playback_info.voice.resume)
        logger.debug(f"Resumed playback {handle.id}")

    def set_volume(self, handle: PlaybackHandle, volume: float) -> None:
        """
        Set volume for a playback.

        Args:
            handle: Playback handle.
            volume: Volume (0.0 to 1.0).

        Raises:
            EngineNotStarted: If engine is not started.
            PlaybackNotFound: If handle is invalid.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        playback_info = self._playbacks.get(handle.id)
        if playback_info is None:
            raise PlaybackNotFound(f"Playback handle not found: {handle.id}")

        volume = validate_volume(volume)
        self._worker.execute(lambda: playback_info.voice.set_volume(volume))
        playback_info.params.volume = volume

    def set_pan(self, handle: PlaybackHandle, pan: float) -> None:
        """
        Set pan for a playback.

        Args:
            handle: Playback handle.
            pan: Pan (-1.0 left, 0.0 center, 1.0 right).

        Raises:
            EngineNotStarted: If engine is not started.
            PlaybackNotFound: If handle is invalid.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        playback_info = self._playbacks.get(handle.id)
        if playback_info is None:
            raise PlaybackNotFound(f"Playback handle not found: {handle.id}")

        pan = validate_pan(pan)
        self._worker.execute(lambda: playback_info.voice.set_pan(pan))
        playback_info.params.pan = pan

    def set_master_volume(self, volume: float) -> None:
        """
        Set master volume.

        Args:
            volume: Volume (0.0 to 1.0).

        Raises:
            EngineNotStarted: If engine is not started.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        volume = validate_volume(volume)
        self._worker.execute(lambda: self._backend.set_master_volume(volume))

    def is_playing(self, handle: PlaybackHandle) -> bool:
        """
        Check if playback is currently playing.

        Args:
            handle: Playback handle.

        Returns:
            True if playing, False otherwise.

        Raises:
            EngineNotStarted: If engine is not started.
            PlaybackNotFound: If handle is invalid.
        """
        if not self._started:
            raise EngineNotStarted("Engine not started")

        playback_info = self._playbacks.get(handle.id)
        if playback_info is None:
            logger.debug(f"is_playing: handle {handle.id} not found")
            return False

        # Get state from voice
        state = self._worker.execute(playback_info.voice.get_state)
        
        elapsed = time.monotonic() - playback_info.start_time
        logger.info(
            f"is_playing: handle={handle.id}, state={state}, "
            f"elapsed={elapsed:.3f}s"
        )

        # Also check time-based completion for non-looping sounds
        if state == PlaybackState.PLAYING and not playback_info.params.loop:
            if elapsed >= playback_info.sound.duration:
                logger.info(f"is_playing: playback completed (duration {elapsed:.3f}s >= {playback_info.sound.duration:.3f}s)")
                return False

        result = state == PlaybackState.PLAYING
        logger.info(f"is_playing: returning {result}")
        return result

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


class PlaybackInfo:
    """Internal playback tracking information."""

    def __init__(
        self,
        handle: PlaybackHandle,
        voice,
        sound: Sound,
        params: VoiceParams,
        start_time: float,
    ):
        self.handle = handle
        self.voice = voice
        self.sound = sound
        self.params = params
        self.start_time = start_time

