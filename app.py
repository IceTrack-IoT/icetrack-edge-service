"""Flask application entry point for the IceTrack Edge Service."""

import atexit
from pathlib import Path

from flask import jsonify
from flask_openapi3 import Info, OpenAPI

from config import load_config
from iam.application.services import AuthApplicationService
from iam.infrastructure.repositories import DeviceRepository
from iam.interfaces.services import iam_api
from shared.interfaces.openapi import (
    API_KEY_SECURITY_SCHEMES,
    SYSTEM_TAG,
    StatusResponse,
)
from shared.infrastructure.database import configure_database, db, init_db
from synchronization.application.services import TelemetrySynchronizationService
from synchronization.application.worker import SynchronizationWorker
from synchronization.infrastructure.cloud_gateway import IceTrackCloudGateway
from synchronization.infrastructure.repositories import SynchronizationRepository
from synchronization.interfaces.services import synchronization_api
from telemetry.application.services import TelemetryApplicationService
from telemetry.integration.iam_anti_corruption_layer import IamAntiCorruptionLayer
from telemetry.interfaces.services import telemetry_api


def create_app() -> OpenAPI:
    """Create the application and prepare its shared infrastructure."""
    app = OpenAPI(
        __name__,
        info=Info(
            title="IceTrack Edge Service API",
            version="1.0.0",
            description=(
                "Local HTTP API between the ESP32, the Edge Service, and "
                "IceTrack cloud synchronization."
            ),
        ),
        security_schemes=API_KEY_SECURITY_SCHEMES,
        doc_prefix="/docs",
        doc_url="/openapi.json",
    )
    app.config.from_mapping(load_config(Path(__file__).resolve().parent))
    configure_database(app.config["DATABASE_PATH"])
    init_db()
    device_repository = DeviceRepository()
    device_repository.migrate_schema()
    synchronization_repository = SynchronizationRepository()
    synchronization_repository.migrate_schema()
    iam_authentication_service = AuthApplicationService(device_repository)
    app.extensions["iam_authentication_service"] = iam_authentication_service
    app.extensions["telemetry_service"] = TelemetryApplicationService(
        IamAntiCorruptionLayer(iam_authentication_service)
    )
    synchronization_service = TelemetrySynchronizationService(
        synchronization_repository,
        IceTrackCloudGateway(
            app.config["CLOUD_API_BASE_URL"],
            app.config["EDGE_DEVICE_API_KEY"],
            app.config["SYNC_TIMEOUT_SECONDS"],
        ),
        app.config["SYNC_BATCH_SIZE"],
        app.config["SYNC_ENABLED"],
    )
    app.extensions["telemetry_synchronization_service"] = synchronization_service
    app.register_api(iam_api)
    app.register_api(telemetry_api)
    app.register_api(synchronization_api)

    if app.config["SEED_EDGE_DEVICE"]:
        iam_authentication_service.get_or_create_seeded_device(
            app.config["EDGE_DEVICE_UID"],
            app.config["EDGE_DEVICE_API_KEY"],
        )

    @app.get(
        "/api/v1/status",
        tags=[SYSTEM_TAG],
        summary="Check Edge Service readiness",
        responses={200: StatusResponse},
    )
    def status() -> tuple[dict[str, str], int]:
        """Report that the Edge HTTP service is ready to receive requests."""
        return jsonify({"status": "ok"}), 200

    @app.teardown_appcontext
    def close_database(_exception: BaseException | None) -> None:
        if not db.is_closed():
            db.close()

    return app


app = create_app()


def start_background_services(application: OpenAPI) -> None:
    """Start the single Edge-process worker after application composition."""
    if not application.config["SYNC_ENABLED"]:
        return
    if "telemetry_synchronization_worker" in application.extensions:
        return
    synchronization_worker = SynchronizationWorker(
        application.extensions["telemetry_synchronization_service"],
        application.config["SYNC_INTERVAL_SECONDS"],
    )
    synchronization_worker.start()
    application.extensions["telemetry_synchronization_worker"] = synchronization_worker
    atexit.register(synchronization_worker.stop)


start_background_services(app)


if __name__ == "__main__":
    if app.config["APP_ENV"] != "development":
        raise RuntimeError("The built-in Flask server is development-only")
    app.run(
        debug=app.config["DEBUG"],
        host=app.config["HOST"],
        port=app.config["PORT"],
        use_reloader=False,
    )
