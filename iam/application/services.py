"""Application services for local Edge device authentication."""

from iam.domain.entities import Device
from iam.domain.repositories import DeviceRepository
from iam.infrastructure.repositories import DeviceRepository as DeviceRepositoryImpl


class AuthApplicationService:
    """Coordinate device enrollment and authentication use cases."""

    def __init__(self, device_repository: DeviceRepository | None = None):
        self.device_repository = device_repository or DeviceRepositoryImpl()

    def authenticate(self, device_uid: str, api_key: str) -> bool:
        """Return whether this active local device accepts the supplied key."""
        device = self.device_repository.find_by_device_uid(device_uid)
        return device is not None and device.authenticate(api_key)

    def enroll_device(self, device_uid: str, api_key: str) -> Device:
        """Create a device enrollment unless its UID already exists."""
        if self.device_repository.find_by_device_uid(device_uid) is not None:
            raise ValueError("Device is already enrolled")
        return self.device_repository.save(Device.enroll(device_uid, api_key))

    def revoke_device(self, device_uid: str) -> Device:
        """Revoke a locally enrolled device."""
        device = self.device_repository.find_by_device_uid(device_uid)
        if device is None:
            raise ValueError("Device not found")
        return self.device_repository.save(device.revoke())

    def get_or_create_seeded_device(self, device_uid: str, api_key: str | None) -> Device:
        """Create the local development enrollment when explicitly configured."""
        if api_key is None:
            raise ValueError("Seed device API key is required")
        repository = self.device_repository
        if not isinstance(repository, DeviceRepositoryImpl):
            existing = repository.find_by_device_uid(device_uid)
            return existing or repository.save(Device.enroll(device_uid, api_key))
        return repository.get_or_create_seeded_device(device_uid, api_key)
