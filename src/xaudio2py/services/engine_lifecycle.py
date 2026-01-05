"""Service for managing audio engine lifecycle."""

from typing import Optional
from xaudio2py.core.exceptions import EngineNotStartedError
from xaudio2py.core.interfaces import IAudioBackend, IBackendWorker
from xaudio2py.core.models import EngineConfig
from xaudio2py.concurrency.worker import BackendWorker
from xaudio2py.utils.log import get_logger

logger = get_logger(__name__)


class EngineLifecycleService:
    """
    Service for managing audio engine lifecycle.
    
    Responsibilities:
    - Initialize and shutdown backend
    - Manage worker thread lifecycle
    - Ensure proper resource cleanup
    """
    
    def __init__(
        self,
        backend: IAudioBackend,
        config: EngineConfig,
        worker: Optional[IBackendWorker] = None,
    ):
        """
        Initialize lifecycle service.
        
        Args:
            backend: Audio backend implementation.
            config: Engine configuration.
            worker: Optional worker implementation (for testing).
        """
        self._backend = backend
        self._config = config
        self._worker: Optional[IBackendWorker] = worker
        self._started = False
    
    def start(self) -> None:
        """
        Start the audio engine.
        
        Raises:
            RuntimeError: If engine is already started.
        """
        if self._started:
            logger.warning("Engine already started")
            return
        
        if self._worker is None:
            self._worker = BackendWorker(self._backend)
        
        self._worker.start()
        self._started = True
        logger.info("Audio engine started")
    
    def shutdown(self) -> None:
        """
        Shutdown the audio engine and free all resources.
        
        This method is idempotent and safe to call multiple times.
        """
        if not self._started:
            logger.debug("Engine not started, skipping shutdown")
            return
        
        logger.info("Shutting down audio engine...")
        
        # Shutdown backend in worker thread
        if self._worker is not None:
            try:
                self._worker.execute(self._backend.shutdown)
            except Exception as e:
                logger.warning(f"Error during backend shutdown: {e}")
            
            # Stop worker thread
            try:
                self._worker.stop()
            except Exception as e:
                logger.warning(f"Error stopping worker thread: {e}")
            
            self._worker = None
        
        self._started = False
        logger.info("Audio engine shut down")
    
    @property
    def is_started(self) -> bool:
        """
        Check if engine is started.
        
        Returns:
            True if started, False otherwise.
        """
        return self._started
    
    @property
    def worker(self) -> Optional[IBackendWorker]:
        """
        Get worker instance.
        
        Returns:
            Worker instance if started, None otherwise.
            
        Raises:
            EngineNotStartedError: If engine is not started.
        """
        if not self._started:
            raise EngineNotStartedError("Engine must be started before accessing worker")
        return self._worker
    
    @property
    def backend(self) -> IAudioBackend:
        """
        Get backend instance.
        
        Returns:
            Backend instance.
        """
        return self._backend

