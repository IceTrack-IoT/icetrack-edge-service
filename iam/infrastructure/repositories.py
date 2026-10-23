"""Peewee repository implementation for IAM devices."""

import peewee

from iam.domain.credentials import ApiCredential
from iam.domain.entities import Device
from iam.infrastructure.models import EdgeDeviceModel


class DeviceRepository:
    """Persist and reconstruct locally enrolled device aggregates."""

    def migrate_schema(self) -> None:
        """Validate the current schema's credential data after bootstrap."""
        for row in EdgeDeviceModel.select():
            ApiCredential.from_encoded(row.credential_verifier)

    def find_by_device_uid(self, device_uid: str) -> Device | None:
        """Load a device without leaking ORM objects into the domain."""
        if not isinstance(device_uid, str) or not device_uid.strip():
            return None
        try:
            row = EdgeDeviceModel.get(EdgeDeviceModel.device_uid == device_uid.strip())
        except peewee.DoesNotExist:
            return None
        return self._to_entity(row)

    def save(self, device: Device) -> Device:
        """Insert or update a device's protected credential and lifecycle state."""
        values = {
            "credential_verifier": device.credential.encode(),
            "created_at": device.created_at,
            "revoked_at": device.revoked_at,
        }
        with EdgeDeviceModel._meta.database.atomic():
            row = EdgeDeviceModel.get_or_none(
                EdgeDeviceModel.device_uid == device.device_uid
            )
            if row is None:
                EdgeDeviceModel.create(device_uid=device.device_uid, **values)
            else:
                EdgeDeviceModel.update(**values).where(
                    EdgeDeviceModel.device_uid == device.device_uid
                ).execute()
        return device

    def get_or_create_seeded_device(self, device_uid: str, api_key: str) -> Device:
        """Create the explicit development device only when it does not exist."""
        existing = self.find_by_device_uid(device_uid)
        if existing is not None:
            return existing
        return self.save(Device.enroll(device_uid, api_key))

    @staticmethod
    def _to_entity(row: EdgeDeviceModel) -> Device:
        return Device(
            row.device_uid,
            ApiCredential.from_encoded(row.credential_verifier),
            row.created_at,
            row.revoked_at,
        )
