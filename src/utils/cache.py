from collections import OrderedDict
from dataclasses import dataclass
import threading
import time
from PIL.Image import Image


@dataclass
class _CacheEntry:
    image: Image
    timestamp: float


class ImageCache:
    """Thread-safe, bounded image cache with LRU eviction and TTL support."""

    def __init__(self, max_size: int = 50, ttl_seconds: float = 300.0) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    def _is_expired(self, entry: _CacheEntry, now: float) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (now - entry.timestamp) > self.ttl_seconds

    def _purge_expired(self, now: float) -> None:
        if self.ttl_seconds <= 0:
            return
        expired_keys = [k for k, v in self._cache.items() if self._is_expired(v, now)]
        for k in expired_keys:
            self._cache.pop(k, None)

    def set(self, key: str, image: Image) -> None:
        """Store an image in the cache with the current timestamp."""
        if image is None:
            return

        with self._lock:
            now = time.time()
            self._purge_expired(now)

            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = _CacheEntry(image=image, timestamp=now)

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def set_many(self, images: dict[str, Image]) -> None:
        """Store multiple images in the cache atomically."""
        if not images:
            return

        with self._lock:
            now = time.time()
            self._purge_expired(now)
            for key, image in images.items():
                if image is None:
                    continue
                if key in self._cache:
                    self._cache.move_to_end(key)
                self._cache[key] = _CacheEntry(image=image, timestamp=now)

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def get(self, key: str) -> Image | None:
        """Retrieve an image from the cache. Returns None if absent or expired."""
        with self._lock:
            now = time.time()
            entry = self._cache.get(key)
            if entry is None:
                return None

            if self._is_expired(entry, now):
                self._cache.pop(key, None)
                return None

            self._cache.move_to_end(key)
            return entry.image

    def delete(self, key: str) -> bool:
        """Delete an image from the cache. Returns True if existed."""
        with self._lock:
            return self._cache.pop(key, None) is not None

    def clear(self) -> None:
        """Empty the cache."""
        with self._lock:
            self._cache.clear()

    def keys(self) -> list[str]:
        """Return list of active non-expired keys."""
        with self._lock:
            now = time.time()
            self._purge_expired(now)
            return list(self._cache.keys())

    def __len__(self) -> int:
        with self._lock:
            now = time.time()
            self._purge_expired(now)
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            now = time.time()
            entry = self._cache.get(key)
            if entry is None:
                return False
            if self._is_expired(entry, now):
                self._cache.pop(key, None)
                return False
            return True
