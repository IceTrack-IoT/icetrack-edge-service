"""Peewee repository implementation for idempotent telemetry persistence."""

import peewee

from telemetry.domain.entities import SubmittingDevice, TelemetrySample
from telemetry.domain.errors import TelemetryEventConflict
from telemetry.domain.repositories import TelemetrySaveResult
from telemetry.domain.value_objects import RecordedAt, TelemetryEventId
from telemetry.infrastructure.models import TelemetrySampleModel


class TelemetryRepository:
    """Store samples locally and enforce device-scoped event idempotency."""

    def save_idempotently(self, sample: TelemetrySample) -> TelemetrySaveResult:
        """Insert a sample or resolve a semantically identical retry."""
        existing = self._find_by_event(sample.submitting_device.device_uid, sample.event_id.value)
        if existing is not None:
            if existing.has_same_payload(sample):
                return TelemetrySaveResult(existing, created=False)
            raise TelemetryEventConflict(
                "Telemetry event ID has already been used for different data"
            )

        try:
            with TelemetrySampleModel._meta.database.atomic():
                row = TelemetrySampleModel.create(
                    device_uid=sample.submitting_device.device_uid,
                    event_id=sample.event_id.value,
                    freezer_temperature=sample.freezer_temperature,
                    ambient_temperature=sample.ambient_temperature,
                    ambient_humidity=sample.ambient_humidity,
                    interior_light_lux=sample.interior_light_lux,
                    door_open=sample.door_open,
                    humidity_critical=sample.humidity_critical,
                    general_alert=sample.general_alert,
                    recorded_at=sample.recorded_at.value,
                    received_at=sample.received_at,
                )
        except peewee.IntegrityError:
            existing = self._find_by_event(
                sample.submitting_device.device_uid, sample.event_id.value
            )
            if existing is not None and existing.has_same_payload(sample):
                return TelemetrySaveResult(existing, created=False)
            raise TelemetryEventConflict(
                "Telemetry event ID has already been used for different data"
            )
        return TelemetrySaveResult(self._to_entity(row), created=True)

    @staticmethod
    def _find_by_event(device_uid: str, event_id: str) -> TelemetrySample | None:
        row = TelemetrySampleModel.get_or_none(
            (TelemetrySampleModel.device_uid == device_uid)
            & (TelemetrySampleModel.event_id == event_id)
        )
        return TelemetryRepository._to_entity(row) if row is not None else None

    @staticmethod
    def _to_entity(row: TelemetrySampleModel) -> TelemetrySample:
        return TelemetrySample(
            id=row.id,
            submitting_device=SubmittingDevice(row.device_uid),
            event_id=TelemetryEventId(row.event_id),
            freezer_temperature=row.freezer_temperature,
            ambient_temperature=row.ambient_temperature,
            ambient_humidity=row.ambient_humidity,
            interior_light_lux=row.interior_light_lux,
            door_open=row.door_open,
            humidity_critical=row.humidity_critical,
            general_alert=row.general_alert,
            recorded_at=RecordedAt(row.recorded_at),
            received_at=row.received_at,
        )
