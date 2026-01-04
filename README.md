# xaudio2py

Python wrapper for XAudio2 using ctypes. Provides a high-level API for audio playback on Windows with support for WAV files, multiple simultaneous playbacks, volume control, panning, and looping.

## Requirements

- Python 3.11+
- Windows 10/11
- XAudio2 DLL (see installation section)

## Installation

1. Clone or download this repository.

2. Install the package:
```bash
pip install -e .
```

3. Ensure `xaudio2_9redist.dll` is available:
   - Place `xaudio2_9redist.dll` in the `bin/` directory of the project
   - Or place it in the same directory as your Python script
   - Or ensure it's in your system PATH

### Как проверить наличие xaudio2_9redist.dll

Вы можете проверить наличие DLL следующими способами:

1. **Проверка в bin/ директории:**
```bash
dir bin\xaudio2_9redist.dll
```

2. **Проверка через Python:**
```python
from pathlib import Path
dll_path = Path("bin/xaudio2_9redist.dll")
if dll_path.exists():
    print(f"DLL found at: {dll_path.absolute()}")
else:
    print("DLL not found in bin/")
```

3. **Проверка в системных директориях:**
```bash
dir C:\Windows\System32\xaudio2_9redist.dll
dir C:\Windows\SysWOW64\xaudio2_9redist.dll
```

4. **Использование dumpbin (если установлен Visual Studio):**
```bash
dumpbin /exports bin\xaudio2_9redist.dll
```

DLL loader автоматически ищет DLL в следующем порядке:
1. Текущая директория
2. `bin/` директория проекта
3. Директория Python
4. `C:\Windows\System32`
5. `C:\Windows\SysWOW64`
6. Системный PATH

Если `xaudio2_9redist.dll` не найден, будет предпринята попытка загрузить `xaudio2_9.dll`, `xaudio2_8.dll`, или `xaudio2_7.dll` в указанном порядке.

## Quick Start

```python
from xaudio2py import AudioEngine

# Create and start engine
engine = AudioEngine()
engine.start()

# Load a WAV file
sound = engine.load_wav("music.wav")

# Play the sound
handle = engine.play(sound)

# Control playback
engine.pause(handle)
engine.resume(handle)
engine.set_volume(handle, 0.5)
engine.set_pan(handle, -0.5)  # Pan left

# Stop playback
engine.stop(handle)

# Shutdown
engine.shutdown()
```

Or use as a context manager:

```python
with AudioEngine() as engine:
    sound = engine.load_wav("music.wav")
    handle = engine.play(sound, loop=True)
    # ... do something ...
```

## API Reference

### AudioEngine

Main facade class for audio operations.

#### Methods

- `start()` - Start the audio engine (must be called before playing sounds)
- `shutdown()` - Shutdown the engine and free all resources
- `load_wav(path: str) -> Sound` - Load a WAV file
- `play(sound: Sound, *, volume=1.0, pan=0.0, loop=False) -> PlaybackHandle` - Start playback
- `stop(handle: PlaybackHandle)` - Stop playback
- `pause(handle: PlaybackHandle)` - Pause playback
- `resume(handle: PlaybackHandle)` - Resume playback
- `set_volume(handle: PlaybackHandle, volume: float)` - Set volume (0.0 to 1.0)
- `set_pan(handle: PlaybackHandle, pan: float)` - Set pan (-1.0 left, 0.0 center, 1.0 right)
- `set_master_volume(volume: float)` - Set master volume (0.0 to 1.0)
- `is_playing(handle: PlaybackHandle) -> bool` - Check if playback is active

### Sound

Represents a loaded audio file.

#### Properties

- `data: SoundData` - Audio data and format
- `path: str` - Source file path
- `duration: float` - Duration in seconds

### PlaybackHandle

Handle for controlling a playback instance.

## Supported Audio Formats

Currently supported WAV formats:
- **Format**: PCM (fmt=1)
- **Bit depth**: 16-bit
- **Channels**: Mono (1) or Stereo (2)
- **Sample rates**: 44100 Hz or 48000 Hz

Other formats will raise `InvalidAudioFormat` with a descriptive error message.

## Architecture

### SOLID Principles

The project follows SOLID principles:

#### Single Responsibility Principle (SRP)
- **WAV parser** (`formats/wav.py`) - Only responsible for parsing WAV files
- **Backend** (`backends/`) - Only responsible for XAudio2 operations
- **Engine** (`api/engine.py`) - Only responsible for high-level API and coordination
- **Worker thread** (`core/thread.py`) - Only responsible for command dispatch

#### Open/Closed Principle (OCP)
- **IAudioBackend protocol** allows replacing the backend implementation without modifying core code
- New backends can be added by implementing the `IAudioBackend` interface
- Example: `NullBackend` for testing, `XAudio2Backend` for production

#### Liskov Substitution Principle (LSP)
- All backend implementations are interchangeable through the `IAudioBackend` protocol
- `NullBackend` and `XAudio2Backend` can be used interchangeably

#### Interface Segregation Principle (ISP)
- Small, focused protocols: `IAudioBackend`, `IVoice`, `IBackendWorker`
- No "god interfaces" - each interface has a specific purpose

#### Dependency Inversion Principle (DIP)
- `AudioEngine` depends on `IAudioBackend` protocol, not concrete implementations
- Core modules depend on abstractions (Protocols, models), not ctypes/XAudio2 directly

### Thread Safety

**Почему выбран worker thread:**

1. **COM Requirements**: XAudio2 is a COM-based API. COM requires that all calls to a COM object are made from the same thread where it was created (apartment threading model). By using a dedicated worker thread with `COINIT_MULTITHREADED`, we ensure all XAudio2 operations happen in one thread.

2. **Thread Safety**: The public API (`AudioEngine` methods) is thread-safe and can be called from any thread. Commands are queued and executed in the worker thread, preventing race conditions.

3. **Blocking Operations**: Some XAudio2 operations may block. Isolating them in a worker thread prevents blocking the main application thread.

4. **Resource Management**: Centralized resource management in one thread simplifies cleanup and prevents resource leaks.

All public API methods are thread-safe. Commands to the backend are executed asynchronously in a worker thread via a queue-based system.

### Backend Abstraction

The backend is abstracted through the `IAudioBackend` protocol:

```python
class IAudioBackend(Protocol):
    def initialize(self) -> None: ...
    def create_source_voice(...) -> IVoice: ...
    def set_master_volume(self, volume: float) -> None: ...
    def shutdown(self) -> None: ...
```

This allows:
- Testing with `NullBackend` (no actual audio output)
- Future support for other backends (e.g., DirectSound, WASAPI)
- Easy mocking in unit tests

## Limitations

### Playback State Detection

**Current Implementation (Polling-based):**

The MVP uses a polling-based approach for detecting playback completion:

- `is_playing()` checks voice state and elapsed time
- For non-looping sounds, completion is detected by comparing elapsed time to sound duration
- For looping sounds, `is_playing()` returns `True` until explicitly stopped

**Why not callbacks:**

XAudio2 supports callbacks through `IXAudio2VoiceCallback`, but implementing this in MVP would require:
- Creating a Python callback function
- Managing callback lifetime and thread safety
- More complex COM interop

This is marked as a TODO for future enhancement.

**Workaround:**

For applications that need event-driven completion detection, you can:
1. Poll `is_playing()` in a loop
2. Use threading to monitor playback state
3. Calculate expected completion time and schedule actions

### Pan Implementation

Panning is implemented using `SetOutputMatrix` for stereo output:
- Simple left/right balance
- For mono sources: pan affects both output channels
- For stereo sources: pan adjusts the balance between left and right channels

More advanced panning (e.g., HRTF, 3D positioning) is not implemented in MVP.

### Format Support

Only WAV PCM 16-bit mono/stereo at 44100/48000 Hz is supported. Other formats will raise `InvalidAudioFormat`.

## Examples

See the `examples/` directory:

- `play_wav.py` - Basic playback example
- `multi_play_demo.py` - Multiple simultaneous playbacks with controls

## Testing

Run tests with pytest:

```bash
pytest tests/
```

Tests use `NullBackend` to avoid requiring XAudio2 DLL and actual audio hardware.

## Error Handling

The library raises specific exceptions:

- `XAudio2Error(hresult, message)` - XAudio2/COM errors
- `InvalidAudioFormat` - Unsupported audio format
- `EngineNotStarted` - Operations attempted before `start()`
- `PlaybackNotFound` - Invalid playback handle

All HRESULT values are checked, and failures (< 0) raise `XAudio2Error`.

## Logging

The library uses Python's `logging` module. Set log level to see debug information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Project Structure

```
repo/
  pyproject.toml
  README.md
  src/
    xaudio2py/
      __init__.py
      api/              # Public API
        engine.py
        sound.py
      core/             # Core abstractions
        interfaces.py
        models.py
        exceptions.py
        thread.py
      formats/          # Format parsers
        wav.py
      backends/         # Backend implementations
        null_backend.py
        xaudio2/
          dll.py
          bindings.py
          com.py
          interfaces.py
          backend.py
          voices.py
          utils.py
      utils/
        log.py
        validate.py
  tests/
  examples/
```

### Adding a New Backend

1. Implement `IAudioBackend` protocol
2. Implement `IVoice` for voice control
3. Register in `AudioEngine.__init__` (or use dependency injection)

### Adding Format Support

1. Create parser in `formats/`
2. Return `SoundData` with `AudioFormat`
3. Update `AudioEngine.load_*` methods

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Code follows SOLID principles
- All tests pass
- New features include tests
- Documentation is updated

