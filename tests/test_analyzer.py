from pathlib import Path

from game_translator.analyzer import detect_unity_mono_game


def test_detect_unity_mono_game(tmp_path: Path) -> None:
    game_dir = tmp_path / "SampleGame"
    game_dir.mkdir()
    (game_dir / "SampleGame.exe").write_bytes(b"")
    (game_dir / "MonoBleedingEdge").mkdir()
    (game_dir / "SampleGame_Data" / "Managed").mkdir(parents=True)

    info = detect_unity_mono_game(game_dir)

    assert info.is_unity_mono is True
    assert info.exe_name == "SampleGame.exe"
    assert info.managed_dir == game_dir / "SampleGame_Data" / "Managed"
