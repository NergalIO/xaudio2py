"""Worker thread for backend command execution."""

import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar
from xaudio2py.core.interfaces import IAudioBackend, IBackendWorker
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class Command:
    """Command to execute in worker thread."""

    id: str
    func: Callable[[], T]
    result_event: threading.Event
    result: Optional[Any] = None
    error: Optional[Exception] = None


class BackendWorker(IBackendWorker):
    """
    Worker thread that executes backend commands.

    All XAudio2 operations must be performed in this thread to ensure
    thread safety and proper COM initialization.
    """

    def __init__(self, backend: IAudioBackend):
        self.backend = backend
        self._queue: queue.Queue[Optional[Command]] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._initialized = False

    def start(self) -> None:
        """Start the worker thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=False)
        self._thread.start()

        # Mark as initialized so execute() can be called
        # The thread is running, even though backend.initialize hasn't been called yet
        self._initialized = True

        # Wait for thread to start processing commands
        time.sleep(0.01)  # Small delay to ensure thread is ready

        # Now execute initialization in the worker thread
        self.execute(self.backend.initialize)
        logger.info("Backend worker thread started")

    def stop(self) -> None:
        """Stop the worker thread (blocks until done)."""
        if self._thread is None or not self._thread.is_alive():
            return

        logger.info("Stopping backend worker thread...")
        self._queue.put(None)  # Sentinel
        self._thread.join(timeout=5.0)
        if self._thread.is_alive():
            logger.warning("Worker thread did not stop gracefully")
        self._thread = None
        self._initialized = False
        logger.info("Backend worker thread stopped")

    def execute(self, func: Callable[[], T], timeout: Optional[float] = None) -> T:
        """
        Execute a function in the worker thread and return result.

        Args:
            func: Function to execute (no arguments).
            timeout: Maximum time to wait for result (None = infinite).

        Returns:
            Result of function execution.

        Raises:
            RuntimeError: If worker thread is not running.
            TimeoutError: If timeout is exceeded.
            Exception: Any exception raised by the function.
        """
        if not self._initialized:
            raise RuntimeError("Worker thread not initialized")

        cmd = Command(
            id=str(uuid.uuid4()),
            func=func,
            result_event=threading.Event(),
        )

        self._queue.put(cmd)

        if not cmd.result_event.wait(timeout=timeout):
            raise TimeoutError(f"Command execution timeout after {timeout}s")

        if cmd.error is not None:
            raise cmd.error

        return cmd.result

    def _worker_loop(self) -> None:
        """Main worker loop."""
        logger.debug("Worker thread started")
        try:
            while True:
                cmd = self._queue.get()
                if cmd is None:  # Sentinel
                    break

                try:
                    cmd.result = cmd.func()
                except Exception as e:
                    logger.exception("Error in worker thread command")
                    cmd.error = e
                finally:
                    cmd.result_event.set()
                    self._queue.task_done()

        except Exception as e:
            logger.exception("Fatal error in worker thread")
        finally:
            logger.debug("Worker thread exiting")

