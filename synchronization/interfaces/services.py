"""Local HTTP controls for observing and triggering cloud synchronization."""

from flask import current_app, jsonify
from flask_openapi3 import APIBlueprint

from shared.interfaces.openapi import (
    ErrorResponse,
    SYNCHRONIZATION_TAG,
    SynchronizationAttemptResponse,
    SynchronizationStatusResponse,
)


synchronization_api = APIBlueprint(
    "synchronization_api", __name__, abp_tags=[SYNCHRONIZATION_TAG]
)


@synchronization_api.get(
    "/api/v1/synchronization/status",
    summary="Inspect the local telemetry outbox",
    responses={200: SynchronizationStatusResponse},
)
def synchronization_status():
    """Report the durable outbox backlog without sending data to the cloud."""
    service = current_app.extensions["telemetry_synchronization_service"]
    return jsonify(service.status_counts()), 200


@synchronization_api.post(
    "/api/v1/synchronization/attempts",
    summary="Attempt one cloud synchronization",
    responses={
        200: SynchronizationAttemptResponse,
        202: SynchronizationAttemptResponse,
        503: SynchronizationAttemptResponse,
        500: ErrorResponse,
    },
)
def synchronize_once():
    """Attempt one cloud delivery; intended for local scheduler integration."""
    service = current_app.extensions["telemetry_synchronization_service"]
    result = service.synchronize_once()
    body = {
        "outcome": result.outcome,
        "batch_uid": result.batch_uid,
        "sample_count": result.sample_count,
        "error": result.error,
    }
    if result.outcome in {"disabled", "not_configured"}:
        return jsonify(body), 503
    if result.outcome == "failed":
        return jsonify(body), 202
    return jsonify(body), 200
