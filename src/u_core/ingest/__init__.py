"""Local deterministic parsers for ingestion inputs."""

from .local_notes_parser import parse_local_notes
from .models import NormalizedRecord
from .service import ingest_records, ingest_text_with_parser
from .telegram_parser import parse_telegram_export
from .whatsapp_parser import parse_whatsapp_export

__all__ = [
    "NormalizedRecord",
    "ingest_records",
    "ingest_text_with_parser",
    "parse_local_notes",
    "parse_telegram_export",
    "parse_whatsapp_export",
]
