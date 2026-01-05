"""MP3 file parser and decoder."""

from pathlib import Path
from xaudio2py.core.exceptions import InvalidAudioFormat
from xaudio2py.core.models import AudioFormat, SoundData
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def load_mp3(path: str) -> SoundData:
    """
    Load an MP3 file and convert to PCM SoundData.

    Supports:
    - All MP3 bitrates and sample rates
    - Converts to 16-bit PCM
    - Mono or stereo (preserved from source)
    - Automatic resampling to 44100 or 48000 Hz if needed

    Args:
        path: Path to MP3 file.

    Returns:
        SoundData with format and PCM data.

    Raises:
        InvalidAudioFormat: If format cannot be decoded or converted.
        FileNotFoundError: If file does not exist.
        ImportError: If pydub is not installed.
    """
    if not PYDUB_AVAILABLE:
        raise ImportError(
            "pydub is required for MP3 support. Install it with: pip install pydub"
        )

    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"MP3 file not found: {path}")

    try:
        # Load MP3 using pydub
        audio = AudioSegment.from_mp3(str(path_obj))
        
        # Convert to required format
        # Ensure 16-bit
        if audio.sample_width != 2:  # 2 bytes = 16-bit
            audio = audio.set_sample_width(2)
        
        # Ensure mono or stereo
        if audio.channels not in (1, 2):
            # Convert to stereo if more than 2 channels
            audio = audio.set_channels(2)
            logger.warning(
                f"MP3 has {audio.channels} channels, converting to stereo"
            )
        
        # Resample to supported sample rate (44100 or 48000)
        original_rate = audio.frame_rate
        if original_rate not in (44100, 48000):
            # Choose closest supported rate
            target_rate = 44100 if abs(original_rate - 44100) < abs(original_rate - 48000) else 48000
            logger.info(
                f"Resampling MP3 from {original_rate} Hz to {target_rate} Hz"
            )
            audio = audio.set_frame_rate(target_rate)
            sample_rate = target_rate
        else:
            sample_rate = original_rate
        
        # Get raw PCM data
        raw_audio = audio.raw_data
        
        # Create AudioFormat
        num_channels = audio.channels
        bits_per_sample = audio.sample_width * 8  # sample_width is in bytes
        block_align = num_channels * (bits_per_sample // 8)
        byte_rate = sample_rate * block_align
        
        format = AudioFormat(
            sample_rate=sample_rate,
            channels=num_channels,
            bits_per_sample=bits_per_sample,
            block_align=block_align,
            avg_bytes_per_sec=byte_rate,
        )
        
        # Calculate duration
        duration_seconds = len(audio) / 1000.0  # pydub returns duration in milliseconds
        
        logger.info(
            f"Loaded MP3: {num_channels}ch, {sample_rate}Hz, {bits_per_sample}bit, "
            f"{duration_seconds:.2f}s (original: {original_rate}Hz)"
        )
        
        return SoundData(
            format=format,
            data=raw_audio,
            duration_seconds=duration_seconds,
        )
        
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ImportError)):
            raise
        raise InvalidAudioFormat(f"Failed to decode MP3 file: {e}")

