from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BotConfig:
    bot_role: str
    updated_at: str


class ConfigStore:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        os.makedirs(os.path.dirname(sqlite_path) or ".", exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    bot_role TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur = conn.execute("SELECT bot_role, updated_at FROM config WHERE id = 1")
            row = cur.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO config (id, bot_role, updated_at) VALUES (1, ?, ?)",
                    (
                        "あなたは親切で簡潔なアシスタントです。与えられたナレッジ以外は推測せず、分からない場合は「分かりかねます」と答えてください。",
                        _utc_now_iso(),
                    ),
                )

    def get(self) -> BotConfig:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT bot_role, updated_at FROM config WHERE id = 1"
            ).fetchone()
            assert row is not None
            return BotConfig(bot_role=row["bot_role"], updated_at=row["updated_at"])

    def set_role(self, bot_role: str) -> BotConfig:
        bot_role = (bot_role or "").strip()
        if not bot_role:
            bot_role = "あなたは親切で簡潔なアシスタントです。与えられたナレッジ以外は推測せず、分からない場合は「分かりかねます」と答えてください。"

        updated_at = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE config SET bot_role = ?, updated_at = ? WHERE id = 1",
                (bot_role, updated_at),
            )
        return BotConfig(bot_role=bot_role, updated_at=updated_at)
