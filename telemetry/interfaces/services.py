"""Flask HTTP adapter for refrigeration telemetry ingestion."""

from datetime import datetime

from flask import current_app, jsonify, request
from flask_openapi3 import APIBlueprint
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shared.interfaces.openapi import (
    API_KEY_SECURITY,
    ErrorResponse,
    TELEMETRY_TAG,
    TelemetrySampleResponse,
    document_without_runtime_validation,
)
from telemetry.application.errors import DeviceAuthenticationFailed
from telemetry.domain.errors import TelemetryEventConflict


telemetry_api = APIBlueprint("telemetry_api", __name__, abp_tags=[TELEMETRY_TAG])


class TelemetrySampleRequest(BaseModel):
    """HTTP contract emitted by an ESP32 for one sensor-reading cycle."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    device_uid: str = Field(..., min_length=1, max_length=64)
    event_id: str = Field(..., min_length=1, max_length=128)
    freezer_temperature: float = Field(..., ge=-80, le=80)
    ambient_temperature: float = Field(..., ge=-80, le=80)
    ambient_humidity: float = Field(..., ge=0, le=100)
    interior_light_lux: float = Field(..., ge=0, le=500_000)
    door_open: bool
    humidity_critical: bool
    general_alert: bool
    recorded_at: datetime | None = None


@telemetry_api.post(
    "/api/v1/telemetry/samples",
    summary="Store an ESP32 sensor-reading cycle",
    security=API_KEY_SECURITY,
    responses={
        200: TelemetrySampleResponse,
        201: TelemetrySampleResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        409: ErrorResponse,
        415: ErrorResponse,
    },
)
@document_without_runtime_validation
def create_telemetry_sample(body: TelemetrySampleRequest = None):
    """Persist one authenticated ESP32 sample without duplicating retries."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    request_data = request.get_json(silent=True)
    if request_data is None:
        return jsonify({"error": "Invalid JSON request body"}), 400
    if isinstance(request_data, dict) and not request_data.get("device_uid"):
        return jsonify({"error": "Missing device_uid"}), 401

    try:
        sample_request = TelemetrySampleRequest.model_validate(request_data)
    except ValidationError:
        return jsonify({"error": "Invalid telemetry sample request"}), 400

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": "Missing X-API-Key"}), 401

    try:
        result = current_app.extensions["telemetry_service"].record_sample(
            sample_request.device_uid,
            sample_request.event_id,
            sample_request.freezer_temperature,
            sample_request.ambient_temperature,
            sample_request.ambient_humidity,
            sample_request.interior_light_lux,
            sample_request.door_open,
            sample_request.humidity_critical,
            sample_request.general_alert,
            sample_request.recorded_at,
            api_key,
        )
    except DeviceAuthenticationFailed:
        return jsonify({"error": "Invalid device_uid or API key"}), 401
    except TelemetryEventConflict:
        return jsonify({"error": "event_id has already been used for different telemetry"}), 409
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid telemetry sample data"}), 400

    sample = result.sample
    return jsonify(
        {
            "id": sample.id,
            "device_uid": sample.submitting_device.device_uid,
            "event_id": sample.event_id.value,
            "freezer_temperature": sample.freezer_temperature,
            "ambient_temperature": sample.ambient_temperature,
            "ambient_humidity": sample.ambient_humidity,
            "interior_light_lux": sample.interior_light_lux,
            "door_open": sample.door_open,
            "humidity_critical": sample.humidity_critical,
            "general_alert": sample.general_alert,
            "recorded_at": sample.recorded_at.value.isoformat().replace("+00:00", "Z"),
        }
    ), 201 if result.created else 200
