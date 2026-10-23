"""Application-level errors for telemetry use cases."""


class DeviceAuthenticationFailed(Exception):
    """Raised when IAM rejects the ESP32 that submitted telemetry."""
