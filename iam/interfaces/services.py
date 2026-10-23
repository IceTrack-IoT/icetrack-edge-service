"""Flask adapter for local Edge device authentication."""

from flask import current_app, jsonify, request
from flask_openapi3 import APIBlueprint
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shared.interfaces.openapi import (
    API_KEY_SECURITY,
    AuthenticationResponse,
    ErrorResponse,
    IAM_TAG,
    document_without_runtime_validation,
)


iam_api = APIBlueprint("iam_api", __name__, abp_tags=[IAM_TAG])


class AuthenticationRequest(BaseModel):
    """Identity of the ESP32 requesting local Edge access."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    device_uid: str = Field(..., min_length=1, max_length=64)


@iam_api.post(
    "/api/v1/iam/authentications",
    summary="Authenticate an ESP32 locally",
    security=API_KEY_SECURITY,
    responses={200: AuthenticationResponse, 400: ErrorResponse, 401: ErrorResponse, 415: ErrorResponse},
)
@document_without_runtime_validation
def authenticate_device(body: AuthenticationRequest = None):
    """Authenticate an ESP32 through its UID and X-API-Key header."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    request_data = request.get_json(silent=True)
    if request_data is None:
        return jsonify({"error": "Invalid JSON request body"}), 400
    try:
        authentication_request = AuthenticationRequest.model_validate(request_data)
    except ValidationError:
        return jsonify({"error": "Invalid authentication request"}), 400

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": "Missing X-API-Key"}), 401

    service = current_app.extensions["iam_authentication_service"]
    if not service.authenticate(authentication_request.device_uid, api_key):
        return jsonify({"error": "Invalid device_uid or API key"}), 401

    return jsonify(
        {"device_uid": authentication_request.device_uid, "authenticated": True}
    ), 200
