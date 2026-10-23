"""Persistence contracts for telemetry."""

from dataclasses import dataclass
from typing import Protocol

from telemetry.domain.entities import TelemetrySample


@dataclass(frozen=True)
class TelemetrySaveResult:
    """Persisted sample and whether it was newly created."""

    sample: TelemetrySample
    created: bool


class TelemetryRepository(Protocol):
    """Persistence port for local telemetry samples."""

    def save_idempotently(self, sample: TelemetrySample) -> TelemetrySaveResult:
        """Persist a sample or return the existing equivalent retry."""
        ...
