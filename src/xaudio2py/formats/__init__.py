"""Audio format parsers with automatic registration."""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Optional
from xaudio2py.core.exceptions import AudioFormatError, InvalidAudioFormat
from xaudio2py.core.interfaces import IAudioFormat
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)

# Registry of all available formats
_format_registry: Dict[str, IAudioFormat] = {}


def _register_format(format: IAudioFormat) -> None:
    """
    Register an audio format.
    
    Args:
        format: Format instance implementing IAudioFormat.
    """
    for ext in format.extensions:
        ext_lower = ext.lower()
        if ext_lower in _format_registry:
            logger.warning(
                f"Format with extension {ext_lower} already registered, "
                f"overwriting with {type(format).__name__}"
            )
        _format_registry[ext_lower] = format
    logger.debug(f"Registered format {type(format).__name__} for extensions: {format.extensions}")


def _auto_discover_formats() -> None:
    """Automatically discover and register all format implementations in this package."""
    # Try to discover additional formats in this package
    package_path = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_path)]):
        module_name = module_info.name
        # Skip __init__
        if module_name == "__init__":
            continue
        
        try:
            module = importlib.import_module(f"xaudio2py.formats.{module_name}")
            # Look for format instances (variables ending with _format)
            for attr_name in dir(module):
                if attr_name.endswith("_format") and not attr_name.startswith("_"):
                    try:
                        attr = getattr(module, attr_name)
                        if isinstance(attr, IAudioFormat):
                            _register_format(attr)
                            logger.info(f"Auto-discovered format from {module_name}: {type(attr).__name__}")
                    except Exception as e:
                        logger.debug(f"Could not register format {attr_name} from {module_name}: {e}")
        except Exception as e:
            logger.debug(f"Could not load format module {module_name}: {e}")


def get_format_for_file(path: str) -> Optional[IAudioFormat]:
    """
    Get the appropriate format handler for a file.
    
    Args:
        path: Path to audio file.
        
    Returns:
        IAudioFormat instance if a suitable format is found, None otherwise.
    """
    if not _format_registry:
        _auto_discover_formats()
    
    path_obj = Path(path)
    ext = path_obj.suffix.lower()
    
    # First try by extension
    if ext in _format_registry:
        format = _format_registry[ext]
        if format.can_load(path):
            return format
    
    # If extension-based lookup fails, try all formats
    for format in _format_registry.values():
        if format.can_load(path):
            return format
    
    return None


def load_audio(path: str):
    """
    Automatically detect and load an audio file.
    
    Args:
        path: Path to audio file.
        
    Returns:
        SoundData with format and PCM data.
        
    Raises:
        AudioFormatError: If no suitable format is found.
        FileNotFoundError: If file does not exist.
    """
    format = get_format_for_file(path)
    if format is None:
        raise AudioFormatError(
            f"No suitable format handler found for file: {path}. "
            f"Supported extensions: {', '.join(sorted(set(ext for fmt in _format_registry.values() for ext in fmt.extensions)))}"
        )
    
    return format.load(path)


# Initialize registry on import
# Auto-discovery should find and register all formats
_auto_discover_formats()

# If registry is still empty after auto-discovery, explicitly try to import known formats
# This handles edge cases where pkgutil.iter_modules might not work correctly
if not _format_registry:
    try:
        from xaudio2py.formats import wav
        if hasattr(wav, 'wav_format'):
            _register_format(wav.wav_format)
    except ImportError:
        pass
    
    try:
        from xaudio2py.formats import mp3
        if hasattr(mp3, 'mp3_format'):
            _register_format(mp3.mp3_format)
    except ImportError:
        pass  # mp3 may not be available if pydub is missing

__all__ = ["load_audio", "get_format_for_file", "IAudioFormat"]

