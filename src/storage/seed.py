from datetime import datetime, timedelta, timezone
import random
from storage.base import MeterReading, StorageBackend


def seed_demo_history(
    storage: StorageBackend | None,
    meter_name: str = "total",
    days: int = 14,
    base_val: float = 300.0,
) -> int:
    """Generate sample historical readings for visualization and testing."""
    if storage is None:
        return 0
    now = datetime.now(timezone.utc)
    current_val = base_val
    count = 0
    for day_offset in range(days, -1, -1):
        day_time = now - timedelta(days=day_offset)
        for hour in [6, 12, 18, 22]:
            ts = day_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            increment = random.uniform(0.04, 0.25)  # nosec B311
            current_val += increment
            storage.record_reading(
                timestamp=ts,
                meters={
                    meter_name: MeterReading(
                        value=round(current_val, 3),
                        raw_value=f"{current_val:.3f}",
                        unit="m3",
                        quality="good",
                        confidence=100.0,
                    ),
                    "digital": MeterReading(
                        value=round(current_val, 0),
                        raw_value=f"{int(current_val)}",
                        unit="m3",
                        quality="good",
                        confidence=99.0,
                    ),
                },
            )
            count += 1
    return count
