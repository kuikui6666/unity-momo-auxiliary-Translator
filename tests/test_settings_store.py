from pathlib import Path

import game_translator.settings_store as settings_store
from game_translator.models import TranslationSettings


def test_translation_settings_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings_store, "settings_dir", lambda: tmp_path)

    settings = TranslationSettings()
    settings.mode = "machine"
    settings.local_port = 15001
    settings.llm.model = "gpt-4.1"
    settings.machine.provider = "libretranslate"
    settings.machine.api_base = "https://example.com/translate"
    settings.machine.api_key = "secret"

    path = settings_store.save_translation_settings(settings)
    loaded = settings_store.load_translation_settings()

    assert path.exists()
    assert loaded.mode == "machine"
    assert loaded.local_port == 15001
    assert loaded.llm.model == "gpt-4.1"
    assert loaded.machine.provider == "libretranslate"
    assert loaded.machine.api_base == "https://example.com/translate"
    assert loaded.machine.api_key == "secret"
