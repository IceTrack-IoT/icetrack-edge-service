"""Use case that delivers durable local telemetry batches to the cloud."""

from dataclasses import dataclass

from synchronization.infrastructure.cloud_gateway import (
    CloudRequestError,
    IceTrackCloudGateway,
)
from synchronization.infrastructure.repositories import (
    SynchronizationRepository,
    TelemetrySyncBatch,
)


@dataclass(frozen=True)
class SynchronizationResult:
    """Outcome of one explicit synchronization attempt."""

    outcome: str
    batch_uid: str | None = None
    sample_count: int = 0
    error: str | None = None


class TelemetrySynchronizationService:
    """Build and deliver batches while preserving a retryable local outbox."""

    def __init__(
        self,
        repository: SynchronizationRepository,
        cloud_gateway: IceTrackCloudGateway,
        batch_size: int,
        sync_enabled: bool,
    ):
        self._repository = repository
        self._cloud_gateway = cloud_gateway
        self._batch_size = batch_size
        self._sync_enabled = sync_enabled

    def synchronize_once(self) -> SynchronizationResult:
        """Attempt delivery of one pending batch, keeping failures durable."""
        if not self._sync_enabled:
            return SynchronizationResult(
                outcome="disabled",
                error="Cloud synchronization is disabled",
            )
        if not self._cloud_gateway.is_configured:
            return SynchronizationResult(
                outcome="not_configured",
                error="Cloud synchronization is not configured",
            )
        batch = self._repository.next_deliverable_batch(self._batch_size)
        if batch is None:
            return SynchronizationResult(outcome="idle")
        return self._deliver(batch)

    def synchronize_available(self, maximum_batches: int = 5) -> list[SynchronizationResult]:
        """Deliver a bounded number of queued batches during one worker cycle."""
        results: list[SynchronizationResult] = []
        for _ in range(maximum_batches):
            result = self.synchronize_once()
            results.append(result)
            if result.outcome != "synchronized":
                break
        return results

    def status_counts(self) -> dict[str, int]:
        """Expose local queue health without exposing stored telemetry values."""
        return self._repository.status_counts()

    def _deliver(self, batch: TelemetrySyncBatch) -> SynchronizationResult:
        try:
            cloud_device = self._cloud_gateway.authenticate_device(batch.device_uid)
            self._cloud_gateway.submit_batch(batch, cloud_device)
        except CloudRequestError as error:
            self._repository.mark_failed(batch.batch_uid, str(error))
            return SynchronizationResult(
                outcome="failed",
                batch_uid=batch.batch_uid,
                sample_count=batch.sample_count,
                error=str(error),
            )
        self._repository.mark_synchronized(batch.batch_uid)
        return SynchronizationResult(
            outcome="synchronized",
            batch_uid=batch.batch_uid,
            sample_count=batch.sample_count,
        )
