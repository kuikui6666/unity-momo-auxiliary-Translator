from game_translator.gui import (
    build_install_summary,
    build_uninstall_summary,
    suggest_next_step,
    validate_game_dir_input,
    validate_runtime_dir_input,
    validate_translation_settings,
)
from game_translator.models import TranslationSettings


def test_validate_game_dir_input_rejects_data_directory(tmp_path) -> None:
    game_data_dir = tmp_path / "SampleGame_Data"
    game_data_dir.mkdir()

    issue = validate_game_dir_input(str(game_data_dir))

    assert issue is not None
    assert "*_Data" in issue


def test_validate_runtime_dir_input_rejects_packaged_tool_directory(tmp_path) -> None:
    runtime_dir = tmp_path / "PrivateGameTranslator"
    runtime_dir.mkdir()
    (runtime_dir / "PrivateGameTranslator.exe").write_bytes(b"")

    issue = validate_runtime_dir_input(str(runtime_dir))

    assert issue is not None
    assert "打包目录" in issue


def test_validate_translation_settings_requires_llm_fields() -> None:
    settings = TranslationSettings()
    settings.llm.api_base = ""

    issue = validate_translation_settings(settings)

    assert issue == "当前是大模型模式，请先填写 API Base。"


def test_suggest_next_step_prefers_game_selection() -> None:
    step = suggest_next_step(
        game_dir_text="",
        runtime_dir_text="D:\\runtime",
        source_game_text="",
        settings=TranslationSettings(),
        bridge_running=False,
    )

    assert step == "先选择目标游戏目录"


def test_build_install_summary_for_dry_run() -> None:
    summary = build_install_summary(
        {
            "dry_run": True,
            "manifest_path": "D:\\Game\\.private_translator\\install_manifest.json",
            "operations": ["复制 AutoTranslator", "生成 Config.ini"],
        }
    )

    assert "安装预览" in summary
    assert "复制 AutoTranslator" in summary


def test_build_uninstall_summary() -> None:
    summary = build_uninstall_summary({"removed": 5, "restored": 2})

    assert "卸载回滚完成" in summary
    assert "已删除: 5" in summary
