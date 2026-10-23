"""Peewee mapping for locally accepted refrigeration telemetry."""

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    CompositeKey,
    DateTimeField,
    DoubleField,
    Model,
)

from shared.infrastructure.database import db


class TelemetrySampleModel(Model):
    """SQLite row for one sample awaiting later cloud synchronization."""

    id = AutoField()
    device_uid = CharField(max_length=64)
    event_id = CharField(max_length=128)
    freezer_temperature = DoubleField()
    ambient_temperature = DoubleField()
    ambient_humidity = DoubleField()
    interior_light_lux = DoubleField()
    door_open = BooleanField()
    humidity_critical = BooleanField()
    general_alert = BooleanField()
    recorded_at = DateTimeField()
    received_at = DateTimeField()
    sync_batch_uid = CharField(max_length=64, null=True, index=True)

    class Meta:
        database = db
        table_name = "telemetry_samples"
        indexes = ((("device_uid", "event_id"), True),)
