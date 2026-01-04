"""Null backend for testing (no actual audio output)."""

import time
from typing import Dict
from xaudio2py.core.interfaces import IAudioBackend, IVoice
from xaudio2py.core.models import AudioFormat, PlaybackState, SoundData, VoiceParams
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


class NullVoice(IVoice):
    """Null voice implementation for testing."""

    def __init__(self, voice_id: str, format: AudioFormat, data: bytes, params: VoiceParams):
        self.voice_id = voice_id
        self.format = format
        self.data = data
        self.params = params
        self._state = PlaybackState.STOPPED
        self._start_time: float = 0.0
        self._paused_time: float = 0.0
        self._total_played: float = 0.0

    def start(self) -> None:
        """Start playback."""
        if self._state == PlaybackState.PAUSED:
            # Resume from pause
            self._start_time = time.monotonic() - self._total_played
        else:
            self._start_time = time.monotonic()
            self._total_played = 0.0
        self._state = PlaybackState.PLAYING
        logger.debug(f"NullVoice {self.voice_id}: started")

    def stop(self) -> None:
        """Stop playback."""
        if self._state == PlaybackState.PLAYING:
            self._total_played = time.monotonic() - self._start_time
        self._state = PlaybackState.STOPPED
        logger.debug(f"NullVoice {self.voice_id}: stopped")

    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            self._total_played = time.monotonic() - self._start_time
            self._state = PlaybackState.PAUSED
            logger.debug(f"NullVoice {self.voice_id}: paused")

    def resume(self) -> None:
        """Resume playback."""
        if self._state == PlaybackState.PAUSED:
            self._start_time = time.monotonic() - self._total_played
            self._state = PlaybackState.PLAYING
            logger.debug(f"NullVoice {self.voice_id}: resumed")

    def set_volume(self, volume: float) -> None:
        """Set volume."""
        self.params.volume = volume
        logger.debug(f"NullVoice {self.voice_id}: volume={volume}")

    def set_pan(self, pan: float) -> None:
        """Set pan."""
        self.params.pan = pan
        logger.debug(f"NullVoice {self.voice_id}: pan={pan}")

    def get_state(self) -> PlaybackState:
        """Get playback state."""
        if self._state == PlaybackState.PLAYING:
            # Simulate playback completion if not looping
            if not self.params.loop:
                duration = len(self.data) / (self.format.sample_rate * self.format.frame_size)
                elapsed = time.monotonic() - self._start_time
                if elapsed >= duration:
                    self._state = PlaybackState.STOPPED
        return self._state

    def destroy(self) -> None:
        """Destroy voice."""
        logger.debug(f"NullVoice {self.voice_id}: destroyed")


class NullBackend(IAudioBackend):
    """Null backend implementation for testing."""

    def __init__(self):
        self._initialized = False
        self._master_volume = 1.0
        self._voices: Dict[str, NullVoice] = {}
        self._next_voice_id = 0

    def initialize(self) -> None:
        """Initialize backend."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("NullBackend initialized")

    def create_source_voice(
        self, format: AudioFormat, data: bytes, params: VoiceParams
    ) -> IVoice:
        """Create a source voice."""
        voice_id = f"null_{self._next_voice_id}"
        self._next_voice_id += 1
        voice = NullVoice(voice_id, format, data, params)
        self._voices[voice_id] = voice
        logger.debug(f"Created NullVoice {voice_id}")
        return voice

    def set_master_volume(self, volume: float) -> None:
        """Set master volume."""
        self._master_volume = volume
        logger.debug(f"NullBackend: master_volume={volume}")

    def shutdown(self) -> None:
        """Shutdown backend."""
        for voice in self._voices.values():
            voice.destroy()
        self._voices.clear()
        self._initialized = False
        logger.info("NullBackend shut down")

