from __future__ import annotations

import json
from pathlib import Path

from .app_paths import app_root
from .models import TranslationSettings


def settings_dir() -> Path:
    # 把用户本地配置统一收口到项目根下的私有目录，便于忽略和清理。
    return app_root() / ".private_translator"


def settings_path() -> Path:
    return settings_dir() / "settings.json"


def load_translation_settings() -> TranslationSettings:
    path = settings_path()
    if not path.exists():
        # 首次运行时直接回退到内置默认配置，不强制要求预先建文件。
        return TranslationSettings()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TranslationSettings.from_dict(payload)


def save_translation_settings(settings: TranslationSettings) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
