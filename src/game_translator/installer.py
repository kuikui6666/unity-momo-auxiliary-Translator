from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config_templates import build_auto_translator_config, build_rei_patcher_ini
from .models import GameInfo, InstallPlan, RuntimeInfo, TranslationSettings


STATE_DIR_NAME = ".private_translator"
MANIFEST_NAME = "install_manifest.json"


def build_install_plan(game: GameInfo, runtime: RuntimeInfo, target_language: str) -> InstallPlan:
    operations = [
        f"复制 AutoTranslator -> {game.game_dir / 'AutoTranslator'}",
        f"复制 ReiPatcher -> {game.game_dir / 'ReiPatcher'}",
        f"复制 Managed 运行时 -> {game.managed_dir}",
        f"生成 AutoTranslator\\Config.ini，目标语言={target_language}",
        f"生成 ReiPatcher\\{game.exe_path.stem}.ini",
    ]
    if runtime.font_files:
        operations.append("复制字体文件到游戏根目录")
    return InstallPlan(game=game, runtime=runtime, target_language=target_language, operations=operations)


def install_runtime(
    plan: InstallPlan,
    dry_run: bool = False,
    translation_settings: TranslationSettings | None = None,
) -> dict[str, object]:
    manifest_entries: list[dict[str, str]] = []
    game_dir = plan.game.game_dir
    manifest_path = game_dir / STATE_DIR_NAME / MANIFEST_NAME

    if dry_run:
        result: dict[str, object] = {
            "dry_run": True,
            "operations": plan.operations,
            "manifest_path": str(manifest_path),
        }
        if translation_settings is not None:
            result["bridge_url"] = translation_settings.local_endpoint_url()
            result["translation_mode"] = translation_settings.mode
        return result

    _ensure_directory(game_dir / STATE_DIR_NAME)
    _copytree_with_manifest(
        plan.runtime.auto_translator_dir,
        game_dir / "AutoTranslator",
        manifest_entries,
        exclude_names={"Config.ini"},
    )
    _copytree_with_manifest(
        plan.runtime.rei_patcher_dir,
        game_dir / "ReiPatcher",
        manifest_entries,
        exclude_suffixes={".ini"},
    )

    for runtime_file in plan.runtime.managed_files:
        relative_path = runtime_file.relative_to(plan.runtime.root / "Managed")
        target = plan.game.managed_dir / relative_path
        _copyfile_with_manifest(runtime_file, target, manifest_entries)

    for font_file in plan.runtime.font_files:
        _copyfile_with_manifest(font_file, game_dir / font_file.name, manifest_entries)

    bridge_url = "http://127.0.0.1:14366/translate"
    translation_mode = "custom"
    if translation_settings is not None:
        bridge_url = translation_settings.local_endpoint_url()
        translation_mode = translation_settings.mode

    config_path = game_dir / "AutoTranslator" / "Config.ini"
    _write_text_with_manifest(
        config_path,
        build_auto_translator_config(
            language=plan.target_language,
            endpoint="CustomTranslate",
            custom_url=bridge_url,
        ),
        manifest_entries,
    )

    translation_dir = game_dir / "AutoTranslator" / "Translation" / plan.target_language / "Text"
    _ensure_directory(translation_dir)
    for name in ("_Preprocessors.txt", "_Postprocessors.txt", "_Substitutions.txt"):
        _write_text_with_manifest(translation_dir / name, "", manifest_entries)

    rei_ini_path = game_dir / "ReiPatcher" / f"{plan.game.exe_path.stem}.ini"
    _write_text_with_manifest(
        rei_ini_path,
        build_rei_patcher_ini(plan.game.exe_name),
        manifest_entries,
    )

    manifest_path.write_text(
        json.dumps({"entries": manifest_entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "dry_run": False,
        "manifest_path": str(manifest_path),
        "files_written": len(manifest_entries),
        "bridge_url": bridge_url,
        "translation_mode": translation_mode,
    }


def uninstall_runtime(game_dir: Path) -> dict[str, object]:
    game_dir = game_dir.resolve()
    manifest_path = game_dir / STATE_DIR_NAME / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"未找到安装清单: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    removed = 0
    restored = 0

    for entry in reversed(payload["entries"]):
        target = Path(entry["target"])
        backup = entry.get("backup")
        if target.exists():
            if target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
            removed += 1
            _prune_empty_parents(target.parent, game_dir)
        if backup:
            backup_path = Path(backup)
            if backup_path.exists():
                _ensure_directory(target.parent)
                shutil.move(str(backup_path), str(target))
                restored += 1

    if manifest_path.exists():
        manifest_path.unlink()

    backup_root = game_dir / STATE_DIR_NAME / "backup"
    if backup_root.exists():
        shutil.rmtree(backup_root)
    state_dir = game_dir / STATE_DIR_NAME
    if state_dir.exists() and not any(state_dir.iterdir()):
        state_dir.rmdir()

    return {"removed": removed, "restored": restored}


def _copytree_with_manifest(
    source: Path,
    target: Path,
    manifest_entries: list[dict[str, str]],
    exclude_names: set[str] | None = None,
    exclude_suffixes: set[str] | None = None,
) -> None:
    exclude_names = exclude_names or set()
    exclude_suffixes = exclude_suffixes or set()
    for file_path in source.rglob("*"):
        if file_path.is_file():
            if file_path.name in exclude_names:
                continue
            if file_path.suffix.lower() in exclude_suffixes:
                continue
            relative_path = file_path.relative_to(source)
            _copyfile_with_manifest(file_path, target / relative_path, manifest_entries)


def _copyfile_with_manifest(source: Path, target: Path, manifest_entries: list[dict[str, str]]) -> None:
    backup = _backup_if_needed(target)
    _ensure_directory(target.parent)
    shutil.copy2(source, target)
    manifest_entries.append(_build_manifest_entry(target, backup))


def _write_text_with_manifest(target: Path, content: str, manifest_entries: list[dict[str, str]]) -> None:
    backup = _backup_if_needed(target)
    _ensure_directory(target.parent)
    target.write_text(content, encoding="utf-8")
    manifest_entries.append(_build_manifest_entry(target, backup))


def _build_manifest_entry(target: Path, backup: Path | None) -> dict[str, str]:
    item = {"target": str(target)}
    if backup is not None:
        item["backup"] = str(backup)
    return item


def _backup_if_needed(target: Path) -> Path | None:
    if not target.exists():
        return None
    game_dir = _find_game_root(target)
    backup_root = game_dir / STATE_DIR_NAME / "backup"
    backup_path = backup_root / target.relative_to(game_dir)
    _ensure_directory(backup_path.parent)
    shutil.move(str(target), str(backup_path))
    return backup_path


def _find_game_root(path: Path) -> Path:
    current = path.resolve()
    for parent in [current.parent, *current.parents]:
        if any(parent.glob("*_Data")):
            return parent
    raise ValueError(f"无法推断游戏根目录: {path}")


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _prune_empty_parents(start: Path, stop: Path) -> None:
    current = start
    stop = stop.resolve()
    while current.resolve() != stop:
        if current.exists() and current.is_dir() and not any(current.iterdir()):
            current.rmdir()
            current = current.parent
            continue
        break
