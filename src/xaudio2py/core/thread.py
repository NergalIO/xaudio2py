"""Backward compatibility: BackendWorker moved to concurrency.worker."""

# Re-export for backward compatibility
from xaudio2py.concurrency.worker import BackendWorker

__all__ = ["BackendWorker"]
