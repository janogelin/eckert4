import io
import avro.schema
from avro.datafile import DataFileWriter, DataFileReader
from avro.io import DatumWriter, DatumReader
from app.models.schemas import ANCHOR_URL_AVRO_SCHEMA

import pytest

def test_anchor_url_avro_roundtrip():
    """
    Test Avro serialization and deserialization for anchor URL records using the ANCHOR_URL_AVRO_SCHEMA.
    """
    schema = avro.schema.parse(ANCHOR_URL_AVRO_SCHEMA)
    record = {
        'normalized_url': 'https://www.svt.se',
        'source_url': 'https://source.svt.se',
        'timestamp': '2024-01-01T00:00:00Z'
    }
    buf = io.BytesIO()
    writer = DataFileWriter(buf, DatumWriter(), schema)
    writer.append(record)
    writer.flush()
    avro_bytes = buf.getvalue()
    writer.close()
    reader = DataFileReader(io.BytesIO(avro_bytes), DatumReader())
    records = list(reader)
    reader.close()
    assert len(records) == 1
    assert records[0] == record 