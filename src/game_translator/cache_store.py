from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from .settings_store import settings_dir


class TranslationCacheStore:
    def __init__(self, cache_path: Path | None = None) -> None:
        self._cache_path = cache_path or (settings_dir() / "translation_cache.json")
        self._lock = threading.Lock()

    @property
    def cache_path(self) -> Path:
        return self._cache_path

    def get(self, cache_key: str) -> str | None:
        with self._lock:
            payload = self._load_unlocked()
            entry = payload.get("entries", {}).get(cache_key)
            if not isinstance(entry, dict):
                return None
            value = entry.get("translation")
            if not isinstance(value, str):
                return None
            return value

    def put(self, cache_key: str, source_text: str, translation: str, metadata: dict[str, str]) -> Path:
        with self._lock:
            payload = self._load_unlocked()
            entries = payload.setdefault("entries", {})
            entries[cache_key] = {
                "source_text": source_text,
                "translation": translation,
                "metadata": metadata,
            }
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return self._cache_path

    def build_cache_key(
        self,
        *,
        mode: str,
        source_lang: str,
        target_lang: str,
        text: str,
        backend_fingerprint: str,
    ) -> str:
        raw = "\n".join(
            [
                mode.strip().lower(),
                source_lang.strip().lower(),
                target_lang.strip().lower(),
                backend_fingerprint.strip(),
                text,
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load_unlocked(self) -> dict[str, object]:
        if not self._cache_path.exists():
            return {"entries": {}}
        payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"entries": {}}
        if "entries" not in payload or not isinstance(payload["entries"], dict):
            payload["entries"] = {}
        return payload
