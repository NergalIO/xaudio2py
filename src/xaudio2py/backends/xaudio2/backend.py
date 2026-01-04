"""XAudio2 backend implementation."""

import ctypes
from ctypes import POINTER, c_void_p, c_uint32, c_float, byref, cast, pointer, CFUNCTYPE
from typing import Dict, Optional
from xaudio2py.backends.xaudio2.bindings import (
    create_waveformatex,
    XAUDIO2_BUFFER,
    XAUDIO2_END_OF_STREAM,
    XAUDIO2_LOOP_INFINITE,
    XAUDIO2_DEFAULT_PROCESSOR,
)
from xaudio2py.backends.xaudio2.com import COMInitializer, COINIT_MULTITHREADED
from xaudio2py.backends.xaudio2.dll import get_XAudio2Create
from xaudio2py.backends.xaudio2.interfaces import IXAudio2, IXAudio2Vtbl
from xaudio2py.backends.xaudio2.utils import hrcheck
from xaudio2py.backends.xaudio2.voices import SourceVoice, MasteringVoice
from xaudio2py.core.interfaces import IAudioBackend, IVoice
from xaudio2py.core.models import AudioFormat, VoiceParams
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


class XAudio2Backend(IAudioBackend):
    """XAudio2 backend implementation."""

    def __init__(self):
        self._com_initializer: Optional[COMInitializer] = None
        self._xaudio2: Optional[ctypes.POINTER(IXAudio2)] = None
        self._mastering_voice: Optional[MasteringVoice] = None
        self._initialized = False
        self._next_voice_id = 0

    def initialize(self) -> None:
        """Initialize XAudio2 backend (called in worker thread)."""
        if self._initialized:
            return

        # Initialize COM
        self._com_initializer = COMInitializer(COINIT_MULTITHREADED)
        self._com_initializer.__enter__()

        # Get XAudio2Create function
        XAudio2Create = get_XAudio2Create()

        # Create XAudio2 instance
        # XAudio2Create expects a pointer to a pointer (void**)
        # Create a c_void_p variable to hold the returned pointer
        xaudio2_ptr = c_void_p()
        hresult = XAudio2Create(
            byref(xaudio2_ptr),
            0,  # Flags (0 = no debug)
            XAUDIO2_DEFAULT_PROCESSOR,
        )
        hrcheck(hresult, "XAudio2Create failed")

        # Cast to IXAudio2
        # xaudio2_ptr.value contains the pointer address
        self._xaudio2 = cast(xaudio2_ptr.value, POINTER(IXAudio2))

        # Start engine
        # Get function pointer from vtable and convert to callable function
        StartEngineFunc = CFUNCTYPE(c_uint32, c_void_p)
        start_engine_ptr = self._xaudio2.contents.lpVtbl.contents.StartEngine
        start_engine_func = cast(start_engine_ptr, StartEngineFunc)

        hresult = start_engine_func(cast(self._xaudio2, c_void_p))
        hrcheck(hresult, "StartEngine failed")

        # Create mastering voice
        # Get function pointer from vtable and convert to callable function
        CreateMasteringVoiceFunc = CFUNCTYPE(
            c_uint32,
            c_void_p,  # this
            POINTER(c_void_p),  # ppMasteringVoice
            c_uint32,  # InputChannels
            c_uint32,  # InputSampleRate
            c_uint32,  # Flags
            c_void_p,  # szDeviceId
            c_void_p,  # pEffectChain
            c_uint32,  # StreamCategory
        )
        create_mastering_voice_ptr = (
            self._xaudio2.contents.lpVtbl.contents.CreateMasteringVoice
        )
        create_mastering_voice_func = cast(
            create_mastering_voice_ptr, CreateMasteringVoiceFunc
        )

        mastering_voice_ptr = c_void_p()
        hresult = create_mastering_voice_func(
            cast(self._xaudio2, c_void_p),
            byref(mastering_voice_ptr),
            0,  # InputChannels (default)
            0,  # InputSampleRate (default)
            0,  # Flags
            None,  # DeviceId
            None,  # EffectChain
            0,  # StreamCategory
        )
        hrcheck(hresult, "CreateMasteringVoice failed")

        self._mastering_voice = MasteringVoice(mastering_voice_ptr)
        self._initialized = True
        logger.info("XAudio2Backend initialized")

    def create_source_voice(
        self, format: AudioFormat, data: bytes, params: VoiceParams
    ) -> IVoice:
        """Create a source voice for playback."""
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        # Create WAVEFORMATEX
        wave_format = create_waveformatex(
            format.sample_rate, format.channels, format.bits_per_sample
        )

        # Get CreateSourceVoice function
        from xaudio2py.backends.xaudio2.bindings import WAVEFORMATEX
        CreateSourceVoiceFunc = CFUNCTYPE(
            c_uint32,
            c_void_p,  # this
            POINTER(c_void_p),  # ppSourceVoice
            POINTER(WAVEFORMATEX),  # pSourceFormat
            c_uint32,  # Flags
            c_float,  # MaxFrequencyRatio
            c_void_p,  # pCallback
            c_void_p,  # pSendList
            c_void_p,  # pEffectChain
        )
        create_source_voice_ptr = (
            self._xaudio2.contents.lpVtbl.contents.CreateSourceVoice
        )
        create_source_voice_func = cast(create_source_voice_ptr, CreateSourceVoiceFunc)

        # Create source voice
        source_voice_ptr = c_void_p()
        hresult = create_source_voice_func(
            cast(self._xaudio2, c_void_p),
            byref(source_voice_ptr),
            byref(wave_format),
            0,  # Flags
            2.0,  # MaxFrequencyRatio
            None,  # Callback
            None,  # SendList
            None,  # EffectChain
        )
        hrcheck(hresult, "CreateSourceVoice failed")
        
        # Validate that pointer was actually set
        if not source_voice_ptr or not source_voice_ptr.value:
            from xaudio2py.core.exceptions import XAudio2Error
            raise XAudio2Error(-1, "CreateSourceVoice returned NULL voice pointer")
        
        logger.debug(f"CreateSourceVoice succeeded: voice_ptr=0x{source_voice_ptr.value:X}")

        voice = SourceVoice(source_voice_ptr, format.channels)

        # Set initial volume and pan
        voice.set_volume(params.volume)
        voice.set_pan(params.pan)

        # Submit buffer - need to keep data alive
        # Create array that will be kept alive - MUST be stored BEFORE submission
        audio_array = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        
        # Store reference in voice FIRST to ensure GC doesn't collect it
        voice._audio_data = audio_array
        
        buffer = XAUDIO2_BUFFER()
        # For MVP, use Flags = 0 (safest option)
        # END_OF_STREAM is optional and can be added later if needed
        buffer.Flags = 0
        buffer.AudioBytes = len(data)
        
        # Validate AudioBytes is multiple of block align
        # nBlockAlign = (channels * bits_per_sample) // 8
        n_block_align = (format.channels * format.bits_per_sample) // 8
        if buffer.AudioBytes % n_block_align != 0:
            from xaudio2py.core.exceptions import InvalidAudioFormat
            raise InvalidAudioFormat(
                f"AudioBytes ({buffer.AudioBytes}) must be multiple of nBlockAlign ({n_block_align})"
            )
        
        buffer.pAudioData = ctypes.cast(audio_array, POINTER(ctypes.c_uint8))
        buffer.PlayBegin = 0
        buffer.PlayLength = 0  # Play entire buffer
        buffer.LoopBegin = 0
        buffer.LoopLength = 0
        buffer.LoopCount = XAUDIO2_LOOP_INFINITE if params.loop else 0
        buffer.pContext = None
        
        # Diagnostic logging
        pAudioData_addr = ctypes.addressof(audio_array) if audio_array else 0
        voice_ptr_addr = voice._voice_ptr.value if voice._voice_ptr and voice._voice_ptr.value else 0
        logger.info(
            f"Preparing buffer: AudioBytes={buffer.AudioBytes}, "
            f"pAudioData=0x{pAudioData_addr:X}, "
            f"voice_ptr=0x{voice_ptr_addr:X}, "
            f"Flags=0x{buffer.Flags:X}, LoopCount={buffer.LoopCount}"
        )

        # Submit buffer using voice method
        voice.submit_buffer(buffer)
        
        # Start playback immediately after submitting buffer
        # This ensures the voice starts playing the submitted buffer
        voice.start()

        logger.debug("Created XAudio2 SourceVoice and started playback")
        return voice

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        if not self._initialized or self._mastering_voice is None:
            raise RuntimeError("Backend not initialized")
        self._mastering_voice.set_volume(volume)

    def shutdown(self) -> None:
        """Shutdown the backend and free all resources."""
        if not self._initialized:
            return

        logger.info("Shutting down XAudio2Backend...")

        # Destroy mastering voice
        if self._mastering_voice is not None:
            self._mastering_voice.destroy()
            self._mastering_voice = None

        # Release XAudio2
        if self._xaudio2 is not None:
            ReleaseFunc = CFUNCTYPE(c_uint32, c_void_p)
            release_ptr = self._xaudio2.contents.lpVtbl.contents.Release
            release_func = cast(release_ptr, ReleaseFunc)

            release_func(cast(self._xaudio2, c_void_p))
            self._xaudio2 = None

        # Uninitialize COM
        if self._com_initializer is not None:
            self._com_initializer.__exit__(None, None, None)
            self._com_initializer = None

        self._initialized = False
        logger.info("XAudio2Backend shut down")

