"""Playback registry for tracking active playbacks."""

import time
from dataclasses import dataclass
from typing import Dict, Optional
from xaudio2py.api.sound import PlaybackHandle, Sound
from xaudio2py.core.interfaces import IVoice
from xaudio2py.core.models import PlaybackState, VoiceParams


@dataclass
class PlaybackInfo:
    """Information about an active playback."""
    
    handle: PlaybackHandle
    voice: IVoice
    sound: Sound
    params: VoiceParams
    start_time: float


class PlaybackRegistry:
    """
    Registry for managing active audio playbacks.
    
    Responsibilities:
    - Store and retrieve playback information
    - Track playback lifecycle
    - Provide thread-safe access to playback data
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._playbacks: Dict[str, PlaybackInfo] = {}
    
    def register(
        self,
        handle: PlaybackHandle,
        voice: IVoice,
        sound: Sound,
        params: VoiceParams,
    ) -> None:
        """
        Register a new playback.
        
        Args:
            handle: Playback handle.
            voice: Voice instance.
            sound: Sound being played.
            params: Voice parameters.
        """
        playback_info = PlaybackInfo(
            handle=handle,
            voice=voice,
            sound=sound,
            params=params,
            start_time=time.monotonic(),
        )
        self._playbacks[handle.id] = playback_info
    
    def get(self, handle: PlaybackHandle) -> Optional[PlaybackInfo]:
        """
        Get playback information.
        
        Args:
            handle: Playback handle.
            
        Returns:
            PlaybackInfo if found, None otherwise.
        """
        return self._playbacks.get(handle.id)
    
    def remove(self, handle: PlaybackHandle) -> None:
        """
        Remove playback from registry.
        
        Args:
            handle: Playback handle.
        """
        self._playbacks.pop(handle.id, None)
    
    def get_all_handles(self) -> list[PlaybackHandle]:
        """
        Get all active playback handles.
        
        Returns:
            List of all active handles.
        """
        return [info.handle for info in self._playbacks.values()]
    
    def clear(self) -> None:
        """Clear all playbacks from registry."""
        self._playbacks.clear()
    
    def count(self) -> int:
        """
        Get number of active playbacks.
        
        Returns:
            Number of active playbacks.
        """
        return len(self._playbacks)

