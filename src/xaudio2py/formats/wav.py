"""RIFF WAV file parser."""

import struct
from pathlib import Path
from typing import BinaryIO
from xaudio2py.core.exceptions import AudioFormatError, InvalidAudioFormat
from xaudio2py.core.interfaces import IAudioFormat
from xaudio2py.core.models import AudioFormat, SoundData
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


class WavFormat(IAudioFormat):
    """WAV format parser implementing IAudioFormat."""

    @property
    def extensions(self) -> tuple[str, ...]:
        """Supported file extensions."""
        return (".wav", ".wave")

    def can_load(self, path: str) -> bool:
        """Check if file can be loaded as WAV."""
        path_obj = Path(path)
        if not path_obj.exists():
            return False
        
        # Check extension
        if path_obj.suffix.lower() not in self.extensions:
            return False
        
        # Check file header (RIFF WAVE)
        try:
            with open(path_obj, "rb") as f:
                riff = f.read(4)
                if riff != b"RIFF":
                    return False
                f.seek(8)  # Skip file size
                wave = f.read(4)
                return wave == b"WAVE"
        except Exception:
            return False

    def load(self, path: str) -> SoundData:
        """
        Load a WAV file and return SoundData.

        Supports:
        - PCM format (fmt=1)
        - 16-bit samples
        - Mono or stereo
        - 44100 or 48000 Hz sample rate

        Args:
            path: Path to WAV file.

        Returns:
            SoundData with format and PCM data.

        Raises:
            InvalidAudioFormat: If format is not supported.
            FileNotFoundError: If file does not exist.
            IOError: If file cannot be read.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"WAV file not found: {path}")

        with open(path_obj, "rb") as f:
            return _parse_wav(f)


def _parse_wav(f: BinaryIO) -> SoundData:
    """Parse WAV file from file handle."""
    # Read RIFF header
    riff = f.read(4)
    if riff != b"RIFF":
        raise InvalidAudioFormat("Not a RIFF file")

    file_size = struct.unpack("<I", f.read(4))[0]

    wave = f.read(4)
    if wave != b"WAVE":
        raise InvalidAudioFormat("Not a WAVE file")

    # Read chunks
    fmt_data = None
    data_chunk = None

    while True:
        chunk_id = f.read(4)
        if len(chunk_id) < 4:
            break

        chunk_size = struct.unpack("<I", f.read(4))[0]

        if chunk_id == b"fmt ":
            fmt_data = f.read(chunk_size)
        elif chunk_id == b"data":
            data_chunk = f.read(chunk_size)
            break
        else:
            # Skip unknown chunks
            f.seek(chunk_size, 1)

    if fmt_data is None:
        raise InvalidAudioFormat("Missing fmt chunk")

    if data_chunk is None:
        raise InvalidAudioFormat("Missing data chunk")

    # Parse fmt chunk
    # Format: audio_format(2), num_channels(2), sample_rate(4),
    #         byte_rate(4), block_align(2), bits_per_sample(2)
    if len(fmt_data) < 16:
        raise InvalidAudioFormat("Invalid fmt chunk size")

    audio_format = struct.unpack("<H", fmt_data[0:2])[0]
    num_channels = struct.unpack("<H", fmt_data[2:4])[0]
    sample_rate = struct.unpack("<I", fmt_data[4:8])[0]
    byte_rate = struct.unpack("<I", fmt_data[8:12])[0]
    block_align = struct.unpack("<H", fmt_data[12:14])[0]
    bits_per_sample = struct.unpack("<H", fmt_data[14:16])[0]

    # Validate format
    if audio_format != 1:  # PCM
        raise InvalidAudioFormat(
            f"Unsupported audio format: {audio_format} (only PCM=1 is supported)"
        )

    if bits_per_sample != 16:
        raise InvalidAudioFormat(
            f"Unsupported bits per sample: {bits_per_sample} (only 16-bit is supported)"
        )

    if num_channels not in (1, 2):
        raise InvalidAudioFormat(
            f"Unsupported channel count: {num_channels} (only mono=1 or stereo=2)"
        )

    if sample_rate not in (44100, 48000):
        raise InvalidAudioFormat(
            f"Unsupported sample rate: {sample_rate} Hz (only 44100 or 48000 supported)"
        )

    # Create format
    format = AudioFormat(
        sample_rate=sample_rate,
        channels=num_channels,
        bits_per_sample=bits_per_sample,
        block_align=block_align,
        avg_bytes_per_sec=byte_rate,
    )

    # Calculate duration
    num_frames = len(data_chunk) // format.frame_size
    duration_seconds = num_frames / sample_rate

    logger.info(
        f"Loaded WAV: {num_channels}ch, {sample_rate}Hz, {bits_per_sample}bit, "
        f"{duration_seconds:.2f}s"
    )

    return SoundData(
        format=format,
        data=data_chunk,
        duration_seconds=duration_seconds,
    )


# Format instance for automatic registration
wav_format = WavFormat()