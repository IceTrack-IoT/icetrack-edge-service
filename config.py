"""Environment-specific configuration for the IceTrack Edge Service."""

import os
from pathlib import Path
from typing import TypedDict

from dotenv import dotenv_values


class AppConfig(TypedDict):
    """Settings required to start the Edge Service."""

    APP_ENV: str
    DEBUG: bool
    DATABASE_PATH: str
    SEED_EDGE_DEVICE: bool
    EDGE_DEVICE_UID: str
    EDGE_DEVICE_API_KEY: str | None
    CLOUD_API_BASE_URL: str | None
    SYNC_ENABLED: bool
    SYNC_INTERVAL_SECONDS: int
    SYNC_BATCH_SIZE: int
    SYNC_TIMEOUT_SECONDS: int
    HOST: str
    PORT: int


def load_config(project_root: Path) -> AppConfig:
    """Load the selected environment file and then apply process overrides."""
    environment_name = os.getenv("APP_ENV", "development").strip().lower()
    if environment_name not in {"development", "production"}:
        raise ValueError("APP_ENV must be 'development' or 'production'")

    values = {
        **{
            key: value
            for key, value in dotenv_values(project_root / f".env.{environment_name}").items()
            if value is not None
        },
        **os.environ,
    }
    configured_environment = _required(values, "APP_ENV").strip().lower()
    if configured_environment != environment_name:
        raise ValueError(
            f"APP_ENV in .env.{environment_name} must be '{environment_name}'"
        )

    debug = _as_bool("DEBUG", _required(values, "DEBUG"))
    if environment_name == "production" and debug:
        raise ValueError("DEBUG must be false in production")

    seed_edge_device = _as_bool(
        "SEED_EDGE_DEVICE", _required(values, "SEED_EDGE_DEVICE")
    )
    if environment_name == "production" and seed_edge_device:
        raise ValueError("SEED_EDGE_DEVICE must be false in production")

    database_path = _required(values, "DATABASE_PATH").strip()
    if not database_path:
        raise ValueError("DATABASE_PATH cannot be empty")
    database = Path(database_path).expanduser()
    if not database.is_absolute():
        database = project_root / database

    try:
        port = int(_required(values, "PORT"))
    except ValueError as error:
        raise ValueError("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")

    host = _required(values, "HOST").strip()
    if not host:
        raise ValueError("HOST cannot be empty")

    edge_device_uid = _required(values, "EDGE_DEVICE_UID").strip()
    edge_device_api_key = values.get("EDGE_DEVICE_API_KEY", "").strip() or None
    cloud_api_base_url = values.get("CLOUD_API_BASE_URL", "").strip().rstrip("/") or None
    sync_enabled = _as_bool("SYNC_ENABLED", _required(values, "SYNC_ENABLED"))
    sync_interval_seconds = _positive_int(
        "SYNC_INTERVAL_SECONDS", _required(values, "SYNC_INTERVAL_SECONDS")
    )
    sync_batch_size = _positive_int("SYNC_BATCH_SIZE", _required(values, "SYNC_BATCH_SIZE"))
    sync_timeout_seconds = _positive_int(
        "SYNC_TIMEOUT_SECONDS", _required(values, "SYNC_TIMEOUT_SECONDS")
    )
    if seed_edge_device and not edge_device_uid:
        raise ValueError("EDGE_DEVICE_UID cannot be empty when seeding is enabled")
    if seed_edge_device and not edge_device_api_key:
        raise ValueError("EDGE_DEVICE_API_KEY is required when seeding is enabled")
    if sync_enabled and not cloud_api_base_url:
        raise ValueError("CLOUD_API_BASE_URL is required when synchronization is enabled")
    if sync_enabled and not edge_device_api_key:
        raise ValueError("EDGE_DEVICE_API_KEY is required when synchronization is enabled")

    return {
        "APP_ENV": environment_name,
        "DEBUG": debug,
        "DATABASE_PATH": str(database),
        "SEED_EDGE_DEVICE": seed_edge_device,
        "EDGE_DEVICE_UID": edge_device_uid,
        "EDGE_DEVICE_API_KEY": edge_device_api_key,
        "CLOUD_API_BASE_URL": cloud_api_base_url,
        "SYNC_ENABLED": sync_enabled,
        "SYNC_INTERVAL_SECONDS": sync_interval_seconds,
        "SYNC_BATCH_SIZE": sync_batch_size,
        "SYNC_TIMEOUT_SECONDS": sync_timeout_seconds,
        "HOST": host,
        "PORT": port,
    }


def _as_bool(name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _required(values: dict[str, str], name: str) -> str:
    try:
        return values[name]
    except KeyError as error:
        raise ValueError(f"{name} must be set in the selected dotenv file or environment") from error


def _positive_int(name: str, value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed
