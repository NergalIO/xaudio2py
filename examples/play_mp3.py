"""Example: Play an MP3 file."""

import sys
import time
from pathlib import Path

from xaudio2py import AudioEngine

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_mp3.py <path_to_mp3_file>")
        sys.exit(1)

    mp3_path = sys.argv[1]
    if not Path(mp3_path).exists():
        print(f"Error: File not found: {mp3_path}")
        sys.exit(1)

    # Create engine
    engine = AudioEngine()

    try:
        # Start engine
        engine.start()

        # Load MP3 file
        print(f"Loading {mp3_path}...")
        try:
            sound = engine.load_mp3(mp3_path)
            print(f"Loaded: {sound.duration:.2f} seconds")
        except ImportError as e:
            print(f"Error: {e}")
            print("Install pydub to enable MP3 support:")
            print("  pip install pydub")
            sys.exit(1)

        # Play sound
        print("Playing...")
        handle = engine.play(sound)

        # Give XAudio2 a moment to initialize playback
        time.sleep(0.05)

        # Wait for playback to complete (or interrupt)
        try:
            while engine.is_playing(handle):
                time.sleep(0.1)
            print("Playback completed")
        except KeyboardInterrupt:
            print("\nInterrupted, stopping...")
            engine.stop(handle)

    finally:
        # Shutdown engine
        engine.shutdown()
        print("Engine shut down")

