"""Validation utilities."""


def validate_volume(volume: float) -> float:
    """Validate and clamp volume to [0.0, 1.0]."""
    if volume < 0.0:
        return 0.0
    if volume > 1.0:
        return 1.0
    return volume


def validate_pan(pan: float) -> float:
    """Validate and clamp pan to [-1.0, 1.0]."""
    if pan < -1.0:
        return -1.0
    if pan > 1.0:
        return 1.0
    return pan

