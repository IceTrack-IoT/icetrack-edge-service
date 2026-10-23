"""Peewee mapping for locally enrolled ESP32 devices."""

from peewee import CharField, DateTimeField, Model

from shared.infrastructure.database import db


class EdgeDeviceModel(Model):
    """SQLite representation of a device credential verifier and lifecycle."""

    device_uid = CharField(primary_key=True, max_length=64)
    credential_verifier = CharField(column_name="api_key_verifier", max_length=255)
    created_at = DateTimeField()
    revoked_at = DateTimeField(null=True)

    class Meta:
        database = db
        table_name = "edge_devices"
