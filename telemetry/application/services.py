"""Application use case for accepting refrigeration telemetry."""

from datetime import datetime

from telemetry.application.errors import DeviceAuthenticationFailed
from telemetry.domain.entities import TelemetrySample
from telemetry.domain.repositories import TelemetryRepository, TelemetrySaveResult
from telemetry.infrastructure.repositories import TelemetryRepository as TelemetryRepositoryImpl
from telemetry.integration.iam_anti_corruption_layer import IamAntiCorruptionLayer


class TelemetryApplicationService:
    """Authenticate, validate and persist one ESP32 measurement."""

    def __init__(
        self,
        iam_anti_corruption_layer: IamAntiCorruptionLayer,
        telemetry_repository: TelemetryRepository | None = None,
    ):
        self._telemetry_repository = telemetry_repository or TelemetryRepositoryImpl()
        self._iam_anti_corruption_layer = iam_anti_corruption_layer

    def record_sample(
        self,
        device_uid: str,
        event_id: str,
        freezer_temperature: float,
        ambient_temperature: float,
        ambient_humidity: float,
        interior_light_lux: float,
        door_open: bool,
        humidity_critical: bool,
        general_alert: bool,
        recorded_at: datetime | None,
        api_key: str,
    ) -> TelemetrySaveResult:
        """Accept one authenticated measurement through the domain aggregate."""
        device = self._iam_anti_corruption_layer.authenticated_submitting_device(
            device_uid, api_key
        )
        if device is None:
            raise DeviceAuthenticationFailed
        sample = TelemetrySample.record(
            device,
            event_id,
            freezer_temperature,
            ambient_temperature,
            ambient_humidity,
            interior_light_lux,
            door_open,
            humidity_critical,
            general_alert,
            recorded_at,
        )
        return self._telemetry_repository.save_idempotently(sample)
