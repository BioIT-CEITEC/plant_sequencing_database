"""
Thread-safe rate limiter for embedding API calls.
Prevents exceeding CERIT's max_parallel_requests limit (default: 4).
Uses semaphore-based concurrency control with minimum inter-request spacing.
"""
import threading
import time


class EmbeddingRateLimiter:
    """Semaphore + token bucket for embedding API concurrency control.
    
    Args:
        max_concurrent: Maximum simultaneous API requests (stay under provider limit).
        min_interval: Minimum seconds between consecutive API calls.
    """

    def __init__(self, max_concurrent: int = 3, min_interval: float = 0.1):
        self._semaphore = threading.Semaphore(max_concurrent)
        self._lock = threading.Lock()
        self._last_request_time = 0.0
        self._min_interval = min_interval

    def acquire(self):
        """Acquire a slot. Blocks if all slots are in use."""
        self._semaphore.acquire()
        with self._lock:
            now = time.time()
            wait = self._min_interval - (now - self._last_request_time)
            if wait > 0:
                time.sleep(wait)
            self._last_request_time = time.time()

    def release(self):
        """Release a slot back to the pool."""
        self._semaphore.release()
