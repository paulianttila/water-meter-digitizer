import asyncio
from datetime import datetime, timezone, timedelta
import logging
import time
from typing import Any, Callable

from configuration import Poller
from mqtt.client import MQTTService
from processor.digitizer import MeterResult

logger = logging.getLogger(__name__)


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

        self._running = True
        self._trigger_event.clear()
        self._task = asyncio.create_task(self._run_loop())
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
        logger.info("Background poller stopped")

    def trigger_now(self) -> None:
        """Trigger an immediate readout cycle asynchronously."""
        logger.info("Manual poller trigger requested")
        self._trigger_event.set()

    async def _run_loop(self) -> None:
        """Main polling scheduler loop."""
        if self.config.run_on_startup:
            await self._execute_poll()

        while self._running:
            interval = max(5, self.config.interval_seconds)
            self.next_run = datetime.now(timezone.utc) + timedelta(seconds=interval)

            try:
                # Wait for interval or immediate trigger
                await asyncio.wait_for(self._trigger_event.wait(), timeout=interval)
                self._trigger_event.clear()
                logger.debug("Poller triggered ahead of interval timer")
            except asyncio.TimeoutError:
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
        self.last_run = datetime.now(timezone.utc)
        self.total_runs += 1

        try:
            logger.info("Background poller executing meter readout...")
            # Run CPU-bound neural network inference in a separate thread
            result: MeterResult = await asyncio.to_thread(
                self.readout_func,
                saveimages=self.config.save_images,
            )

            duration = time.time() - start_time
            self.successful_runs += 1
            self.last_error = ""

            logger.info("Meter readout completed in %.2fs", duration)

            # Publish to MQTT if service is active
            if self.mqtt_service:
                self.mqtt_service.publish_meter_result(
                    meter_result=result,
                    processing_time_sec=duration,
                )

            return result
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
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "last_error": self.last_error,
        }
