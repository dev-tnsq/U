"""Parser for local plaintext or markdown note content."""

from __future__ import annotations

import re
from collections import OrderedDict

from .models import NormalizedRecord

_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_-]+)")


def _extract_tags(content: str) -> list[str]:
    tags = OrderedDict()
    for match in _HASHTAG_RE.finditer(content):
        tags[match.group(1).lower()] = None
    return list(tags.keys())


def parse_local_notes(text: str, *, note_id_prefix: str = "note") -> list[NormalizedRecord]:
    """Parse note lines into normalized records.

    The parser treats each non-empty line as one note entry and keeps original
    content intact except for leading markdown bullet markers.
    """
    records: list[NormalizedRecord] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        content = stripped
        if content.startswith("- ") or content.startswith("* "):
            content = content[2:].strip()

        if not content:
            continue

        tags = _extract_tags(content)
        source_id = f"{note_id_prefix}:{line_number}"
        records.append(
            NormalizedRecord(
                source="local_notes",
                source_id=source_id,
                content=content,
                tags=tags,
                metadata={"line_number": line_number},
            )
        )

    return records
