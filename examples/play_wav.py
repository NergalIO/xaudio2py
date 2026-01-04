"""Example: Play a WAV file."""

import sys
import time
from pathlib import Path

from xaudio2py import AudioEngine

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_wav.py <path_to_wav_file>")
        sys.exit(1)

    wav_path = sys.argv[1]
    if not Path(wav_path).exists():
        print(f"Error: File not found: {wav_path}")
        sys.exit(1)

    # Create engine
    engine = AudioEngine()

    try:
        # Start engine
        engine.start()

        # Load WAV file
        print(f"Loading {wav_path}...")
        sound = engine.load_wav(wav_path)
        print(f"Loaded: {sound.duration:.2f} seconds")

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

