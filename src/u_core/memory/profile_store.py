"""Profile memory access with lightweight versioning semantics."""

from __future__ import annotations

import json
from typing import Any

from .models import Profile
from .store import SQLiteStore, utc_now_iso


class ProfileStore:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def load_profile(self, profile_id: str = "default") -> Profile | None:
        row = self.store._conn.execute(
            "SELECT * FROM profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        if row is None:
            return None
        return Profile(
            profile_id=row["profile_id"],
            data=json.loads(row["profile_json"]),
            version=row["version"],
            updated_at=row["updated_at"],
        )

    def update_profile(self, data: dict[str, Any], profile_id: str = "default") -> Profile:
        existing = self.load_profile(profile_id)
        now = utc_now_iso()
        version = 1 if existing is None else existing.version + 1
        with self.store._conn:
            self.store._conn.execute(
                """
                INSERT INTO profiles(profile_id, profile_json, version, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (profile_id, json.dumps(data, separators=(",", ":")), version, now),
            )
        return Profile(profile_id=profile_id, data=data, version=version, updated_at=now)
