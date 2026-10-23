"""Background worker that periodically drains the local synchronization outbox."""

import logging
from threading import Event, Thread

from shared.infrastructure.database import connect_database, db
from synchronization.application.services import TelemetrySynchronizationService


logger = logging.getLogger(__name__)


class SynchronizationWorker:
    """Run a bounded synchronization cycle at a fixed interval in one Edge process."""

    def __init__(
        self, synchronization_service: TelemetrySynchronizationService, interval_seconds: int
    ):
        self._synchronization_service = synchronization_service
        self._interval_seconds = interval_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the daemon only once; no worker is created while sync is disabled."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(
            target=self._run,
            name="icetrack-telemetry-synchronization",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Request worker shutdown without blocking Flask process termination."""
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                connect_database()
                results = self._synchronization_service.synchronize_available()
                for result in results:
                    if result.outcome == "failed":
                        logger.warning(
                            "Telemetry batch %s remains queued: %s",
                            result.batch_uid,
                            result.error,
                        )
            except Exception:
                logger.exception("Unexpected synchronization worker failure")
            finally:
                if not db.is_closed():
                    db.close()
            self._stop_event.wait(self._interval_seconds)
