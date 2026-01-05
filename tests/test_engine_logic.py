"""Tests for engine logic (using NullBackend)."""

import pytest
from xaudio2py.api.engine import AudioEngine
from xaudio2py.api.sound import Sound
from xaudio2py.backends.null_backend import NullBackend
from xaudio2py.core.exceptions import EngineNotStarted, PlaybackNotFound
from xaudio2py.core.models import EngineConfig, SoundData, AudioFormat, PlaybackState
import time


def create_test_sound() -> Sound:
    """Create a test sound."""
    format = AudioFormat(
        sample_rate=44100,
        channels=2,
        bits_per_sample=16,
        block_align=4,
        avg_bytes_per_sec=176400,
    )
    data = SoundData(
        format=format,
        data=b"\x00" * 10000,  # Dummy PCM data
        duration_seconds=0.1,
    )
    return Sound(data, "test.wav")


def test_engine_start_shutdown():
    """Test engine start and shutdown."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)

    engine.start()
    assert engine._lifecycle_service.is_started

    engine.shutdown()
    assert not engine._lifecycle_service.is_started


def test_engine_context_manager():
    """Test engine as context manager."""
    backend = NullBackend()
    with AudioEngine(backend=backend) as engine:
        assert engine._lifecycle_service.is_started
    assert not engine._lifecycle_service.is_started


def test_play_before_start():
    """Test that play raises error if engine not started."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    sound = create_test_sound()

    with pytest.raises(EngineNotStarted):
        engine.play(sound)


def test_play_stop():
    """Test basic play and stop."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound)

    # Check that playback is registered
    assert engine._playback_service.registry.get(handle) is not None

    engine.stop(handle)
    # Check that playback is removed
    assert engine._playback_service.registry.get(handle) is None


def test_play_pause_resume():
    """Test play, pause, and resume."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound)

    engine.pause(handle)
    # State should be paused (checked via voice)

    engine.resume(handle)
    # Should not raise

    engine.stop(handle)


def test_set_volume():
    """Test setting volume."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound, volume=0.5)

    engine.set_volume(handle, 0.75)
    # Should not raise

    engine.stop(handle)


def test_set_pan():
    """Test setting pan."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound, pan=-0.5)

    engine.set_pan(handle, 0.5)
    # Should not raise

    engine.stop(handle)


def test_set_master_volume():
    """Test setting master volume."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    engine.set_master_volume(0.5)
    # Should not raise


def test_play_with_loop():
    """Test playing with loop enabled."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound, loop=True)

    # Should not raise
    engine.stop(handle)


def test_invalid_handle():
    """Test operations with invalid handle."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    from xaudio2py.api.sound import PlaybackHandle
    invalid_handle = PlaybackHandle("invalid")

    with pytest.raises(PlaybackNotFound):
        engine.stop(invalid_handle)

    with pytest.raises(PlaybackNotFound):
        engine.pause(invalid_handle)

    with pytest.raises(PlaybackNotFound):
        engine.set_volume(invalid_handle, 0.5)


def test_is_playing():
    """Test is_playing check."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound)

    # Should be playing initially
    assert engine.is_playing(handle)

    engine.stop(handle)
    assert not engine.is_playing(handle)


def test_volume_validation():
    """Test volume validation (clamping)."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound, volume=2.0)  # Should be clamped to 1.0

    engine.set_volume(handle, -1.0)  # Should be clamped to 0.0
    engine.stop(handle)


def test_pan_validation():
    """Test pan validation (clamping)."""
    backend = NullBackend()
    engine = AudioEngine(backend=backend)
    engine.start()

    sound = create_test_sound()
    handle = engine.play(sound, pan=2.0)  # Should be clamped to 1.0

    engine.set_pan(handle, -2.0)  # Should be clamped to -1.0
    engine.stop(handle)
