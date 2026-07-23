from game_translator.config_templates import (
    build_auto_translator_config,
    build_rei_patcher_ini,
)


def test_build_auto_translator_config_contains_language() -> None:
    config = build_auto_translator_config(
        language="zh",
        endpoint="CustomTranslate",
        custom_url="http://127.0.0.1:14366/translate",
    )

    assert "Language=zh" in config
    assert "OverrideFont=NotoSansSC_sdf32_optimized_12k_lz4_2020" in config
    assert "Endpoint=CustomTranslate" in config
    assert "Url=http://127.0.0.1:14366/translate" in config


def test_build_rei_patcher_ini_points_to_data_dir() -> None:
    config = build_rei_patcher_ini("LongJumpGame.exe")

    assert "AssembliesDir=..\\LongJumpGame_Data\\Managed" in config
    assert "Executable=..\\LongJumpGame.exe" in config
