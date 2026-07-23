from pathlib import Path

from game_translator.analyzer import detect_unity_mono_game
from game_translator.installer import build_install_plan, install_runtime, uninstall_runtime
from game_translator.runtime import inspect_runtime


def test_install_and_uninstall_runtime(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    (runtime_root / "AutoTranslator" / "Translation" / "zh" / "Text").mkdir(parents=True)
    (runtime_root / "ReiPatcher" / "Patches").mkdir(parents=True)
    (runtime_root / "Managed" / "Translators" / "FullNET").mkdir(parents=True)

    (runtime_root / "AutoTranslator" / "placeholder.txt").write_text("ok", encoding="utf-8")
    (runtime_root / "AutoTranslator" / "Config.ini").write_text("old", encoding="utf-8")
    (runtime_root / "ReiPatcher" / "ReiPatcher.exe").write_bytes(b"")
    (runtime_root / "ReiPatcher" / "Sample.ini").write_text("old", encoding="utf-8")
    (runtime_root / "Managed" / "ExIni.dll").write_bytes(b"")
    (runtime_root / "Managed" / "XUnity.Common.dll").write_bytes(b"")
    (runtime_root / "Managed" / "Translators" / "FullNET" / "Newtonsoft.Json.dll").write_bytes(b"")
    (runtime_root / "NotoSansSC_sdf32_optimized_12k_lz4_2020").write_text("font", encoding="utf-8")

    game_dir = tmp_path / "TestGame"
    (game_dir / "TestGame_Data" / "Managed").mkdir(parents=True)
    (game_dir / "MonoBleedingEdge").mkdir()
    (game_dir / "TestGame.exe").write_bytes(b"")

    game = detect_unity_mono_game(game_dir)
    runtime = inspect_runtime(runtime_root)
    plan = build_install_plan(game, runtime, "zh")

    result = install_runtime(plan, dry_run=False)

    assert result["dry_run"] is False
    assert (game_dir / "AutoTranslator" / "Config.ini").exists()
    assert (game_dir / "ReiPatcher" / "TestGame.ini").exists()
    assert not (game_dir / "ReiPatcher" / "Sample.ini").exists()
    assert (game_dir / "TestGame_Data" / "Managed" / "XUnity.Common.dll").exists()

    uninstall_result = uninstall_runtime(game_dir)

    assert uninstall_result["removed"] > 0
    assert not (game_dir / "AutoTranslator").exists()
    assert not (game_dir / "ReiPatcher").exists()
