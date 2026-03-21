from __future__ import annotations

import os
import re
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _env_int(name: str, default: int) -> int:
    v = _env(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    v = _env(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    v = _env(name)
    if v is None:
        return default
    s = v.strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _normalize_model_id(raw: str | None, *, default: str) -> str:
    """
    Accept common formats and normalize to the SDK-friendly model ID.

    Examples:
    - "gemini-2.0-flash" -> "gemini-2.0-flash"
    - "models/gemini-2.0-flash" -> "gemini-2.0-flash"
    - "v1beta/models/gemini-2.0-flash:generateContent" -> "gemini-2.0-flash"
    - "\"gemini-2.0-flash\"" -> "gemini-2.0-flash"
    """
    s = (raw or "").strip()
    if not s:
        return default

    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    # If someone pasted a whole assignment line into the value, extract the RHS.
    # e.g. "GEMINI_MODEL=gemini-2.0-flash" -> "gemini-2.0-flash"
    m = re.match(r"^[A-Z0-9_]+\s*=\s*(.+)$", s)
    if m:
        s = (m.group(1) or "").strip()

    # Drop endpoint-like prefixes.
    for prefix in ("v1beta/models/", "v1/models/", "models/"):
        if s.startswith(prefix):
            s = s[len(prefix) :].strip()

    # Drop method suffix if present.
    if ":" in s:
        s = s.split(":", 1)[0].strip()

    s = s or default

    # Backward-compatible aliases for common deprecated IDs.
    if s in {"text-embedding-004", "text-embedding-04"}:
        return "gemini-embedding-001"

    return s


@dataclass(frozen=True)
class Settings:
    line_channel_secret: str | None
    line_channel_access_token: str | None

    gemini_api_key: str | None
    gemini_model: str
    gemini_embed_model: str

    data_dir: str
    chroma_dir: str
    sqlite_path: str

    firestore_project_id: str | None
    firestore_database: str | None

    rag_top_k: int
    rag_min_similarity: float
    rag_fallback_to_llm: bool


def get_settings() -> Settings:
    data_dir = _env("DATA_DIR", "./data") or "./data"
    chroma_dir = _env("CHROMA_DIR", os.path.join(data_dir, "chroma")) or os.path.join(
        data_dir, "chroma"
    )
    sqlite_path = _env("SQLITE_PATH", os.path.join(data_dir, "config.sqlite3")) or os.path.join(
        data_dir, "config.sqlite3"
    )

    firestore_project_id = _env("FIRESTORE_PROJECT_ID") or _env("GOOGLE_CLOUD_PROJECT")
    firestore_database = _env("FIRESTORE_DATABASE")

    return Settings(
        line_channel_secret=_env("LINE_CHANNEL_SECRET"),
        line_channel_access_token=_env("LINE_CHANNEL_ACCESS_TOKEN"),
        gemini_api_key=_env("GEMINI_API_KEY"),
        gemini_model=_normalize_model_id(_env("GEMINI_MODEL"), default="gemini-1.5-flash"),
        gemini_embed_model=_normalize_model_id(
            _env("GEMINI_EMBED_MODEL"), default="gemini-embedding-001"
        ),
        data_dir=data_dir,
        chroma_dir=chroma_dir,
        sqlite_path=sqlite_path,
        firestore_project_id=firestore_project_id,
        firestore_database=firestore_database,
        rag_top_k=_env_int("RAG_TOP_K", 3),
        rag_min_similarity=_env_float("RAG_MIN_SIMILARITY", 0.0),
        rag_fallback_to_llm=_env_bool("RAG_FALLBACK_TO_LLM", True),
    )
