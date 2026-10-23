"""IAM aggregate roots."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from iam.domain.credentials import ApiCredential


@dataclass(frozen=True)
class Device:
    """Locally enrolled ESP32 with credential and revocation state."""

    device_uid: str
    credential: ApiCredential
    created_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.device_uid, str) or not self.device_uid.strip():
            raise ValueError("Device UID cannot be empty")
        if not isinstance(self.credential, ApiCredential):
            raise TypeError("Device requires an API credential verifier")
        object.__setattr__(self, "device_uid", self.device_uid.strip())
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "creation"))
        if self.revoked_at is not None:
            revoked_at = _utc_datetime(self.revoked_at, "revocation")
            if revoked_at < self.created_at:
                raise ValueError("Revocation cannot predate device registration")
            object.__setattr__(self, "revoked_at", revoked_at)

    @classmethod
    def enroll(
        cls, device_uid: str, api_key: str, created_at: datetime | None = None
    ) -> "Device":
        """Enroll a device and protect its credential before persistence."""
        return cls(device_uid, ApiCredential.create(api_key), created_at or datetime.now(UTC))

    def authenticate(self, api_key: str) -> bool:
        """Authenticate only active devices with matching credentials."""
        return self.revoked_at is None and self.credential.matches(api_key)

    def revoke(self, at: datetime | None = None) -> "Device":
        """Return a revoked copy of this aggregate."""
        if self.revoked_at is not None:
            raise ValueError("Device is already revoked")
        return replace(self, revoked_at=at or datetime.now(UTC))


def _utc_datetime(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"Device {label} time must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Device {label} time must include a timezone")
    return value.astimezone(UTC)
