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
        # Use daemon thread to ensure it doesn't block program exit
        # Proper shutdown via stop() is still required for cleanup
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
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
            self._initialized = False
            return

        logger.info("Stopping backend worker thread...")
        # First, prevent new commands from being accepted
        self._initialized = False
        
        # Signal stop - this will cause the thread to exit on next check
        self._stop_event.set()
        
        # Send multiple sentinels to ensure thread wakes up and exits
        # This handles race conditions where thread might be in different states
        try:
            self._queue.put_nowait(None)  # Try non-blocking first
        except queue.Full:
            self._queue.put(None)  # Fallback to blocking if queue is full
        
        # Wait for thread to exit
        self._thread.join(timeout=5.0)
        if self._thread.is_alive():
            logger.warning("Worker thread did not stop gracefully within timeout")
            # Try one more sentinel
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
            # Wait a bit more
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                logger.error("Worker thread still alive after timeout - may need manual cleanup")
            self._thread = None
        else:
            logger.info("Backend worker thread stopped")
            self._thread = None

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
            while not self._stop_event.is_set():
                try:
                    # Use timeout to periodically check stop event
                    cmd = self._queue.get(timeout=0.1)
                    
                    # Check stop event immediately after getting command
                    if self._stop_event.is_set():
                        logger.debug("Stop event set, exiting worker loop")
                        # Put sentinel back if it wasn't one, or just break
                        if cmd is not None:
                            # Can't put back easily, but we're exiting anyway
                            pass
                        break
                    
                    if cmd is None:  # Sentinel
                        logger.debug("Received sentinel, exiting worker loop")
                        break

                    try:
                        cmd.result = cmd.func()
                    except Exception as e:
                        logger.exception("Error in worker thread command")
                        cmd.error = e
                    finally:
                        cmd.result_event.set()
                        self._queue.task_done()
                        
                    # Check stop event after command completion
                    if self._stop_event.is_set():
                        logger.debug("Stop event set after command, exiting worker loop")
                        break
                        
                except queue.Empty:
                    # Timeout - check stop event and continue loop
                    continue

        except Exception as e:
            logger.exception("Fatal error in worker thread")
        finally:
            logger.debug("Worker thread exiting")

