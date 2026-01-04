"""ctypes vtable declarations for XAudio2 COM interfaces."""

from ctypes import (
    Structure,
    POINTER,
    c_void_p,
    c_uint32,
    c_float,
    c_uint8,
    c_uint64,
    CFUNCTYPE,
)
from xaudio2py.backends.xaudio2.bindings import (
    WAVEFORMATEX,
    XAUDIO2_BUFFER,
    XAUDIO2_VOICE_STATE,
)


# VTable structures (simplified - only methods we need)
class IXAudio2Vtbl(Structure):
    """IXAudio2 vtable (simplified)."""

    _fields_ = [
        ("QueryInterface", c_void_p),
        ("AddRef", c_void_p),
        ("Release", c_void_p),
        ("RegisterForCallbacks", c_void_p),
        ("UnregisterForCallbacks", c_void_p),
        ("CreateSourceVoice", c_void_p),
        ("CreateSubmixVoice", c_void_p),
        ("CreateMasteringVoice", c_void_p),
        ("StartEngine", c_void_p),
        ("StopEngine", c_void_p),
        ("CommitChanges", c_void_p),
        ("GetPerformanceData", c_void_p),
        ("SetDebugConfiguration", c_void_p),
        ("GetDeviceCount", c_void_p),
        ("GetDeviceDetails", c_void_p),
        ("Initialize", c_void_p),
        ("Release", c_void_p),  # Duplicate, but that's how it is
    ]


class IXAudio2(Structure):
    """IXAudio2 interface."""

    _fields_ = [("lpVtbl", POINTER(IXAudio2Vtbl))]


class IXAudio2VoiceVtbl(Structure):
    """IXAudio2Voice vtable (base for all voices)."""

    _fields_ = [
        ("GetVoiceDetails", c_void_p),
        ("SetOutputVoices", c_void_p),
        ("SetEffectChain", c_void_p),
        ("EnableEffect", c_void_p),
        ("DisableEffect", c_void_p),
        ("GetEffectState", c_void_p),
        ("SetEffectParameters", c_void_p),
        ("GetEffectParameters", c_void_p),
        ("SetFilterParameters", c_void_p),
        ("GetFilterParameters", c_void_p),
        ("SetOutputFilterParameters", c_void_p),
        ("GetOutputFilterParameters", c_void_p),
        ("SetVolume", c_void_p),
        ("GetVolume", c_void_p),
        ("SetChannelVolumes", c_void_p),
        ("GetChannelVolumes", c_void_p),
        ("SetOutputMatrix", c_void_p),
        ("GetOutputMatrix", c_void_p),
        ("DestroyVoice", c_void_p),
    ]


class IXAudio2Voice(Structure):
    """IXAudio2Voice interface (base)."""

    _fields_ = [("lpVtbl", POINTER(IXAudio2VoiceVtbl))]


class IXAudio2SourceVoiceVtbl(Structure):
    """
    IXAudio2SourceVoice vtable.
    
    In COM, derived interfaces include ALL base interface methods first.
    IXAudio2SourceVoice inherits from IXAudio2Voice, so all 18 base methods
    come first, then the SourceVoice-specific methods.
    """
    _fields_ = [
        # Base interface methods (from IXAudio2VoiceVtbl) - MUST be first
        ("GetVoiceDetails", c_void_p),
        ("SetOutputVoices", c_void_p),
        ("SetEffectChain", c_void_p),
        ("EnableEffect", c_void_p),
        ("DisableEffect", c_void_p),
        ("GetEffectState", c_void_p),
        ("SetEffectParameters", c_void_p),
        ("GetEffectParameters", c_void_p),
        ("SetFilterParameters", c_void_p),
        ("GetFilterParameters", c_void_p),
        ("SetOutputFilterParameters", c_void_p),
        ("GetOutputFilterParameters", c_void_p),
        ("SetVolume", c_void_p),
        ("GetVolume", c_void_p),
        ("SetChannelVolumes", c_void_p),
        ("GetChannelVolumes", c_void_p),
        ("SetOutputMatrix", c_void_p),
        ("GetOutputMatrix", c_void_p),
        ("DestroyVoice", c_void_p),
        # SourceVoice-specific methods (after base methods)
        ("Start", c_void_p),
        ("Stop", c_void_p),
        ("SubmitSourceBuffer", c_void_p),
        ("FlushSourceBuffers", c_void_p),
        ("Discontinuity", c_void_p),
        ("ExitLoop", c_void_p),
        ("GetState", c_void_p),
        ("SetFrequencyRatio", c_void_p),
        ("GetFrequencyRatio", c_void_p),
        ("SetSourceSampleRate", c_void_p),
    ]


class IXAudio2SourceVoice(Structure):
    """IXAudio2SourceVoice interface."""

    _fields_ = [("lpVtbl", POINTER(IXAudio2SourceVoiceVtbl))]


# Function signatures for calling vtable methods
# These will be set up dynamically when we get the interface pointer

