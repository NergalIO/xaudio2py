"""Voice wrappers for XAudio2."""

import ctypes
from ctypes import POINTER, c_void_p, c_uint32, c_float, byref, cast, CFUNCTYPE
from xaudio2py.backends.xaudio2.bindings import (
    XAUDIO2_BUFFER,
    XAUDIO2_VOICE_STATE,
    XAUDIO2_END_OF_STREAM,
    XAUDIO2_LOOP_INFINITE,
)
from xaudio2py.backends.xaudio2.interfaces import (
    IXAudio2SourceVoice,
    IXAudio2Voice,
    IXAudio2SourceVoiceVtbl,
    IXAudio2VoiceVtbl,
)
from xaudio2py.backends.xaudio2.utils import hrcheck, pan_to_matrix
from xaudio2py.core.interfaces import IVoice
from xaudio2py.core.models import PlaybackState
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


class SourceVoice(IVoice):
    """Wrapper for IXAudio2SourceVoice."""

    def __init__(self, voice_ptr: c_void_p, format_channels: int):
        """
        Initialize SourceVoice wrapper.

        Args:
            voice_ptr: Pointer to IXAudio2SourceVoice COM object.
            format_channels: Number of channels in source format.
        """
        self._voice_ptr = voice_ptr
        self._format_channels = format_channels
        self._voice = cast(voice_ptr, POINTER(IXAudio2SourceVoice)).contents
        self._base_voice = cast(voice_ptr, POINTER(IXAudio2Voice)).contents
        self._state = PlaybackState.STOPPED
        self._buffer_submitted = False
        self._audio_data = None  # Keep reference to audio data

    def start(self) -> None:
        """Start playback."""
        # Get Start function from vtable
        StartFunc = CFUNCTYPE(c_uint32, c_void_p, c_uint32, c_uint32)
        start_ptr = self._voice.lpVtbl.contents.Start
        if not start_ptr:
            from xaudio2py.core.exceptions import XAudio2Error
            raise XAudio2Error(-1, "Start vtable entry is NULL")
        
        start_func = cast(start_ptr, StartFunc)

        # Check buffer status before starting
        if not self._buffer_submitted:
            logger.warning("Starting voice without submitted buffer!")
        else:
            logger.info("Starting voice with submitted buffer")
        
        hresult = start_func(self._voice_ptr, 0, 0)  # Flags, OperationSet
        hrcheck(hresult, "Start failed")
        self._state = PlaybackState.PLAYING
        logger.info(f"SourceVoice: started successfully (voice_ptr=0x{self._voice_ptr.value:X})")
        
        # Verify state immediately after start
        from xaudio2py.backends.xaudio2.bindings import XAUDIO2_VOICE_STATE
        temp_state = XAUDIO2_VOICE_STATE()
        GetStateFunc = CFUNCTYPE(c_uint32, c_void_p, POINTER(XAUDIO2_VOICE_STATE), c_uint32)
        get_state_ptr = self._voice.lpVtbl.contents.GetState
        if get_state_ptr:
            get_state_func = cast(get_state_ptr, GetStateFunc)
            hr = get_state_func(self._voice_ptr, byref(temp_state), 0)
            if hr >= 0:
                logger.info(f"Voice state immediately after start: BuffersQueued={temp_state.BuffersQueued}, SamplesPlayed={temp_state.SamplesPlayed}")
            else:
                from xaudio2py.backends.xaudio2.utils import hr_to_hex
                logger.warning(f"GetState failed immediately after start: HRESULT {hr_to_hex(hr)}")

    def stop(self) -> None:
        """Stop playback and flush buffers."""
        # Get Stop function
        StopFunc = CFUNCTYPE(c_uint32, c_void_p, c_uint32, c_uint32)
        stop_ptr = self._voice.lpVtbl.contents.Stop
        stop_func = cast(stop_ptr, StopFunc)

        hresult = stop_func(self._voice_ptr, 0, 0)  # Flags, OperationSet
        hrcheck(hresult, "Stop failed")

        # Flush buffers
        FlushFunc = CFUNCTYPE(c_uint32, c_void_p)
        flush_ptr = self._voice.lpVtbl.contents.FlushSourceBuffers
        flush_func = cast(flush_ptr, FlushFunc)

        hresult = flush_func(self._voice_ptr)
        hrcheck(hresult, "FlushSourceBuffers failed")

        self._state = PlaybackState.STOPPED
        self._buffer_submitted = False
        logger.debug("SourceVoice: stopped")

    def submit_buffer(self, buffer) -> None:
        """Submit audio buffer for playback."""
        from xaudio2py.backends.xaudio2.bindings import XAUDIO2_BUFFER
        from xaudio2py.core.exceptions import XAudio2Error
        from ctypes import byref, sizeof
        
        # Validate voice pointer
        if not self._voice_ptr or not self._voice_ptr.value:
            raise XAudio2Error(-1, "Voice pointer is NULL in submit_buffer")
        
        # Diagnostic logging
        # Get address of pAudioData pointer
        pAudioData_addr = cast(buffer.pAudioData, c_void_p).value if buffer.pAudioData else 0
        logger.debug(
            f"submit_buffer: voice_ptr=0x{self._voice_ptr.value:X}, "
            f"AudioBytes={buffer.AudioBytes}, "
            f"pAudioData=0x{pAudioData_addr:X}, "
            f"buffer_size={sizeof(buffer)}"
        )
        
        # Get SubmitSourceBuffer function from vtable
        # SubmitSourceBuffer is at index 20 (after 18 base methods + Start + Stop)
        SubmitSourceBufferFunc = CFUNCTYPE(
            c_uint32,  # HRESULT
            c_void_p,  # this (IXAudio2SourceVoice*)
            POINTER(XAUDIO2_BUFFER),  # pBuffer
            c_void_p  # pBufferWMA (usually NULL)
        )
        
        # Access vtable entry - this must be at the correct offset
        vtable = self._voice.lpVtbl.contents
        if not vtable:
            raise XAudio2Error(-1, "VTable pointer is NULL")
        
        submit_buffer_ptr = vtable.SubmitSourceBuffer
        if not submit_buffer_ptr or submit_buffer_ptr == 0xFFFFFFFFFFFFFFFF:
            raise XAudio2Error(-1, f"SubmitSourceBuffer vtable entry is invalid: 0x{submit_buffer_ptr:X}")
        
        submit_buffer_func = cast(submit_buffer_ptr, SubmitSourceBufferFunc)

        # Call the method - must pass voice pointer as 'this'
        logger.info(f"Calling SubmitSourceBuffer: voice_ptr=0x{self._voice_ptr.value:X}, AudioBytes={buffer.AudioBytes}")
        hresult = submit_buffer_func(self._voice_ptr, byref(buffer), None)
        hrcheck(hresult, "SubmitSourceBuffer failed")
        self._buffer_submitted = True
        from xaudio2py.backends.xaudio2.utils import hr_to_hex
        logger.info(f"SubmitSourceBuffer succeeded with HRESULT {hr_to_hex(hresult)}")
        
        # Verify buffer was queued
        from xaudio2py.backends.xaudio2.bindings import XAUDIO2_VOICE_STATE
        check_state = XAUDIO2_VOICE_STATE()
        GetStateFunc = CFUNCTYPE(c_uint32, c_void_p, POINTER(XAUDIO2_VOICE_STATE), c_uint32)
        get_state_ptr = self._voice.lpVtbl.contents.GetState
        if get_state_ptr:
            get_state_func = cast(get_state_ptr, GetStateFunc)
            hr = get_state_func(self._voice_ptr, byref(check_state), 0)
            if hr >= 0:
                logger.info(f"Buffer state after submit: BuffersQueued={check_state.BuffersQueued}, SamplesPlayed={check_state.SamplesPlayed}")
            else:
                from xaudio2py.backends.xaudio2.utils import hr_to_hex
                logger.warning(f"GetState failed after submit: HRESULT {hr_to_hex(hr)}")

    def pause(self) -> None:
        """Pause playback."""
        # Pause is just Stop without flush
        StopFunc = CFUNCTYPE(c_uint32, c_void_p, c_uint32, c_uint32)
        stop_ptr = self._voice.lpVtbl.contents.Stop
        stop_func = cast(stop_ptr, StopFunc)

        hresult = stop_func(self._voice_ptr, 0, 0)
        hrcheck(hresult, "Pause (Stop) failed")
        self._state = PlaybackState.PAUSED
        logger.debug("SourceVoice: paused")

    def resume(self) -> None:
        """Resume playback."""
        self.start()
        logger.debug("SourceVoice: resumed")

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        # Clamp volume
        volume = max(0.0, min(1.0, volume))

        # Get SetVolume function from base voice vtable
        SetVolumeFunc = CFUNCTYPE(c_uint32, c_void_p, c_float, c_uint32)
        set_volume_ptr = self._base_voice.lpVtbl.contents.SetVolume
        set_volume_func = cast(set_volume_ptr, SetVolumeFunc)

        hresult = set_volume_func(self._voice_ptr, c_float(volume), 0)  # OperationSet
        hrcheck(hresult, "SetVolume failed")
        logger.debug(f"SourceVoice: volume={volume}")

    def set_pan(self, pan: float) -> None:
        """Set pan (-1.0 left, 0.0 center, 1.0 right)."""
        # Get SetOutputMatrix function
        SetOutputMatrixFunc = CFUNCTYPE(
            c_uint32,
            c_void_p,  # this
            c_void_p,  # pDestinationVoice
            c_uint32,  # SourceChannels
            c_uint32,  # DestinationChannels
            POINTER(c_float),  # pLevelMatrix
            c_uint32,  # OperationSet
        )
        set_matrix_ptr = self._base_voice.lpVtbl.contents.SetOutputMatrix
        set_matrix_func = cast(set_matrix_ptr, SetOutputMatrixFunc)

        # Calculate matrix coefficients
        # For stereo output: [L->L, L->R, R->L, R->R]
        matrix = pan_to_matrix(pan, 2)  # Assume stereo output
        matrix_array = (c_float * len(matrix))(*matrix)

        # Source channels: format_channels, Destination: 2 (stereo)
        hresult = set_matrix_func(
            self._voice_ptr,
            None,  # Output to mastering voice
            self._format_channels,
            2,  # Stereo output
            matrix_array,
            0,  # OperationSet
        )
        hrcheck(hresult, "SetOutputMatrix failed")
        logger.debug(f"SourceVoice: pan={pan}")

    def get_state(self) -> PlaybackState:
        """Get current playback state."""
        # Try to get voice state
        GetStateFunc = CFUNCTYPE(
            c_uint32, c_void_p, POINTER(XAUDIO2_VOICE_STATE), c_uint32
        )
        get_state_ptr = self._voice.lpVtbl.contents.GetState
        if not get_state_ptr:
            logger.warning("GetState vtable entry is NULL, using cached state")
            return self._state
            
        get_state_func = cast(get_state_ptr, GetStateFunc)

        state = XAUDIO2_VOICE_STATE()
        hresult = get_state_func(self._voice_ptr, byref(state), 0)
        if hresult >= 0:
            # Log state for debugging (INFO level so it's always visible)
            logger.info(
                f"Voice get_state: BuffersQueued={state.BuffersQueued}, "
                f"SamplesPlayed={state.SamplesPlayed}, "
                f"cached_state={self._state}"
            )
            
            # If BuffersQueued > 0, voice is active
            if state.BuffersQueued > 0:
                if self._state == PlaybackState.PAUSED:
                    return PlaybackState.PAUSED
                return PlaybackState.PLAYING
            else:
                # BuffersQueued == 0 means playback finished
                if self._state == PlaybackState.PLAYING:
                    logger.info("Voice finished: BuffersQueued == 0")
                self._state = PlaybackState.STOPPED
        else:
            from xaudio2py.backends.xaudio2.utils import hr_to_hex
            logger.warning(f"GetState failed with HRESULT {hr_to_hex(hresult)}, using cached state")

        return self._state

    def destroy(self) -> None:
        """Destroy the voice and free resources."""
        # Get DestroyVoice function
        DestroyVoiceFunc = CFUNCTYPE(None, c_void_p)
        destroy_ptr = self._base_voice.lpVtbl.contents.DestroyVoice
        destroy_func = cast(destroy_ptr, DestroyVoiceFunc)

        destroy_func(self._voice_ptr)
        logger.debug("SourceVoice: destroyed")


class MasteringVoice:
    """Wrapper for IXAudio2MasteringVoice (simplified, no IVoice interface)."""

    def __init__(self, voice_ptr: c_void_p):
        """Initialize MasteringVoice wrapper."""
        self._voice_ptr = voice_ptr
        self._voice = cast(voice_ptr, POINTER(IXAudio2Voice)).contents

    def set_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        volume = max(0.0, min(1.0, volume))

        SetVolumeFunc = CFUNCTYPE(c_uint32, c_void_p, c_float, c_uint32)
        set_volume_ptr = self._voice.lpVtbl.contents.SetVolume
        set_volume_func = cast(set_volume_ptr, SetVolumeFunc)

        hresult = set_volume_func(self._voice_ptr, c_float(volume), 0)
        hrcheck(hresult, "MasteringVoice SetVolume failed")

    def destroy(self) -> None:
        """Destroy mastering voice."""
        DestroyVoiceFunc = CFUNCTYPE(None, c_void_p)
        destroy_ptr = self._voice.lpVtbl.contents.DestroyVoice
        destroy_func = cast(destroy_ptr, DestroyVoiceFunc)

        destroy_func(self._voice_ptr)

