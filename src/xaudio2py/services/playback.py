"""Service for managing audio playback operations."""

import time
import uuid
from typing import Optional
from xaudio2py.api.sound import PlaybackHandle, Sound
from xaudio2py.core.exceptions import EngineNotStartedError, PlaybackNotFoundError
from xaudio2py.core.interfaces import IBackendWorker, IVoice
from xaudio2py.core.models import PlaybackState, VoiceParams
from xaudio2py.core.registry import PlaybackRegistry
from xaudio2py.utils.log import get_logger
from xaudio2py.utils.validate import validate_pan, validate_volume

logger = get_logger(__name__)


class PlaybackService:
    """
    Service for managing audio playback operations.
    
    Responsibilities:
    - Start, stop, pause, resume playbacks
    - Control volume and pan
    - Track playback state
    - Manage playback registry
    """
    
    def __init__(
        self,
        worker: IBackendWorker,
        backend,
        registry: Optional[PlaybackRegistry] = None,
    ):
        """
        Initialize playback service.
        
        Args:
            worker: Backend worker for executing commands.
            backend: Audio backend implementation.
            registry: Optional playback registry (creates new if None).
        """
        self._worker = worker
        self._backend = backend
        self._registry = registry or PlaybackRegistry()
    
    def start_playback(
        self,
        sound: Sound,
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
        volume = validate_volume(volume)
        pan = validate_pan(pan)
        
        params = VoiceParams(volume=volume, pan=pan, loop=loop)
        
        # Create voice in worker thread
        voice = self._worker.execute(
            lambda: self._backend.create_source_voice(
                sound.data.format, sound.data.data, params
            )
        )
        
        # Create handle and register playback
        handle_id = str(uuid.uuid4())
        handle = PlaybackHandle(handle_id)
        
        self._registry.register(handle, voice, sound, params)
        
        logger.debug(f"Started playback {handle_id}")
        return handle
    
    def stop_playback(self, handle: PlaybackHandle) -> None:
        """
        Stop playback.
        
        Args:
            handle: Playback handle.
            
        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        playback_info = self._registry.get(handle)
        if playback_info is None:
            raise PlaybackNotFoundError(f"Playback handle not found: {handle.id}")
        
        self._worker.execute(playback_info.voice.stop)
        self._registry.remove(handle)
        logger.debug(f"Stopped playback {handle.id}")
    
    def pause_playback(self, handle: PlaybackHandle) -> None:
        """
        Pause playback.
        
        Args:
            handle: Playback handle.
            
        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        playback_info = self._registry.get(handle)
        if playback_info is None:
            raise PlaybackNotFoundError(f"Playback handle not found: {handle.id}")
        
        self._worker.execute(playback_info.voice.pause)
        logger.debug(f"Paused playback {handle.id}")
    
    def resume_playback(self, handle: PlaybackHandle) -> None:
        """
        Resume playback.
        
        Args:
            handle: Playback handle.
            
        Raises:
            EngineNotStartedError: If engine is not started.
            PlaybackNotFoundError: If handle is invalid.
        """
        playback_info = self._registry.get(handle)
        if playback_info is None:
            raise PlaybackNotFoundError(f"Playback handle not found: {handle.id}")
        
        self._worker.execute(playback_info.voice.resume)
        logger.debug(f"Resumed playback {handle.id}")
    
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
        playback_info = self._registry.get(handle)
        if playback_info is None:
            raise PlaybackNotFoundError(f"Playback handle not found: {handle.id}")
        
        volume = validate_volume(volume)
        self._worker.execute(lambda: playback_info.voice.set_volume(volume))
        playback_info.params.volume = volume
        logger.debug(f"Set volume for playback {handle.id}: {volume}")
    
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
        playback_info = self._registry.get(handle)
        if playback_info is None:
            raise PlaybackNotFoundError(f"Playback handle not found: {handle.id}")
        
        pan = validate_pan(pan)
        self._worker.execute(lambda: playback_info.voice.set_pan(pan))
        playback_info.params.pan = pan
        logger.debug(f"Set pan for playback {handle.id}: {pan}")
    
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
        playback_info = self._registry.get(handle)
        if playback_info is None:
            logger.debug(f"is_playing: handle {handle.id} not found")
            return False
        
        # Get state from voice
        state = self._worker.execute(playback_info.voice.get_state)
        
        elapsed = time.monotonic() - playback_info.start_time
        
        # Check time-based completion for non-looping sounds
        if state == PlaybackState.PLAYING and not playback_info.params.loop:
            if elapsed >= playback_info.sound.duration:
                logger.debug(
                    f"is_playing: playback completed "
                    f"(duration {elapsed:.3f}s >= {playback_info.sound.duration:.3f}s)"
                )
                return False
        
        return state == PlaybackState.PLAYING
    
    def stop_all(self) -> None:
        """
        Stop all active playbacks.
        
        Raises:
            EngineNotStartedError: If engine is not started.
        """
        handles = self._registry.get_all_handles()
        for handle in handles:
            try:
                self.stop_playback(handle)
            except Exception as e:
                logger.warning(f"Error stopping playback {handle.id}: {e}")
    
    @property
    def registry(self) -> PlaybackRegistry:
        """
        Get playback registry.
        
        Returns:
            Playback registry instance.
        """
        return self._registry

