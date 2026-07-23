from __future__ import annotations

from pathlib import Path

from .models import GameInfo


def detect_unity_mono_game(game_dir: Path) -> GameInfo:
    game_dir = game_dir.resolve()
    exe_files = sorted(game_dir.glob("*.exe"))
    if not exe_files:
        raise FileNotFoundError(f"未找到 exe: {game_dir}")

    for exe_path in exe_files:
        if exe_path.name.lower() == "unitycrashhandler64.exe":
            continue
        data_dir = game_dir / f"{exe_path.stem}_Data"
        managed_dir = data_dir / "Managed"
        mono_dir = game_dir / "MonoBleedingEdge"
        if data_dir.exists() and managed_dir.exists():
            notes: list[str] = []
            if mono_dir.exists():
                notes.append("检测到 MonoBleedingEdge")
            notes.append("检测到 *_Data/Managed")
            architecture = "x64" if _looks_64_bit(game_dir) else "unknown"
            return GameInfo(
                game_dir=game_dir,
                exe_path=exe_path,
                exe_name=exe_path.name,
                data_dir=data_dir,
                managed_dir=managed_dir,
                engine="unity",
                architecture=architecture,
                is_unity_mono=True,
                notes=notes,
            )

    raise ValueError(f"目录看起来不是受支持的 Unity Mono 游戏: {game_dir}")


def _looks_64_bit(game_dir: Path) -> bool:
    if (game_dir / "UnityPlayer.dll").exists():
        return True
    if (game_dir / "GameAssembly.dll").exists():
        return True
    if (game_dir / "D3D12").exists():
        return True
    return False
