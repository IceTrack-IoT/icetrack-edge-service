"""HTTP adapter that connects the local Edge outbox to IceTrack cloud APIs."""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from synchronization.infrastructure.repositories import TelemetrySyncBatch


class CloudRequestError(RuntimeError):
    """Raised when the cloud cannot authenticate a device or accept a batch."""


@dataclass(frozen=True)
class AuthenticatedCloudDevice:
    """Cloud identities resolved from a valid Edge device credential."""

    device_id: int
    equipment_id: int


class IceTrackCloudGateway:
    """Call Device Management and Monitoring through their HTTP contracts."""

    def __init__(
        self,
        cloud_api_base_url: str | None,
        device_api_key: str | None,
        timeout_seconds: int,
    ):
        self._cloud_api_base_url = cloud_api_base_url
        self._device_api_key = device_api_key
        self._timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        """Whether the Edge has the endpoint and key required for cloud delivery."""
        return bool(self._cloud_api_base_url and self._device_api_key)

    def authenticate_device(self, device_uid: str) -> AuthenticatedCloudDevice:
        """Resolve the cloud device and equipment IDs for an enrolled ESP32."""
        response = self._post(
            "/internal/v1/devices/authenticate", {"device_uid": device_uid}
        )
        try:
            return AuthenticatedCloudDevice(
                device_id=int(response["device_id"]),
                equipment_id=int(response["equipment_id"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise CloudRequestError(
                "Cloud device authentication response is incomplete"
            ) from error

    def submit_batch(
        self, batch: TelemetrySyncBatch, cloud_device: AuthenticatedCloudDevice
    ) -> None:
        """Send one already-persisted batch to the Monitoring bounded context."""
        self._post(
            "/api/v1/telemetry",
            {
                "reading_uid": batch.batch_uid,
                "equipment_id": cloud_device.equipment_id,
                "device_id": cloud_device.device_id,
                "min_temperature": batch.min_temperature,
                "max_temperature": batch.max_temperature,
                "avg_temperature": batch.avg_temperature,
                "humidity": batch.avg_humidity,
                "sample_count": batch.sample_count,
                "recorded_at": batch.recorded_at.isoformat().replace("+00:00", "Z"),
            },
        )

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        if not self.is_configured:
            raise CloudRequestError("Cloud synchronization is not configured")
        request = Request(
            self._cloud_api_base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self._device_api_key or "",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            raise CloudRequestError(
                "Cloud request failed with HTTP status " + str(error.code)
            ) from error
        except URLError as error:
            raise CloudRequestError("Cloud request could not be completed") from error
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError as error:
            raise CloudRequestError("Cloud response is not valid JSON") from error
        if not isinstance(parsed, dict):
            raise CloudRequestError("Cloud response must be a JSON object")
        return parsed
