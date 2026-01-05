"""Utility functions for XAudio2 backend."""

from ctypes import c_int32
from xaudio2py.core.exceptions import BackendError, XAudio2Error
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


def hr_to_hex(hr: int) -> str:
    """
    Convert HRESULT to readable hex string (unsigned 32-bit).

    Args:
        hr: HRESULT value (signed or unsigned).

    Returns:
        Hex string in format 0xXXXXXXXX.
    """
    return f"0x{(hr & 0xFFFFFFFF):08X}"


def hrcheck(hresult: int, message: str = "") -> None:
    """
    Check HRESULT and raise XAudio2Error if failed.

    Args:
        hresult: HRESULT value.
        message: Optional error message.

    Raises:
        BackendError: If HRESULT indicates failure (< 0).
    """
    # HRESULT is signed 32-bit integer
    # Success codes are >= 0, failure codes are < 0
    # Convert to signed int32 to handle unsigned values from ctypes
    if isinstance(hresult, c_int32):
        hresult = hresult.value
    else:
        # Convert unsigned to signed int32
        hresult = c_int32(hresult).value
    
    if hresult < 0:
        raise BackendError(f"{message} (HRESULT: {hr_to_hex(hresult)})", hresult=hresult)


def safe_call(func, *args, error_message: str = "", **kwargs):
    """
    Call a function and check HRESULT.

    Args:
        func: Function to call.
        *args: Positional arguments.
        error_message: Error message if call fails.
        **kwargs: Keyword arguments.

    Returns:
        Function result.

    Raises:
        BackendError: If HRESULT indicates failure.
    """
    hresult = func(*args, **kwargs)
    hrcheck(hresult, error_message)
    return hresult


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def pan_to_matrix(pan: float, channels: int) -> list:
    """
    Convert pan value to output matrix coefficients.

    Args:
        pan: Pan value (-1.0 left, 0.0 center, 1.0 right).
        channels: Number of output channels (1 or 2).

    Returns:
        List of matrix coefficients.
    """
    pan = clamp(pan, -1.0, 1.0)

    if channels == 1:
        # Mono output: pan doesn't apply
        return [1.0]

    if channels == 2:
        # Stereo: left and right gains
        if pan <= 0.0:
            # Pan left: reduce right channel
            left_gain = 1.0
            right_gain = 1.0 + pan  # pan is negative or zero
        else:
            # Pan right: reduce left channel
            left_gain = 1.0 - pan
            right_gain = 1.0

        return [left_gain, 0.0, 0.0, right_gain]  # [L->L, L->R, R->L, R->R]

    # Default: no panning
    return [1.0] * channels

