from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .analyzer import detect_unity_mono_game
from .installer import build_install_plan, install_runtime, uninstall_runtime
from .models import TranslationSettings
from .runtime import import_runtime_from_game, inspect_runtime
from .settings_store import load_translation_settings, save_translation_settings


def inspect_game_service(game_dir: str) -> dict[str, object]:
    game = detect_unity_mono_game(Path(game_dir))
    return asdict(game)


def inspect_runtime_service(runtime_root: str) -> dict[str, object]:
    runtime = inspect_runtime(Path(runtime_root))
    return asdict(runtime)


def import_runtime_service(source_game: str, runtime_root: str) -> dict[str, object]:
    runtime = import_runtime_from_game(Path(source_game), Path(runtime_root))
    return asdict(runtime)


def install_service(
    game_dir: str,
    runtime_root: str,
    target_language: str = "zh",
    dry_run: bool = False,
    translation_settings: TranslationSettings | None = None,
) -> dict[str, object]:
    game = detect_unity_mono_game(Path(game_dir))
    runtime = inspect_runtime(Path(runtime_root))
    plan = build_install_plan(game, runtime, target_language)
    return install_runtime(
        plan,
        dry_run=dry_run,
        translation_settings=translation_settings,
    )


def uninstall_service(game_dir: str) -> dict[str, object]:
    return uninstall_runtime(Path(game_dir))


def load_settings_service() -> dict[str, object]:
    return load_translation_settings().to_dict()


def save_settings_service(settings: TranslationSettings) -> dict[str, object]:
    path = save_translation_settings(settings)
    return {
        "saved": True,
        "path": str(path),
        "settings": settings.to_dict(),
    }
