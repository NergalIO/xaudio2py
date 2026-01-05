"""Tests for thread dispatch and worker."""

import threading
import time
import pytest
from xaudio2py.backends.null_backend import NullBackend
from xaudio2py.concurrency.worker import BackendWorker


def test_worker_start_stop():
    """Test worker thread start and stop."""
    backend = NullBackend()
    worker = BackendWorker(backend)

    worker.start()
    assert worker._thread is not None
    assert worker._thread.is_alive()

    worker.stop()
    assert worker._thread is None or not worker._thread.is_alive()


def test_worker_execute():
    """Test executing commands in worker thread."""
    backend = NullBackend()
    worker = BackendWorker(backend)

    worker.start()

    # Execute initialization
    worker.execute(backend.initialize)
    assert backend._initialized

    # Execute a simple function
    result = worker.execute(lambda: 42)
    assert result == 42

    worker.stop()


def test_worker_execute_with_error():
    """Test error handling in worker thread."""
    backend = NullBackend()
    worker = BackendWorker(backend)

    worker.start()

    def failing_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        worker.execute(failing_function)

    worker.stop()


def test_worker_execute_timeout():
    """Test command execution timeout."""
    backend = NullBackend()
    worker = BackendWorker(backend)

    worker.start()

    def slow_function():
        time.sleep(2.0)
        return 42

    with pytest.raises(TimeoutError):
        worker.execute(slow_function, timeout=0.1)

    worker.stop()


def test_worker_not_initialized():
    """Test executing before worker is started."""
    backend = NullBackend()
    worker = BackendWorker(backend)

    with pytest.raises(RuntimeError, match="not initialized"):
        worker.execute(lambda: 42)


def test_concurrent_executions():
    """Test concurrent command executions."""
    backend = NullBackend()
    worker = BackendWorker(backend)

    worker.start()

    results = []
    errors = []

    def task(value):
        return value * 2

    def run_task(value):
        try:
            result = worker.execute(lambda: task(value))
            results.append(result)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(10):
        t = threading.Thread(target=run_task, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 10
    assert sorted(results) == [i * 2 for i in range(10)]

    worker.stop()

