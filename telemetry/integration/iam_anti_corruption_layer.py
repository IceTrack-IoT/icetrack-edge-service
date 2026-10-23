"""Translate IAM authentication into Telemetry's local device concept."""

from iam.application.services import AuthApplicationService
from telemetry.domain.entities import SubmittingDevice


class IamAntiCorruptionLayer:
    """Prevent Telemetry from depending on IAM entities or repositories."""

    def __init__(self, iam_authentication_service: AuthApplicationService):
        self._iam_authentication_service = iam_authentication_service

    def authenticated_submitting_device(
        self, device_uid: str, api_key: str
    ) -> SubmittingDevice | None:
        """Return a local submitting-device value when IAM accepts credentials."""
        if not self._iam_authentication_service.authenticate(device_uid, api_key):
            return None
        return SubmittingDevice(device_uid)
