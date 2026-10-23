"""Peewee outbox repository for durable telemetry synchronization batches."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from synchronization.infrastructure.models import TelemetrySyncBatchModel
from telemetry.infrastructure.models import TelemetrySampleModel


PENDING = "PENDING"
FAILED = "FAILED"
SYNCHRONIZED = "SYNCHRONIZED"


@dataclass(frozen=True)
class TelemetrySyncBatch:
    """Cloud-ready aggregation of one or more local telemetry samples."""

    batch_uid: str
    device_uid: str
    sample_ids: tuple[int, ...]
    min_temperature: float
    max_temperature: float
    avg_temperature: float
    avg_humidity: float
    sample_count: int
    recorded_at: datetime
    status: str
    sync_attempts: int


class SynchronizationRepository:
    """Build, retrieve and update the durable local synchronization outbox."""

    def migrate_schema(self) -> None:
        """Add synchronization linkage when upgrading a pre-outbox SQLite file."""
        database = TelemetrySampleModel._meta.database
        columns = {
            column.name for column in database.get_columns("telemetry_samples")
        }
        if "sync_batch_uid" not in columns:
            database.execute_sql(
                'ALTER TABLE "telemetry_samples" ADD COLUMN "sync_batch_uid" VARCHAR(64) NULL'
            )
            database.execute_sql(
                'CREATE INDEX IF NOT EXISTS "telemetry_samples_sync_batch_uid" '
                'ON "telemetry_samples" ("sync_batch_uid")'
            )

    def next_deliverable_batch(self, batch_size: int) -> TelemetrySyncBatch | None:
        """Return an existing retry first, or create one from unbatched samples."""
        row = (
            TelemetrySyncBatchModel.select()
            .where(TelemetrySyncBatchModel.status.in_((PENDING, FAILED)))
            .order_by(TelemetrySyncBatchModel.created_at)
            .first()
        )
        if row is not None:
            return self._to_batch(row)
        return self._create_next_batch(batch_size)

    def mark_synchronized(self, batch_uid: str) -> None:
        """Mark a delivered batch as complete without deleting its audit trail."""
        TelemetrySyncBatchModel.update(
            status=SYNCHRONIZED,
            synchronized_at=datetime.now(UTC),
            last_sync_error=None,
        ).where(TelemetrySyncBatchModel.batch_uid == batch_uid).execute()

    def mark_failed(self, batch_uid: str, error: str) -> None:
        """Record a retryable cloud-delivery failure."""
        safe_error = error[:500] if error else "Unknown synchronization error"
        TelemetrySyncBatchModel.update(
            status=FAILED,
            sync_attempts=TelemetrySyncBatchModel.sync_attempts + 1,
            last_sync_error=safe_error,
            last_attempted_at=datetime.now(UTC),
        ).where(TelemetrySyncBatchModel.batch_uid == batch_uid).execute()

    def status_counts(self) -> dict[str, int]:
        """Return a compact view of local synchronization backlog health."""
        return {
            "unbatched_samples": TelemetrySampleModel.select()
            .where(TelemetrySampleModel.sync_batch_uid.is_null(True))
            .count(),
            "pending_batches": TelemetrySyncBatchModel.select()
            .where(TelemetrySyncBatchModel.status == PENDING)
            .count(),
            "failed_batches": TelemetrySyncBatchModel.select()
            .where(TelemetrySyncBatchModel.status == FAILED)
            .count(),
            "synchronized_batches": TelemetrySyncBatchModel.select()
            .where(TelemetrySyncBatchModel.status == SYNCHRONIZED)
            .count(),
        }

    def _create_next_batch(self, batch_size: int) -> TelemetrySyncBatch | None:
        samples = list(
            TelemetrySampleModel.select()
            .where(TelemetrySampleModel.sync_batch_uid.is_null(True))
            .order_by(TelemetrySampleModel.id)
            .limit(batch_size)
        )
        if not samples:
            return None

        device_uid = samples[0].device_uid
        same_device_samples = [
            sample for sample in samples if sample.device_uid == device_uid
        ]
        batch_uid = str(uuid4())
        temperatures = [sample.freezer_temperature for sample in same_device_samples]
        humidities = [sample.ambient_humidity for sample in same_device_samples]
        with TelemetrySyncBatchModel._meta.database.atomic():
            row = TelemetrySyncBatchModel.create(
                batch_uid=batch_uid,
                device_uid=device_uid,
                sample_ids_json=json.dumps([sample.id for sample in same_device_samples]),
                min_temperature=min(temperatures),
                max_temperature=max(temperatures),
                avg_temperature=sum(temperatures) / len(temperatures),
                avg_humidity=sum(humidities) / len(humidities),
                sample_count=len(same_device_samples),
                recorded_at=max(sample.recorded_at for sample in same_device_samples),
                status=PENDING,
                created_at=datetime.now(UTC),
            )
            TelemetrySampleModel.update(sync_batch_uid=batch_uid).where(
                TelemetrySampleModel.id.in_(
                    [sample.id for sample in same_device_samples]
                )
            ).execute()
        return self._to_batch(row)

    @staticmethod
    def _to_batch(row: TelemetrySyncBatchModel) -> TelemetrySyncBatch:
        return TelemetrySyncBatch(
            batch_uid=row.batch_uid,
            device_uid=row.device_uid,
            sample_ids=tuple(json.loads(row.sample_ids_json)),
            min_temperature=row.min_temperature,
            max_temperature=row.max_temperature,
            avg_temperature=row.avg_temperature,
            avg_humidity=row.avg_humidity,
            sample_count=row.sample_count,
            recorded_at=row.recorded_at,
            status=row.status,
            sync_attempts=row.sync_attempts,
        )
