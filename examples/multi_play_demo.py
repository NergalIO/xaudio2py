"""Example: Multiple simultaneous playbacks."""

import sys
import time
from pathlib import Path

from xaudio2py import AudioEngine

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python multi_play_demo.py <path_to_wav_file> [path_to_wav_file2 ...]")
        sys.exit(1)

    wav_paths = sys.argv[1:]

    # Create engine
    engine = AudioEngine()

    try:
        # Start engine
        engine.start()
        print("Engine started")

        # Load all sounds
        sounds = []
        for wav_path in wav_paths:
            if not Path(wav_path).exists():
                print(f"Warning: File not found: {wav_path}, skipping")
                continue
            sound = engine.load_wav(wav_path)
            sounds.append(sound)
            print(f"Loaded: {wav_path} ({sound.duration:.2f}s)")

        if not sounds:
            print("No valid WAV files to play")
            sys.exit(1)

        # Play all sounds with different parameters
        handles = []
        for i, sound in enumerate(sounds):
            volume = 0.5 + (i * 0.2)  # Vary volume
            pan = -1.0 + (i * 0.5)  # Vary pan
            loop = i == 0  # Loop first sound

            handle = engine.play(sound, volume=volume, pan=pan, loop=loop)
            handles.append(handle)
            print(f"Playing sound {i+1}: volume={volume:.1f}, pan={pan:.1f}, loop={loop}")

        # Demonstrate control
        print("\nControls:")
        print("- Press Enter to adjust volume of first sound")
        print("- Press 'p' + Enter to pause/resume first sound")
        print("- Press 'q' + Enter to quit")

        try:
            while True:
                cmd = input().strip().lower()

                if cmd == "q":
                    break
                elif cmd == "p":
                    if handles:
                        if engine.is_playing(handles[0]):
                            engine.pause(handles[0])
                            print("Paused first sound")
                        else:
                            engine.resume(handles[0])
                            print("Resumed first sound")
                elif cmd == "":
                    # Adjust volume
                    if handles:
                        current_vol = 0.5
                        new_vol = 0.8 if current_vol < 0.8 else 0.3
                        engine.set_volume(handles[0], new_vol)
                        print(f"Set volume to {new_vol:.1f}")

                # Check if any non-looping sounds finished
                for i, handle in enumerate(handles):
                    if not engine.is_playing(handle) and i > 0:  # Skip first (looping)
                        print(f"Sound {i+1} finished")

        except KeyboardInterrupt:
            print("\nInterrupted")

        # Stop all playbacks
        print("\nStopping all playbacks...")
        for handle in handles:
            try:
                engine.stop(handle)
            except Exception as e:
                print(f"Error stopping: {e}")

    finally:
        # Shutdown engine
        engine.shutdown()
        print("Engine shut down")

