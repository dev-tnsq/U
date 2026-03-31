"""Parser for plaintext WhatsApp chat exports."""

from __future__ import annotations

import re
from collections import OrderedDict

from .models import NormalizedRecord

_WHATSAPP_LINE_RE = re.compile(
    r"^(?P<ts>\d{1,2}/\d{1,2}/\d{2,4},\s+\d{1,2}:\d{2}\s+[AP]M)\s+-\s+(?P<sender>[^:]+):\s(?P<message>.*)$"
)
_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_-]+)")


def _extract_tags(content: str) -> list[str]:
    tags = OrderedDict()
    for match in _HASHTAG_RE.finditer(content):
        tags[match.group(1).lower()] = None
    return list(tags.keys())


def parse_whatsapp_export(text: str) -> list[NormalizedRecord]:
    """Parse a WhatsApp plaintext export into normalized records."""
    records: list[NormalizedRecord] = []
    current: dict[str, str] | None = None
    ordinal = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        matched = _WHATSAPP_LINE_RE.match(line)
        if matched:
            if current is not None:
                ordinal += 1
                records.append(
                    _build_record(
                        ordinal=ordinal,
                        timestamp=current["timestamp"],
                        sender=current["sender"],
                        message=current["message"],
                    )
                )
            current = {
                "timestamp": matched.group("ts"),
                "sender": matched.group("sender").strip(),
                "message": matched.group("message").strip(),
            }
            continue

        if current is not None:
            continuation = line.strip()
            if continuation:
                current["message"] = f"{current['message']}\n{continuation}"

    if current is not None:
        ordinal += 1
        records.append(
            _build_record(
                ordinal=ordinal,
                timestamp=current["timestamp"],
                sender=current["sender"],
                message=current["message"],
            )
        )

    return records


def _build_record(ordinal: int, timestamp: str, sender: str, message: str) -> NormalizedRecord:
    tags = _extract_tags(message)
    source_id = f"wa:{timestamp}|{sender}|{ordinal}"
    return NormalizedRecord(
        source="whatsapp",
        source_id=source_id,
        content=message,
        tags=tags,
        metadata={
            "timestamp": timestamp,
            "sender": sender,
            "ordinal": ordinal,
        },
    )
