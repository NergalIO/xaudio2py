"""Tests for WAV parser."""

import io
import struct
import pytest
from xaudio2py.core.exceptions import InvalidAudioFormat
from xaudio2py.formats.wav import _parse_wav, wav_format
from xaudio2py.formats import load_audio
from pathlib import Path
import tempfile


def create_test_wav(
    sample_rate: int = 44100,
    channels: int = 2,
    bits_per_sample: int = 16,
    num_samples: int = 1000,
) -> bytes:
    """Create a test WAV file in memory."""
    # Calculate sizes
    block_align = (channels * bits_per_sample) // 8
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align
    file_size = 36 + data_size  # 36 = header + fmt + data header

    wav = io.BytesIO()

    # RIFF header
    wav.write(b"RIFF")
    wav.write(struct.pack("<I", file_size))
    wav.write(b"WAVE")

    # fmt chunk
    wav.write(b"fmt ")
    wav.write(struct.pack("<I", 16))  # fmt chunk size
    wav.write(struct.pack("<H", 1))  # PCM
    wav.write(struct.pack("<H", channels))
    wav.write(struct.pack("<I", sample_rate))
    wav.write(struct.pack("<I", byte_rate))
    wav.write(struct.pack("<H", block_align))
    wav.write(struct.pack("<H", bits_per_sample))

    # data chunk
    wav.write(b"data")
    wav.write(struct.pack("<I", data_size))
    # Write dummy PCM data
    wav.write(b"\x00" * data_size)

    return wav.getvalue()


def test_parse_valid_wav():
    """Test parsing a valid WAV file."""
    wav_data = create_test_wav(sample_rate=44100, channels=2, bits_per_sample=16)
    wav_file = io.BytesIO(wav_data)

    sound_data = _parse_wav(wav_file)

    assert sound_data.format.sample_rate == 44100
    assert sound_data.format.channels == 2
    assert sound_data.format.bits_per_sample == 16
    assert sound_data.format.block_align == 4
    assert len(sound_data.data) > 0


def test_parse_mono_wav():
    """Test parsing a mono WAV file."""
    wav_data = create_test_wav(sample_rate=48000, channels=1, bits_per_sample=16)
    wav_file = io.BytesIO(wav_data)

    sound_data = _parse_wav(wav_file)

    assert sound_data.format.channels == 1
    assert sound_data.format.sample_rate == 48000


def test_parse_invalid_format():
    """Test parsing a WAV with unsupported format."""
    wav_data = create_test_wav()
    # Modify format tag to non-PCM
    wav_data = bytearray(wav_data)
    wav_data[20] = 0xFF  # Change format tag
    wav_file = io.BytesIO(wav_data)

    with pytest.raises(InvalidAudioFormat):
        _parse_wav(wav_file)


def test_parse_unsupported_bits_per_sample():
    """Test parsing a WAV with unsupported bit depth."""
    wav_data = create_test_wav(bits_per_sample=24)
    wav_file = io.BytesIO(wav_data)

    with pytest.raises(InvalidAudioFormat):
        _parse_wav(wav_file)


def test_parse_unsupported_sample_rate():
    """Test parsing a WAV with unsupported sample rate."""
    wav_data = create_test_wav(sample_rate=22050)
    wav_file = io.BytesIO(wav_data)

    with pytest.raises(InvalidAudioFormat):
        _parse_wav(wav_file)


def test_load_wav_from_file():
    """Test loading WAV from file system."""
    wav_data = create_test_wav()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_data)
        temp_path = f.name

    try:
        sound_data = load_audio(temp_path)
        assert sound_data.format.sample_rate == 44100
    finally:
        Path(temp_path).unlink()


def test_load_wav_file_not_found():
    """Test loading non-existent WAV file."""
    with pytest.raises(FileNotFoundError):
        wav_format.load("nonexistent.wav")

