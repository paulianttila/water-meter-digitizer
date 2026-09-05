import concurrent.futures
import time
from PIL import Image

from utils.cache import ImageCache


def _create_test_image(color=(255, 0, 0)) -> Image.Image:
    return Image.new("RGB", (10, 10), color=color)


def test_cache_set_get():
    cache = ImageCache(max_size=10, ttl_seconds=60)
    img = _create_test_image()
    cache.set("test_img", img)

    assert "test_img" in cache
    assert len(cache) == 1
    assert cache.get("test_img") is not None
    assert cache.get("non_existent") is None


def test_cache_set_many():
    cache = ImageCache(max_size=10, ttl_seconds=60)
    images = {
        "img1": _create_test_image((255, 0, 0)),
        "img2": _create_test_image((0, 255, 0)),
        "img3": _create_test_image((0, 0, 255)),
    }
    cache.set_many(images)

    assert len(cache) == 3
    assert set(cache.keys()) == {"img1", "img2", "img3"}


def test_cache_lru_eviction():
    cache = ImageCache(max_size=3, ttl_seconds=60)
    img = _create_test_image()

    cache.set("img1", img)
    cache.set("img2", img)
    cache.set("img3", img)
    assert len(cache) == 3

    # Access img1 to make it most recently used (LRU becomes img2)
    _ = cache.get("img1")

    # Add img4, should evict img2
    cache.set("img4", img)

    assert len(cache) == 3
    assert "img1" in cache
    assert "img2" not in cache
    assert "img3" in cache
    assert "img4" in cache


def test_cache_ttl_expiration():
    cache = ImageCache(max_size=10, ttl_seconds=0.05)
    img = _create_test_image()

    cache.set("ephemeral", img)
    assert "ephemeral" in cache
    assert cache.get("ephemeral") is not None

    time.sleep(0.06)

    assert cache.get("ephemeral") is None
    assert "ephemeral" not in cache
    assert len(cache) == 0


def test_cache_concurrent_access():
    cache = ImageCache(max_size=20, ttl_seconds=60)
    img = _create_test_image()

    def writer(idx: int):
        for i in range(50):
            cache.set(f"thread_{idx}_img_{i}", img)

    def reader(idx: int):
        for i in range(50):
            _ = cache.get(f"thread_{idx}_img_{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i in range(4):
            futures.append(executor.submit(writer, i))
            futures.append(executor.submit(reader, i))
    assert len(cache) <= 20


def test_cache_stats():
    cache = ImageCache(max_size=5, ttl_seconds=60)
    img = _create_test_image()

    cache.set("key1", img)
    cache.set("key2", img)

    # 2 hits, 1 miss
    _ = cache.get("key1")
    _ = cache.get("key1")
    _ = cache.get("nonexistent")

    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["total_requests"] == 3
    assert stats["hit_ratio_percent"] == 66.67
    assert stats["current_size"] == 2
    assert stats["max_size"] == 5
    assert stats["ttl_seconds"] == 60.0
    assert set(stats["cached_keys"]) == {"key1", "key2"}

    # Test clear with reset_stats
    cache.clear(reset_stats=True)
    cleared_stats = cache.get_stats()
    assert cleared_stats["hits"] == 0
    assert cleared_stats["misses"] == 0
    assert cleared_stats["total_requests"] == 0
    assert cleared_stats["hit_ratio_percent"] == 0.0
    assert cleared_stats["current_size"] == 0
