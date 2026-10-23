"""Domain errors specific to telemetry idempotency."""


class TelemetryEventConflict(ValueError):
    """Raised when one event ID is reused with different telemetry."""
