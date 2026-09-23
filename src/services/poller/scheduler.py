import asyncio
import contextlib
import logging
import math
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from config.models import Poller
from processor.digitizer import MeterResult
from services.mqtt.client import MQTTService
from services.poller.consensus import ConsensusFilter

logger = logging.getLogger(__name__)


def calculate_next_aligned_delay(
    now: float,
    interval_seconds: int,
    min_delay: float = 0.05,
) -> tuple[float, datetime]:
    """Compute seconds to wait until next wall-clock modulo boundary and return target datetime.

    Args:
        now: Current Unix epoch timestamp in seconds.
        interval_seconds: Polling interval in seconds (>= 1).
        min_delay: Minimum acceptable delay before targeting next interval (avoids double-firing).

    Returns:
        tuple[float, datetime]: (seconds_to_wait, target_datetime_with_timezone)
    """
    interval = max(1, interval_seconds)
    next_boundary = (math.floor(now / interval) + 1) * interval
    delay = next_boundary - now
    if delay <= min_delay:
        next_boundary += interval
        delay = next_boundary - now

    target_dt = datetime.fromtimestamp(next_boundary).astimezone()
    return delay, target_dt


class BackgroundPoller:
    """Asynchronous background scheduler for periodic meter readouts."""

    def __init__(
        self,
        config: Poller,
        readout_func: Callable[..., MeterResult],
        mqtt_service: MQTTService | None = None,
    ) -> None:
        self.config = config
        self.readout_func = readout_func
        self.mqtt_service = mqtt_service
        self.consensus_filter = ConsensusFilter(window_size=self.config.consensus_reads)

        self._task: asyncio.Task | None = None
        self._trigger_event = asyncio.Event()
        self._running = False
        self._is_polling = False

        self.last_run: datetime | None = None
        self.next_run: datetime | None = None
        self.total_runs: int = 0
        self.successful_runs: int = 0
        self.failed_runs: int = 0
        self.last_error: str = ""

    def start(self) -> None:
        """Start the background polling task."""
        if not self.config.enabled:
            logger.info("Background poller is disabled in configuration")
            return

        if self._running and self._task and not self._task.done():
            logger.debug("Background poller is already running")
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug(
                "No running event loop; poller start deferred until loop is active"
            )
            return

        self._running = True
        self._trigger_event.clear()
        self._task = loop.create_task(self._run_loop())
        logger.info(
            "Background poller started with interval %ds",
            self.config.interval_seconds,
        )

    def stop(self) -> None:
        """Stop the background polling task."""
        self._running = False
        self._trigger_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
        self.consensus_filter.clear()
        logger.info("Background poller stopped")

    def trigger_now(self) -> None:
        """Trigger an immediate readout cycle asynchronously."""
        logger.info("Manual poller trigger requested")
        if self._running and self._task and not self._task.done():
            self._trigger_event.set()
        else:
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._execute_poll())
            except RuntimeError:
                logger.warning(
                    "Cannot execute manual poll: no active asyncio event loop"
                )

    async def _run_loop(self) -> None:
        """Main polling scheduler loop."""
        if self.config.run_on_startup:
            await self._execute_poll()

        while self._running:
            interval = max(1, self.config.interval_seconds)
            if getattr(self.config, "sync_to_clock", True):
                delay, next_dt = calculate_next_aligned_delay(time.time(), interval)
                self.next_run = next_dt
            else:
                delay = float(interval)
                self.next_run = datetime.now().astimezone() + timedelta(
                    seconds=interval
                )

            try:
                # Wait for interval or immediate trigger
                await asyncio.wait_for(self._trigger_event.wait(), timeout=delay)
                self._trigger_event.clear()
                logger.debug("Poller triggered ahead of interval timer")
            except TimeoutError:
                pass
            except asyncio.CancelledError:
                break

            if not self._running:
                break

            await self._execute_poll()

    async def _execute_poll(self) -> MeterResult | None:
        """Execute a single meter reading cycle in thread pool."""
        if self._is_polling:
            logger.warning("Poller readout already in progress; skipping duplicate run")
            return None

        self._is_polling = True
        start_time = time.time()
        self.last_run = datetime.now().astimezone()
        self.total_runs += 1

        try:
            logger.info("Background poller executing meter readout...")
            # Run CPU-bound neural network inference in a separate thread
            result: MeterResult = await asyncio.to_thread(
                self.readout_func,
                saveimages=self.config.save_images,
            )

            # Apply temporal consensus / median filter
            consensus_result, is_outlier = self.consensus_filter.filter(result)

            duration = time.time() - start_time
            self.successful_runs += 1
            self.last_error = ""

            logger.info("Meter readout completed in %.2fs", duration)

            if is_outlier:
                logger.warning(
                    "Poller detected transient outlier reading; using consensus result"
                )
                if self._running and self.config.consensus_reads > 1:
                    retry_delay = max(1, min(self.config.retry_interval_seconds, 5))
                    with contextlib.suppress(RuntimeError):
                        asyncio.get_running_loop().call_later(
                            retry_delay, self._trigger_event.set
                        )

            # Publish to MQTT if service is active
            if self.mqtt_service:
                self.mqtt_service.publish_meter_result(
                    meter_result=consensus_result,
                    processing_time_sec=duration,
                )

            return consensus_result
        except Exception as e:
            duration = time.time() - start_time
            self.failed_runs += 1
            self.last_error = str(e)
            logger.error("Background poller failed after %.2fs: %s", duration, e)

            if self.mqtt_service:
                self.mqtt_service.publish_error(str(e))

            return None
        finally:
            self._is_polling = False

    def get_status(self) -> dict[str, Any]:
        """Return poller status and statistics."""
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "is_polling": self._is_polling,
            "interval_seconds": self.config.interval_seconds,
            "sync_to_clock": getattr(self.config, "sync_to_clock", True),
            "consensus_reads": self.config.consensus_reads,
            "consensus_buffer_size": self.consensus_filter.current_size,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "last_error": self.last_error,
        }
