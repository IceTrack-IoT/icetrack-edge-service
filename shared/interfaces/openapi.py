"""Reusable OpenAPI metadata and response contracts for the Edge HTTP API."""

from pydantic import BaseModel, ConfigDict, Field

from flask_openapi3 import Tag


SYSTEM_TAG = Tag(name="System", description="Service health and readiness endpoints.")
IAM_TAG = Tag(name="IAM", description="Local ESP32 authentication at the Edge.")
TELEMETRY_TAG = Tag(
    name="Telemetry", description="Authenticated refrigeration sensor readings."
)
SYNCHRONIZATION_TAG = Tag(
    name="Synchronization", description="Durable outbox status and cloud delivery controls."
)

API_KEY_SECURITY = [{"EdgeApiKey": []}]
API_KEY_SECURITY_SCHEMES = {
    "EdgeApiKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key assigned to the ESP32/Edge device after pairing.",
    }
}


class ErrorResponse(BaseModel):
    """Common JSON error envelope returned by the Edge Service."""

    error: str


class StatusResponse(BaseModel):
    """Response returned when the Edge HTTP service is ready."""

    status: str = "ok"


class AuthenticationResponse(BaseModel):
    """Successful local authentication response."""

    device_uid: str
    authenticated: bool = True


class TelemetrySampleResponse(BaseModel):
    """A telemetry sample accepted by the local durable store."""

    id: int
    device_uid: str
    event_id: str
    freezer_temperature: float
    ambient_temperature: float
    ambient_humidity: float
    interior_light_lux: float
    door_open: bool
    humidity_critical: bool
    general_alert: bool
    recorded_at: str


class SynchronizationStatusResponse(BaseModel):
    """Summary counters for the local synchronization outbox."""

    unbatched_samples: int = Field(ge=0)
    pending_batches: int = Field(ge=0)
    failed_batches: int = Field(ge=0)
    synchronized_batches: int = Field(ge=0)


class SynchronizationAttemptResponse(BaseModel):
    """Result of one explicit cloud synchronization attempt."""

    model_config = ConfigDict(extra="forbid")

    outcome: str
    batch_uid: str | None = None
    sample_count: int = Field(ge=0)
    error: str | None = None


def document_without_runtime_validation(function):
    """Expose Pydantic models in OpenAPI while preserving legacy Flask validation.

    The endpoint implementations already return their established 400/401/415
    responses.  This marker avoids Flask-OpenAPI3 replacing them with 422 errors.
    """

    setattr(function, "__delay_validate_request__", True)
    return function
