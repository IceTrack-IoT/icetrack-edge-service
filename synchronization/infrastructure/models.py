"""Peewee mapping for batches waiting to reach the cloud backend."""

from peewee import (
    CharField,
    DateTimeField,
    DoubleField,
    IntegerField,
    Model,
    TextField,
)

from shared.infrastructure.database import db


class TelemetrySyncBatchModel(Model):
    """Durable aggregation batch whose samples are awaiting cloud delivery."""

    batch_uid = CharField(primary_key=True, max_length=64)
    device_uid = CharField(max_length=64, index=True)
    sample_ids_json = TextField()
    min_temperature = DoubleField()
    max_temperature = DoubleField()
    avg_temperature = DoubleField()
    avg_humidity = DoubleField()
    sample_count = IntegerField()
    recorded_at = DateTimeField()
    status = CharField(max_length=16, index=True)
    sync_attempts = IntegerField(default=0)
    last_sync_error = TextField(null=True)
    created_at = DateTimeField()
    last_attempted_at = DateTimeField(null=True)
    synchronized_at = DateTimeField(null=True)

    class Meta:
        database = db
        table_name = "telemetry_sync_batches"
