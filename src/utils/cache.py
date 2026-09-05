from collections import OrderedDict
from dataclasses import dataclass
import threading
import time
from typing import Any
from PIL.Image import Image


@dataclass
class _CacheEntry:
    image: Image
    timestamp: float


class ImageCache:
    """Thread-safe, bounded image cache with LRU eviction and TTL metrics."""

    def __init__(self, max_size: int = 50, ttl_seconds: float = 300.0) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits: int = 0
        self._misses: int = 0

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
                self._misses += 1
                return None

            if self._is_expired(entry, now):
                self._cache.pop(key, None)
                self._misses += 1
                return None

            self._hits += 1
            self._cache.move_to_end(key)
            return entry.image

    def delete(self, key: str) -> bool:
        """Delete an image from the cache. Returns True if existed."""
        with self._lock:
            return self._cache.pop(key, None) is not None

    def clear(self, reset_stats: bool = False) -> None:
        """Empty the cache. Optionally reset telemetry statistics."""
        with self._lock:
            self._cache.clear()
            if reset_stats:
                self._hits = 0
                self._misses = 0

    def get_stats(self) -> dict[str, Any]:
        """Return cache usage and telemetry statistics."""
        with self._lock:
            now = time.time()
            self._purge_expired(now)
            total = self._hits + self._misses
            hit_ratio = round((self._hits / total * 100.0), 2) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total,
                "hit_ratio_percent": hit_ratio,
                "current_size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "cached_keys": list(self._cache.keys()),
            }

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
