"""Audio format parsers."""

from xaudio2py.formats.wav import load_wav
from xaudio2py.formats.mp3 import load_mp3

__all__ = ["load_wav", "load_mp3"]

