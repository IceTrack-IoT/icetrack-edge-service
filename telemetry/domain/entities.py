"""Telemetry aggregate and local device concept."""

from dataclasses import dataclass
from datetime import UTC, datetime

from telemetry.domain.value_objects import RecordedAt, TelemetryEventId


@dataclass(frozen=True)
class SubmittingDevice:
    """Telemetry's local representation of an authenticated ESP32."""

    device_uid: str

    def __post_init__(self) -> None:
        if not isinstance(self.device_uid, str) or not self.device_uid.strip():
            raise ValueError("Submitting device UID cannot be empty")
        object.__setattr__(self, "device_uid", self.device_uid.strip())


@dataclass(frozen=True)
class TelemetrySample:
    """One authenticated refrigeration measurement accepted by the Edge."""

    id: int | None
    submitting_device: SubmittingDevice
    event_id: TelemetryEventId
    freezer_temperature: float
    ambient_temperature: float
    ambient_humidity: float
    interior_light_lux: float
    door_open: bool
    humidity_critical: bool
    general_alert: bool
    recorded_at: RecordedAt
    received_at: datetime

    def __post_init__(self) -> None:
        if self.id is not None and (not isinstance(self.id, int) or self.id <= 0):
            raise ValueError("Telemetry sample ID must be a positive integer")
        if not isinstance(self.submitting_device, SubmittingDevice):
            raise TypeError("Telemetry sample requires an authenticated device")
        if not isinstance(self.event_id, TelemetryEventId):
            raise TypeError("Telemetry sample requires an event ID")
        _validate_number("Freezer temperature", self.freezer_temperature, -80.0, 80.0)
        _validate_number("Ambient temperature", self.ambient_temperature, -80.0, 80.0)
        _validate_number("Ambient humidity", self.ambient_humidity, 0.0, 100.0)
        _validate_number("Interior light", self.interior_light_lux, 0.0, 500_000.0)
        for label, value in (
            ("Door-open flag", self.door_open),
            ("Humidity-critical flag", self.humidity_critical),
            ("General-alert flag", self.general_alert),
        ):
            if not isinstance(value, bool):
                raise TypeError(f"{label} must be boolean")
        if not isinstance(self.recorded_at, RecordedAt):
            raise TypeError("Telemetry sample requires a recorded timestamp")
        if not isinstance(self.received_at, datetime):
            raise TypeError("Received time must be a datetime")
        if self.received_at.tzinfo is None or self.received_at.utcoffset() is None:
            raise ValueError("Received time must include a timezone")
        object.__setattr__(self, "received_at", self.received_at.astimezone(UTC))

    @classmethod
    def record(
        cls,
        submitting_device: SubmittingDevice,
        event_id: str,
        freezer_temperature: float,
        ambient_temperature: float,
        ambient_humidity: float,
        interior_light_lux: float,
        door_open: bool,
        humidity_critical: bool,
        general_alert: bool,
        recorded_at: datetime | None,
    ) -> "TelemetrySample":
        """Create a valid local sample, assigning Edge UTC time when absent."""
        observed_at = recorded_at or datetime.now(UTC)
        return cls(
            id=None,
            submitting_device=submitting_device,
            event_id=TelemetryEventId(event_id),
            freezer_temperature=float(freezer_temperature),
            ambient_temperature=float(ambient_temperature),
            ambient_humidity=float(ambient_humidity),
            interior_light_lux=float(interior_light_lux),
            door_open=door_open,
            humidity_critical=humidity_critical,
            general_alert=general_alert,
            recorded_at=RecordedAt(observed_at),
            received_at=datetime.now(UTC),
        )

    def has_same_payload(self, other: "TelemetrySample") -> bool:
        """Return whether a retry carries the exact original measurement."""
        return (
            self.submitting_device == other.submitting_device
            and self.event_id == other.event_id
            and self.freezer_temperature == other.freezer_temperature
            and self.ambient_temperature == other.ambient_temperature
            and self.ambient_humidity == other.ambient_humidity
            and self.interior_light_lux == other.interior_light_lux
            and self.door_open == other.door_open
            and self.humidity_critical == other.humidity_critical
            and self.general_alert == other.general_alert
            and self.recorded_at == other.recorded_at
        )


def _validate_number(label: str, value: float, lower: float, upper: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    if value != value or value in {float("inf"), float("-inf")}:
        raise ValueError(f"{label} must be finite")
    if not lower <= float(value) <= upper:
        raise ValueError(f"{label} must be between {lower} and {upper}")
