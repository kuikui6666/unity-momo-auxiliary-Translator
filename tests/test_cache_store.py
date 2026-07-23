from pathlib import Path

from game_translator.cache_store import TranslationCacheStore


def test_cache_store_put_and_get(tmp_path: Path) -> None:
    store = TranslationCacheStore(tmp_path / "translation_cache.json")
    key = store.build_cache_key(
        mode="llm",
        source_lang="ja",
        target_lang="zh",
        text="こんにちは",
        backend_fingerprint="llm|https://api.example.com/v1/chat/completions|gpt-4.1-mini",
    )

    assert store.get(key) is None

    path = store.put(
        cache_key=key,
        source_text="こんにちは",
        translation="你好",
        metadata={
            "mode": "llm",
            "source_lang": "ja",
            "target_lang": "zh",
            "backend": "llm|https://api.example.com/v1/chat/completions|gpt-4.1-mini",
        },
    )

    assert path.exists()
    assert store.get(key) == "你好"


def test_cache_key_changes_when_backend_changes(tmp_path: Path) -> None:
    store = TranslationCacheStore(tmp_path / "translation_cache.json")

    key1 = store.build_cache_key(
        mode="llm",
        source_lang="ja",
        target_lang="zh",
        text="test",
        backend_fingerprint="llm|a|m1",
    )
    key2 = store.build_cache_key(
        mode="llm",
        source_lang="ja",
        target_lang="zh",
        text="test",
        backend_fingerprint="llm|a|m2",
    )

    assert key1 != key2
