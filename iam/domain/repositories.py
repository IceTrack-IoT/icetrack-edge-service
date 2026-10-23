"""Persistence contract for IAM device aggregates."""

from typing import Protocol

from iam.domain.entities import Device


class DeviceRepository(Protocol):
    """Repository abstraction owned by the IAM application layer."""

    def find_by_device_uid(self, device_uid: str) -> Device | None:
        """Retrieve one locally enrolled device."""
        ...

    def save(self, device: Device) -> Device:
        """Persist one device aggregate."""
        ...
