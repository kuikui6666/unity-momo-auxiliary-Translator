from __future__ import annotations

import json
import traceback
import urllib.error
import urllib.parse
import urllib.request
from functools import partial
from pathlib import Path
from typing import Callable

from .app_paths import default_runtime_dir
from .models import LLMProviderSettings, MachineProviderSettings, TranslationSettings
from .services import (
    import_runtime_service,
    inspect_game_service,
    inspect_runtime_service,
    install_service,
    load_settings_service,
    save_settings_service,
    uninstall_service,
)
from .settings_store import settings_dir
from .translation_bridge import TranslationBridgeServer


def validate_game_dir_input(path_text: str) -> str | None:
    path_text = path_text.strip()
    if not path_text:
        return "请先选择目标游戏目录。"
    path = Path(path_text)
    if not path.exists():
        return f"目标游戏目录不存在: {path}"
    if not path.is_dir():
        return f"目标游戏路径不是目录: {path}"
    if path.name.endswith("_Data"):
        return "你选到的是 *_Data 子目录。请改选包含游戏 exe 的根目录。"
    if (path / "PrivateGameTranslator.exe").exists() or path.name == "PrivateGameTranslator":
        return "你选到的是本工具的打包目录，不是游戏目录。请改选真正的游戏根目录。"
    if not any(path.glob("*.exe")):
        return "目标目录里没有发现 exe。请改选包含游戏主程序的目录。"
    return None


def validate_runtime_dir_input(path_text: str) -> str | None:
    path_text = path_text.strip()
    if not path_text:
        return "请先选择运行时目录。"
    path = Path(path_text)
    if not path.exists():
        return f"运行时目录不存在: {path}"
    if not path.is_dir():
        return f"运行时路径不是目录: {path}"
    if (path / "PrivateGameTranslator.exe").exists() or path.name == "PrivateGameTranslator":
        return "你选到的是本工具的打包目录，不是运行时目录。请改选包含 AutoTranslator/ReiPatcher/Managed 的目录。"
    return None


def validate_source_game_dir_input(path_text: str) -> str | None:
    path_text = path_text.strip()
    if not path_text:
        return "请先选择样例源游戏目录。"
    path = Path(path_text)
    if not path.exists():
        return f"样例源游戏目录不存在: {path}"
    if not path.is_dir():
        return f"样例源游戏路径不是目录: {path}"
    if path.name.endswith("_Data"):
        return "样例源游戏目录也应该选游戏根目录，而不是 *_Data 子目录。"
    return None


def validate_translation_settings(settings: TranslationSettings) -> str | None:
    if not settings.local_host.strip():
        return "本地 Host 不能为空。"
    if settings.mode == "llm":
        if not settings.llm.api_base.strip():
            return "当前是大模型模式，请先填写 API Base。"
        if not settings.llm.api_key.strip():
            return "当前是大模型模式，请先填写 API Key。"
        if not settings.llm.model.strip():
            return "当前是大模型模式，请先填写模型名。"
        return None
    if not settings.machine.api_base.strip():
        return "当前是普通机翻模式，请先填写机翻 API Base。"
    if settings.machine.provider.lower() == "deepl" and not settings.machine.api_key.strip():
        return "当前是 DeepL 模式，请先填写 API Key。"
    return None


def suggest_next_step(
    game_dir_text: str,
    runtime_dir_text: str,
    source_game_text: str,
    settings: TranslationSettings,
    bridge_running: bool,
) -> str:
    if not game_dir_text.strip():
        return "先选择目标游戏目录"
    if not runtime_dir_text.strip():
        return "再选择运行时目录"
    if not source_game_text.strip() and not Path(runtime_dir_text).exists():
        return "如果没有现成运行时，先选择样例源游戏目录"
    config_issue = validate_translation_settings(settings)
    if config_issue is not None:
        return "补全翻译配置并保存"
    if not bridge_running:
        return "先启动翻译服务，再做干运行安装"
    return "先干运行安装，确认无误后再正式安装"


def build_install_summary(result: dict[str, object]) -> str:
    if result.get("dry_run"):
        operations = result.get("operations", [])
        lines = ["安装预览", f"Manifest: {result.get('manifest_path', '未知')}"]
        lines.extend(f"- {item}" for item in operations if isinstance(item, str))
        return "\n".join(lines)
    return "\n".join(
        [
            "安装完成",
            f"写入文件数: {result.get('files_written', 0)}",
            f"Manifest: {result.get('manifest_path', '未知')}",
            f"翻译模式: {result.get('translation_mode', '未知')}",
            f"桥接地址: {result.get('bridge_url', '未知')}",
        ]
    )


def build_uninstall_summary(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "卸载回滚完成",
            f"已删除: {result.get('removed', 0)}",
            f"已恢复备份: {result.get('restored', 0)}",
        ]
    )


def launch_gui() -> None:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QPalette
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QPushButton,
            QScrollArea,
            QSizePolicy,
            QSpinBox,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError("未安装 PySide6。请先执行: python -m pip install PySide6") from exc

    class PageFriendlyComboBox(QComboBox):
        def wheelEvent(self, event) -> None:  # noqa: N802
            if self.hasFocus():
                super().wheelEvent(event)
            else:
                event.ignore()

    class PageFriendlySpinBox(QSpinBox):
        def wheelEvent(self, event) -> None:  # noqa: N802
            if self.hasFocus():
                super().wheelEvent(event)
            else:
                event.ignore()

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self._settings = TranslationSettings.from_dict(load_settings_service())
            self._bridge = TranslationBridgeServer(self._get_current_settings)
            self.setWindowTitle("私人游戏翻译器")
            self.resize(1240, 900)
            self._apply_palette()
            self._build_ui()
            self._bind_events()
            self._register_clickable_widgets()
            self._apply_defaults()
            self._fill_settings_form(self._settings)
            self._update_mode_hint()
            self._update_bridge_status()
            self._update_summary()
            self._apply_styles()
            self.statusBar().showMessage("就绪")

        def closeEvent(self, event) -> None:  # noqa: N802
            self._bridge.stop()
            super().closeEvent(event)

        def _apply_palette(self) -> None:
            palette = self.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#f5efe6"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#fffdfa"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f1e9de"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#241a14"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#241a14"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#241a14"))
            self.setPalette(palette)

        def _apply_styles(self) -> None:
            self.setStyleSheet(
                """
                QMainWindow {
                    background: #f5efe6;
                }
                QScrollArea, QWidget#Canvas {
                    background: transparent;
                }
                QLabel#HeroTitle {
                    font-size: 30px;
                    font-weight: 700;
                    color: #23160f;
                }
                QLabel#HeroSubtitle {
                    font-size: 13px;
                    color: #70584a;
                }
                QLabel#StatusPill {
                    background: #efe1cf;
                    color: #5c4639;
                    border-radius: 13px;
                    padding: 6px 12px;
                    font-weight: 600;
                }
                QFrame#HeroCard, QFrame#SummaryCard {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #fffaf5,
                        stop:1 #efe3d3
                    );
                    border: 1px solid #ddc7af;
                    border-radius: 20px;
                }
                QTabWidget::pane {
                    border: 1px solid #d7c3af;
                    background: #fffdf9;
                    border-radius: 16px;
                    top: -1px;
                }
                QTabBar::tab {
                    background: #ead9c6;
                    color: #5b4437;
                    border: 1px solid #d7c3af;
                    padding: 10px 18px;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    margin-right: 6px;
                    font-weight: 600;
                }
                QTabBar::tab:selected {
                    background: #fffdf9;
                    color: #241a14;
                }
                QGroupBox {
                    background: #fffdf9;
                    border: 1px solid #e0d0bf;
                    border-radius: 16px;
                    margin-top: 12px;
                    font-weight: 700;
                    color: #2d2018;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 14px;
                    padding: 0 6px;
                }
                QLabel {
                    color: #2d2018;
                }
                QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
                    background: #fffaf5;
                    border: 1px solid #d9c6b3;
                    border-radius: 10px;
                    padding: 8px 10px;
                    selection-background-color: #ca8f4b;
                    selection-color: white;
                }
                QPlainTextEdit {
                    padding: 10px;
                }
                QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                    border: 1px solid #bf7d35;
                }
                QPushButton {
                    background: #efe2d2;
                    color: #2f2017;
                    border: 1px solid #d5bea6;
                    border-radius: 12px;
                    padding: 9px 16px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #e6d3be;
                }
                QPushButton:pressed {
                    background: #dcc3a9;
                    padding-top: 10px;
                    padding-bottom: 8px;
                }
                QPushButton:disabled {
                    background: #ece4da;
                    color: #9a8b7c;
                    border: 1px solid #ddd1c3;
                }
                QPushButton#PrimaryButton {
                    background: #b86d2c;
                    color: white;
                    border: 1px solid #a15d24;
                }
                QPushButton#PrimaryButton:hover {
                    background: #c87934;
                }
                QPushButton#PrimaryButton:pressed {
                    background: #9f5c24;
                }
                QPushButton#GhostButton {
                    background: #fffaf5;
                }
                QLabel#SectionHint {
                    color: #7b6353;
                    font-size: 12px;
                }
                """
            )

        def _build_ui(self) -> None:
            central = QWidget(self)
            self.setCentralWidget(central)
            shell_layout = QVBoxLayout(central)
            shell_layout.setContentsMargins(0, 0, 0, 0)

            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            shell_layout.addWidget(self.scroll_area)

            canvas = QWidget()
            canvas.setObjectName("Canvas")
            self.scroll_area.setWidget(canvas)

            root_layout = QVBoxLayout(canvas)
            root_layout.setContentsMargins(20, 20, 20, 20)
            root_layout.setSpacing(16)

            hero = self._build_hero_card()
            summary = self._build_summary_card()
            self.tabs = QTabWidget()
            self.tabs.addTab(self._build_quick_start_tab(), "快速开始")
            self.tabs.addTab(self._build_translation_tab(), "翻译配置")
            self.tabs.addTab(self._build_tools_tab(), "测试与日志")

            root_layout.addWidget(hero)
            root_layout.addWidget(summary)
            root_layout.addWidget(self.tabs)

        def _build_hero_card(self) -> QFrame:
            card = QFrame()
            card.setObjectName("HeroCard")
            layout = QHBoxLayout(card)
            layout.setContentsMargins(22, 22, 22, 22)

            left = QVBoxLayout()
            title = QLabel("私人游戏翻译器")
            title.setObjectName("HeroTitle")
            subtitle = QLabel(
                "先选游戏，再选翻译模式，最后启动翻译服务并安装。常用路径和状态都放在首页，不必来回翻找。"
            )
            subtitle.setWordWrap(True)
            subtitle.setObjectName("HeroSubtitle")
            left.addWidget(title)
            left.addWidget(subtitle)

            right = QVBoxLayout()
            right.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.hero_support_pill = QLabel("支持：仅 Unity Mono")
            self.hero_support_pill.setObjectName("StatusPill")
            self.hero_mode_pill = QLabel()
            self.hero_mode_pill.setObjectName("StatusPill")
            self.hero_bridge_pill = QLabel()
            self.hero_bridge_pill.setObjectName("StatusPill")
            self.hero_cache_pill = QLabel()
            self.hero_cache_pill.setObjectName("StatusPill")
            right.addWidget(self.hero_support_pill)
            right.addWidget(self.hero_mode_pill)
            right.addWidget(self.hero_bridge_pill)
            right.addWidget(self.hero_cache_pill)

            layout.addLayout(left, 1)
            layout.addLayout(right)
            return card

        def _build_summary_card(self) -> QFrame:
            card = QFrame()
            card.setObjectName("SummaryCard")
            layout = QGridLayout(card)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setHorizontalSpacing(14)
            layout.setVerticalSpacing(10)

            self.summary_game_value = QLabel("未选择")
            self.summary_runtime_value = QLabel("未选择")
            self.summary_endpoint_value = QLabel("未配置")
            self.summary_cache_value = QLabel("未生成")
            self.summary_next_step_value = QLabel("先选择目标游戏目录")

            layout.addWidget(self._summary_label("目标游戏"), 0, 0)
            layout.addWidget(self.summary_game_value, 0, 1)
            layout.addWidget(self._summary_label("运行时"), 1, 0)
            layout.addWidget(self.summary_runtime_value, 1, 1)
            layout.addWidget(self._summary_label("当前接口"), 0, 2)
            layout.addWidget(self.summary_endpoint_value, 0, 3)
            layout.addWidget(self._summary_label("缓存文件"), 1, 2)
            layout.addWidget(self.summary_cache_value, 1, 3)
            layout.addWidget(self._summary_label("建议下一步"), 2, 0)
            layout.addWidget(self.summary_next_step_value, 2, 1, 1, 3)
            return card

        def _summary_label(self, text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("SectionHint")
            return label

        def _build_quick_start_tab(self) -> QWidget:
            tab = QWidget()
            root = QVBoxLayout(tab)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(14)

            path_group = QGroupBox("第 1 步：选择路径")
            path_layout = QGridLayout(path_group)
            self.game_dir_edit = QLineEdit()
            self.runtime_dir_edit = QLineEdit()
            self.source_game_edit = QLineEdit()
            self.language_combo = PageFriendlyComboBox()
            self.language_combo.addItems(["zh", "zh-CN", "zh-TW", "en", "ko", "ja"])
            self.language_combo.setCurrentText("zh")

            path_layout.addWidget(QLabel("目标游戏目录"), 0, 0)
            path_layout.addWidget(self.game_dir_edit, 0, 1)
            path_layout.addWidget(self._build_browse_button(self.game_dir_edit), 0, 2)
            path_layout.addWidget(QLabel("运行时目录"), 1, 0)
            path_layout.addWidget(self.runtime_dir_edit, 1, 1)
            path_layout.addWidget(self._build_browse_button(self.runtime_dir_edit), 1, 2)
            path_layout.addWidget(QLabel("样例源游戏目录"), 2, 0)
            path_layout.addWidget(self.source_game_edit, 2, 1)
            path_layout.addWidget(self._build_browse_button(self.source_game_edit), 2, 2)
            path_layout.addWidget(QLabel("目标语言"), 3, 0)
            path_layout.addWidget(self.language_combo, 3, 1)
            path_layout.addWidget(
                self._hint_label("当前工具只支持 Unity Mono。请选择包含游戏 exe 和 *_Data/Managed 的游戏根目录。"),
                4,
                0,
                1,
                3,
            )

            verify_group = QGroupBox("第 2 步：准备环境")
            verify_layout = QGridLayout(verify_group)
            self.inspect_game_button = QPushButton("检查游戏")
            self.inspect_runtime_button = QPushButton("检查运行时")
            self.import_runtime_button = QPushButton("导入运行时")
            self.inspect_game_button.setObjectName("GhostButton")
            self.inspect_runtime_button.setObjectName("GhostButton")
            verify_layout.addWidget(self.inspect_game_button, 0, 0)
            verify_layout.addWidget(self.inspect_runtime_button, 0, 1)
            verify_layout.addWidget(self.import_runtime_button, 0, 2)
            verify_layout.addWidget(
                self._hint_label("如果运行时目录还是空的，先用“导入运行时”把样例游戏里的翻译运行时同步过来。"),
                1,
                0,
                1,
                3,
            )

            action_group = QGroupBox("第 3 步：启动并安装")
            action_layout = QGridLayout(action_group)
            self.start_bridge_button = QPushButton("启动翻译服务")
            self.stop_bridge_button = QPushButton("停止翻译服务")
            self.dry_run_button = QPushButton("干运行安装")
            self.install_button = QPushButton("正式安装")
            self.uninstall_button = QPushButton("卸载回滚")
            self.start_bridge_button.setObjectName("PrimaryButton")
            self.install_button.setObjectName("PrimaryButton")
            action_layout.addWidget(self.start_bridge_button, 0, 0)
            action_layout.addWidget(self.stop_bridge_button, 0, 1)
            action_layout.addWidget(self.dry_run_button, 0, 2)
            action_layout.addWidget(self.install_button, 1, 0, 1, 2)
            action_layout.addWidget(self.uninstall_button, 1, 2)
            action_layout.addWidget(
                self._hint_label("推荐流程：保存翻译配置 -> 启动翻译服务 -> 正式安装 -> 启动游戏。"),
                2,
                0,
                1,
                3,
            )

            summary_group = QGroupBox("操作摘要")
            summary_layout = QVBoxLayout(summary_group)
            self.operation_summary_output = QPlainTextEdit()
            self.operation_summary_output.setReadOnly(True)
            self.operation_summary_output.setPlaceholderText("这里会显示检查、导入、安装、回滚的结果摘要。")
            summary_layout.addWidget(self.operation_summary_output)

            root.addWidget(path_group)
            root.addWidget(verify_group)
            root.addWidget(action_group)
            root.addWidget(summary_group)
            root.addStretch(1)
            return tab

        def _build_translation_tab(self) -> QWidget:
            tab = QWidget()
            root = QVBoxLayout(tab)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(14)

            bridge_group = QGroupBox("翻译模式与本地服务")
            bridge_layout = QGridLayout(bridge_group)
            self.mode_combo = PageFriendlyComboBox()
            self.mode_combo.addItems(["llm", "machine"])
            self.host_edit = QLineEdit()
            self.port_spin = PageFriendlySpinBox()
            self.port_spin.setRange(1024, 65535)
            self.timeout_spin = PageFriendlySpinBox()
            self.timeout_spin.setRange(5, 300)
            self.bridge_status_label = QLabel()
            self.mode_hint_label = QLabel()
            self.mode_hint_label.setWordWrap(True)
            self.host_edit.setPlaceholderText("127.0.0.1")

            bridge_layout.addWidget(QLabel("翻译模式"), 0, 0)
            bridge_layout.addWidget(self.mode_combo, 0, 1)
            bridge_layout.addWidget(QLabel("本地 Host"), 1, 0)
            bridge_layout.addWidget(self.host_edit, 1, 1)
            bridge_layout.addWidget(QLabel("本地 Port"), 1, 2)
            bridge_layout.addWidget(self.port_spin, 1, 3)
            bridge_layout.addWidget(QLabel("请求超时(秒)"), 2, 0)
            bridge_layout.addWidget(self.timeout_spin, 2, 1)
            bridge_layout.addWidget(QLabel("服务状态"), 2, 2)
            bridge_layout.addWidget(self.bridge_status_label, 2, 3)
            bridge_layout.addWidget(self.mode_hint_label, 3, 0, 1, 4)

            llm_group = QGroupBox("大模型配置")
            llm_layout = QGridLayout(llm_group)
            self.llm_api_base_edit = QLineEdit()
            self.llm_api_key_edit = QLineEdit()
            self.llm_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.llm_model_edit = QLineEdit()
            self.llm_system_prompt_edit = QPlainTextEdit()
            self.llm_system_prompt_edit.setPlaceholderText("系统提示词")
            self.llm_system_prompt_edit.setMaximumHeight(150)
            llm_layout.addWidget(QLabel("API Base"), 0, 0)
            llm_layout.addWidget(self.llm_api_base_edit, 0, 1, 1, 3)
            llm_layout.addWidget(QLabel("API Key"), 1, 0)
            llm_layout.addWidget(self.llm_api_key_edit, 1, 1, 1, 3)
            llm_layout.addWidget(QLabel("模型"), 2, 0)
            llm_layout.addWidget(self.llm_model_edit, 2, 1, 1, 3)
            llm_layout.addWidget(QLabel("系统提示词"), 3, 0)
            llm_layout.addWidget(self.llm_system_prompt_edit, 3, 1, 2, 3)

            machine_group = QGroupBox("普通机翻配置")
            machine_layout = QGridLayout(machine_group)
            self.machine_provider_combo = PageFriendlyComboBox()
            self.machine_provider_combo.addItems(["deepl", "libretranslate"])
            self.machine_api_base_edit = QLineEdit()
            self.machine_api_key_edit = QLineEdit()
            self.machine_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            machine_layout.addWidget(QLabel("提供方"), 0, 0)
            machine_layout.addWidget(self.machine_provider_combo, 0, 1)
            machine_layout.addWidget(QLabel("API Base"), 1, 0)
            machine_layout.addWidget(self.machine_api_base_edit, 1, 1, 1, 3)
            machine_layout.addWidget(QLabel("API Key"), 2, 0)
            machine_layout.addWidget(self.machine_api_key_edit, 2, 1, 1, 3)

            save_group = QGroupBox("保存与缓存")
            save_layout = QGridLayout(save_group)
            self.save_settings_button = QPushButton("保存翻译配置")
            self.save_settings_button.setObjectName("PrimaryButton")
            self.cache_path_label = QLabel()
            self.cache_path_label.setWordWrap(True)
            save_layout.addWidget(self.save_settings_button, 0, 0)
            save_layout.addWidget(self._hint_label("缓存会优先复用已翻译文本，避免重复请求 AI 消耗 token。"), 0, 1)
            save_layout.addWidget(QLabel("缓存文件"), 1, 0)
            save_layout.addWidget(self.cache_path_label, 1, 1)

            root.addWidget(bridge_group)
            root.addWidget(llm_group)
            root.addWidget(machine_group)
            root.addWidget(save_group)
            root.addStretch(1)
            return tab

        def _build_tools_tab(self) -> QWidget:
            tab = QWidget()
            root = QVBoxLayout(tab)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(14)

            test_group = QGroupBox("快速测试")
            test_layout = QGridLayout(test_group)
            self.test_input_edit = QPlainTextEdit()
            self.test_input_edit.setPlaceholderText("输入一段要测试的原文")
            self.test_output_edit = QPlainTextEdit()
            self.test_output_edit.setReadOnly(True)
            self.test_output_edit.setPlaceholderText("这里显示翻译结果")
            self.test_translation_button = QPushButton("测试翻译")
            self.test_translation_button.setObjectName("PrimaryButton")

            test_layout.addWidget(QLabel("原文"), 0, 0)
            test_layout.addWidget(QLabel("结果"), 0, 1)
            test_layout.addWidget(self.test_input_edit, 1, 0)
            test_layout.addWidget(self.test_output_edit, 1, 1)
            test_layout.addWidget(self.test_translation_button, 2, 1)

            log_group = QGroupBox("日志")
            log_layout = QVBoxLayout(log_group)
            self.log_output = QPlainTextEdit()
            self.log_output.setReadOnly(True)
            self.log_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.clear_log_button = QPushButton("清空日志")
            log_layout.addWidget(self.log_output)
            log_layout.addWidget(self.clear_log_button, alignment=Qt.AlignmentFlag.AlignRight)

            root.addWidget(test_group)
            root.addWidget(log_group, 1)
            return tab

        def _bind_events(self) -> None:
            self.inspect_game_button.clicked.connect(
                partial(self._run_with_button_feedback, self.inspect_game_button, "正在检查游戏...", self._inspect_game)
            )
            self.inspect_runtime_button.clicked.connect(
                partial(self._run_with_button_feedback, self.inspect_runtime_button, "正在检查运行时...", self._inspect_runtime)
            )
            self.import_runtime_button.clicked.connect(
                partial(self._run_with_button_feedback, self.import_runtime_button, "正在导入运行时...", self._import_runtime)
            )
            self.start_bridge_button.clicked.connect(
                partial(self._run_with_button_feedback, self.start_bridge_button, "正在启动翻译服务...", self._start_bridge)
            )
            self.stop_bridge_button.clicked.connect(
                partial(self._run_with_button_feedback, self.stop_bridge_button, "正在停止翻译服务...", self._stop_bridge)
            )
            self.dry_run_button.clicked.connect(
                partial(self._run_with_button_feedback, self.dry_run_button, "正在干运行安装...", self._dry_run_install)
            )
            self.install_button.clicked.connect(
                partial(self._run_with_button_feedback, self.install_button, "正在正式安装...", self._install)
            )
            self.uninstall_button.clicked.connect(
                partial(self._run_with_button_feedback, self.uninstall_button, "正在卸载回滚...", self._uninstall)
            )
            self.save_settings_button.clicked.connect(
                partial(self._run_with_button_feedback, self.save_settings_button, "正在保存配置...", self._save_settings)
            )
            self.test_translation_button.clicked.connect(
                partial(self._run_with_button_feedback, self.test_translation_button, "正在测试翻译...", self._test_translation)
            )
            self.clear_log_button.clicked.connect(self.log_output.clear)

            self.mode_combo.currentTextChanged.connect(self._update_mode_hint)
            self.mode_combo.currentTextChanged.connect(lambda _value: self._update_summary())
            self.machine_provider_combo.currentTextChanged.connect(self._apply_machine_provider_defaults)
            self.language_combo.currentTextChanged.connect(lambda _value: self._update_summary())
            self.host_edit.textChanged.connect(lambda _value: self._update_summary())
            self.port_spin.valueChanged.connect(lambda _value: self._update_summary())
            self.timeout_spin.valueChanged.connect(lambda _value: self._update_summary())
            self.llm_api_base_edit.textChanged.connect(lambda _value: self._update_summary())
            self.machine_api_base_edit.textChanged.connect(lambda _value: self._update_summary())
            self.game_dir_edit.textChanged.connect(lambda _value: self._update_summary())
            self.runtime_dir_edit.textChanged.connect(lambda _value: self._update_summary())

        def _register_clickable_widgets(self) -> None:
            for button in (
                self.inspect_game_button,
                self.inspect_runtime_button,
                self.import_runtime_button,
                self.start_bridge_button,
                self.stop_bridge_button,
                self.dry_run_button,
                self.install_button,
                self.uninstall_button,
                self.save_settings_button,
                self.test_translation_button,
                self.clear_log_button,
            ):
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setMinimumHeight(42)

        def _run_with_button_feedback(self, button: "QPushButton", status_text: str, callback) -> None:
            original_text = button.text()
            self.statusBar().showMessage(status_text)
            button.setEnabled(False)
            button.setText(f"{original_text}...")
            QApplication.processEvents()
            try:
                callback()
                self.statusBar().showMessage("操作完成", 3000)
            except Exception:
                self.statusBar().showMessage("操作失败，请查看日志", 5000)
                raise
            finally:
                button.setEnabled(True)
                button.setText(original_text)

        def _hint_label(self, text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("SectionHint")
            label.setWordWrap(True)
            return label

        def _build_browse_button(self, target_edit: "QLineEdit") -> "QPushButton":
            button = QPushButton("选择…")
            button.setObjectName("GhostButton")
            button.clicked.connect(lambda: self._choose_directory(target_edit))
            return button

        def _choose_directory(self, target_edit: "QLineEdit") -> None:
            path = QFileDialog.getExistingDirectory(
                self,
                "选择目录",
                target_edit.text() or str(Path.cwd()),
            )
            if path:
                target_edit.setText(path)
                self._update_summary()

        def _apply_defaults(self) -> None:
            runtime_dir = default_runtime_dir()
            source_game = Path(r"D:\newgame\田径选手.7z\田径选手\田径选手\1\2\LongJump")
            self.runtime_dir_edit.setText(str(runtime_dir))
            if source_game.exists():
                self.source_game_edit.setText(str(source_game))

        def _fill_settings_form(self, settings: TranslationSettings) -> None:
            self.mode_combo.setCurrentText(settings.mode)
            self.host_edit.setText(settings.local_host)
            self.port_spin.setValue(settings.local_port)
            self.timeout_spin.setValue(settings.request_timeout_sec)
            self.llm_api_base_edit.setText(settings.llm.api_base)
            self.llm_api_key_edit.setText(settings.llm.api_key)
            self.llm_model_edit.setText(settings.llm.model)
            self.llm_system_prompt_edit.setPlainText(settings.llm.system_prompt)
            self.machine_provider_combo.setCurrentText(settings.machine.provider)
            self.machine_api_base_edit.setText(settings.machine.api_base)
            self.machine_api_key_edit.setText(settings.machine.api_key)
            self.cache_path_label.setText(str(settings_dir() / "translation_cache.json"))

        def _get_current_settings(self) -> TranslationSettings:
            return TranslationSettings(
                mode=self.mode_combo.currentText(),
                local_host=self.host_edit.text().strip() or "127.0.0.1",
                local_port=self.port_spin.value(),
                request_timeout_sec=self.timeout_spin.value(),
                llm=LLMProviderSettings(
                    api_base=self.llm_api_base_edit.text().strip(),
                    api_key=self.llm_api_key_edit.text().strip(),
                    model=self.llm_model_edit.text().strip() or "gpt-4.1-mini",
                    system_prompt=self.llm_system_prompt_edit.toPlainText().strip()
                    or LLMProviderSettings().system_prompt,
                ),
                machine=MachineProviderSettings(
                    provider=self.machine_provider_combo.currentText(),
                    api_base=self.machine_api_base_edit.text().strip(),
                    api_key=self.machine_api_key_edit.text().strip(),
                ),
            )

        def _save_settings(self) -> None:
            settings = self._get_current_settings()
            issue = validate_translation_settings(settings)
            if issue is not None:
                raise ValueError(issue)
            result = save_settings_service(settings)
            self._settings = settings
            self._update_summary()
            self._update_mode_hint()
            self._append_log("[保存翻译配置] 成功")
            self._append_log(_to_pretty_json(result))
            self._set_operation_summary(
                "翻译配置已保存",
                "\n".join(
                    [
                        f"保存位置: {result['path']}",
                        f"模式: {settings.mode}",
                        f"本地接口: {settings.local_endpoint_url()}",
                    ]
                ),
            )
            QMessageBox.information(self, "保存翻译配置", "翻译配置已保存。")

        def _start_bridge(self) -> None:
            self._save_settings_silently()
            self._bridge.stop()
            self._bridge.start()
            self._update_bridge_status()
            self._update_summary()
            bridge_url = self._get_current_settings().local_endpoint_url()
            self._append_log(f"[启动翻译服务] 成功，地址: {bridge_url}")
            self._set_operation_summary(
                "翻译服务已启动",
                "\n".join(
                    [
                        f"监听地址: {bridge_url}",
                        "建议下一步: 先做一次干运行安装，确认路径和写入计划。",
                    ]
                ),
            )

        def _stop_bridge(self) -> None:
            self._bridge.stop()
            self._update_bridge_status()
            self._update_summary()
            self._append_log("[停止翻译服务] 已停止")
            self._set_operation_summary("翻译服务已停止", "如需继续安装或测试翻译，请重新启动本地翻译服务。")

        def _inspect_game(self) -> None:
            self._run_action(
                "检查游戏",
                lambda: inspect_game_service(self.game_dir_edit.text().strip()),
                validator=lambda: validate_game_dir_input(self.game_dir_edit.text()),
                result_formatter=self._format_game_inspection,
            )

        def _inspect_runtime(self) -> None:
            self._run_action(
                "检查运行时",
                lambda: inspect_runtime_service(self.runtime_dir_edit.text().strip()),
                validator=lambda: validate_runtime_dir_input(self.runtime_dir_edit.text()),
                result_formatter=self._format_runtime_inspection,
            )

        def _import_runtime(self) -> None:
            self._run_action(
                "导入运行时",
                lambda: import_runtime_service(
                    self.source_game_edit.text().strip(),
                    self.runtime_dir_edit.text().strip(),
                ),
                validator=self._validate_runtime_import,
                result_formatter=self._format_runtime_import,
            )

        def _dry_run_install(self) -> None:
            self._run_action(
                "干运行安装",
                lambda: install_service(
                    self.game_dir_edit.text().strip(),
                    self.runtime_dir_edit.text().strip(),
                    self.language_combo.currentText(),
                    dry_run=True,
                    translation_settings=self._get_current_settings(),
                ),
                validator=lambda: self._validate_install_inputs(require_runtime_import=False),
                result_formatter=lambda result: build_install_summary(result),
            )

        def _install(self) -> None:
            self._save_settings_silently()
            self._run_action(
                "正式安装",
                lambda: install_service(
                    self.game_dir_edit.text().strip(),
                    self.runtime_dir_edit.text().strip(),
                    self.language_combo.currentText(),
                    dry_run=False,
                    translation_settings=self._get_current_settings(),
                ),
                validator=lambda: self._validate_install_inputs(require_runtime_import=False),
                result_formatter=lambda result: build_install_summary(result),
                success_message="安装完成。请保持翻译服务运行后再启动游戏。",
            )

        def _uninstall(self) -> None:
            self._run_action(
                "卸载回滚",
                lambda: uninstall_service(self.game_dir_edit.text().strip()),
                validator=lambda: validate_game_dir_input(self.game_dir_edit.text()),
                result_formatter=lambda result: build_uninstall_summary(result),
                success_message="回滚完成。",
            )

        def _test_translation(self) -> None:
            self._save_settings_silently()
            if not self._bridge.is_running:
                self._bridge.start()
                self._update_bridge_status()
                self._update_summary()
            text = self.test_input_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "测试翻译", "请先输入一段测试文本。")
                return
            settings = self._get_current_settings()
            url = (
                f"{settings.local_endpoint_url()}?from=ja&to={self.language_combo.currentText()}"
                f"&text={urllib.parse.quote(text)}"
            )
            try:
                with urllib.request.urlopen(url, timeout=settings.request_timeout_sec) as response:
                    result = response.read().decode("utf-8")
                self.test_output_edit.setPlainText(result)
                self._append_log("[测试翻译] 成功")
                self._append_log(result)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                self._append_log(f"[测试翻译] 失败: HTTP {exc.code} {detail}")
                QMessageBox.critical(self, "测试翻译", detail or str(exc))
            except Exception as exc:  # noqa: BLE001
                self._append_log(f"[测试翻译] 失败: {exc}")
                self._append_log(traceback.format_exc())
                QMessageBox.critical(self, "测试翻译", str(exc))

        def _save_settings_silently(self) -> None:
            settings = self._get_current_settings()
            issue = validate_translation_settings(settings)
            if issue is not None:
                raise ValueError(issue)
            save_settings_service(settings)
            self._settings = settings
            self._update_summary()

        def _update_mode_hint(self) -> None:
            mode = self.mode_combo.currentText()
            if mode == "llm":
                self.mode_hint_label.setText(
                    "当前使用大模型翻译模式。游戏文本会先打到本地翻译服务，再转发到你配置的 OpenAI 兼容接口。"
                )
            else:
                self.mode_hint_label.setText(
                    "当前使用普通机翻模式。现在支持 DeepL 和 LibreTranslate，游戏文本会先打到本地翻译服务，再转发到机翻接口。"
                )
            self._update_summary()

        def _apply_machine_provider_defaults(self) -> None:
            provider = self.machine_provider_combo.currentText()
            if provider == "deepl" and not self.machine_api_base_edit.text().strip():
                self.machine_api_base_edit.setText("https://api-free.deepl.com/v2/translate")
            if provider == "libretranslate" and not self.machine_api_base_edit.text().strip():
                self.machine_api_base_edit.setText("https://libretranslate.com/translate")
            self._update_summary()

        def _update_bridge_status(self) -> None:
            if self._bridge.is_running:
                self.bridge_status_label.setText("运行中")
                self.bridge_status_label.setStyleSheet("color: #0a7a2f; font-weight: 600;")
            else:
                self.bridge_status_label.setText("未启动")
                self.bridge_status_label.setStyleSheet("color: #a33a00; font-weight: 600;")
            self._update_summary()

        def _update_summary(self) -> None:
            self.summary_game_value.setText(self._display_path(self.game_dir_edit.text().strip()))
            self.summary_runtime_value.setText(self._display_path(self.runtime_dir_edit.text().strip()))
            settings = self._get_current_settings()
            if settings.mode == "llm":
                endpoint = settings.llm.api_base or "未配置"
            else:
                endpoint = settings.machine.api_base or "未配置"
            self.summary_endpoint_value.setText(endpoint)
            cache_file = settings_dir() / "translation_cache.json"
            self.summary_cache_value.setText(self._display_path(str(cache_file)))
            self.summary_next_step_value.setText(
                suggest_next_step(
                    self.game_dir_edit.text(),
                    self.runtime_dir_edit.text(),
                    self.source_game_edit.text(),
                    settings,
                    self._bridge.is_running,
                )
            )
            self.hero_mode_pill.setText(f"模式：{'大模型' if settings.mode == 'llm' else '普通机翻'}")
            self.hero_bridge_pill.setText(f"服务：{'运行中' if self._bridge.is_running else '未启动'}")
            self.hero_cache_pill.setText("缓存：JSON 优先命中")

        def _display_path(self, value: str) -> str:
            if not value:
                return "未选择"
            if len(value) <= 52:
                return value
            return f"{value[:24]} ... {value[-24:]}"

        def _run_action(
            self,
            title: str,
            callback,
            success_message: str | None = None,
            validator: Callable[[], str | None] | None = None,
            result_formatter: Callable[[dict[str, object]], str] | None = None,
        ) -> None:
            try:
                if validator is not None:
                    issue = validator()
                    if issue is not None:
                        raise ValueError(issue)
                result = callback()
                self._append_log(f"[{title}] 成功")
                self._append_log(_to_pretty_json(result))
                if result_formatter is not None:
                    self._set_operation_summary(title, result_formatter(result))
                self._update_summary()
                if success_message:
                    QMessageBox.information(self, title, success_message)
            except Exception as exc:  # noqa: BLE001
                self._append_log(f"[{title}] 失败: {exc}")
                self._append_log(traceback.format_exc())
                self._set_operation_summary(title, f"失败\n{exc}")
                QMessageBox.critical(self, title, str(exc))

        def _append_log(self, message: str) -> None:
            self.log_output.appendPlainText(message)
            self.log_output.appendPlainText("")

        def _set_operation_summary(self, title: str, content: str) -> None:
            self.operation_summary_output.setPlainText(f"{title}\n\n{content}")

        def _validate_runtime_import(self) -> str | None:
            source_issue = validate_source_game_dir_input(self.source_game_edit.text())
            if source_issue is not None:
                return source_issue
            return validate_runtime_dir_input(self.runtime_dir_edit.text())

        def _validate_install_inputs(self, require_runtime_import: bool) -> str | None:
            game_issue = validate_game_dir_input(self.game_dir_edit.text())
            if game_issue is not None:
                return game_issue
            runtime_issue = validate_runtime_dir_input(self.runtime_dir_edit.text())
            if runtime_issue is not None:
                return runtime_issue
            settings_issue = validate_translation_settings(self._get_current_settings())
            if settings_issue is not None:
                return settings_issue
            if require_runtime_import and not self.source_game_edit.text().strip():
                return "当前运行时目录不可用时，请先选择样例源游戏目录并导入运行时。"
            return None

        def _format_game_inspection(self, result: dict[str, object]) -> str:
            return "\n".join(
                [
                    "游戏检查通过",
                    f"EXE: {result.get('exe_name', '未知')}",
                    f"数据目录: {result.get('data_dir', '未知')}",
                    f"Managed: {result.get('managed_dir', '未知')}",
                    f"架构: {result.get('architecture', '未知')}",
                    "结论: 这是当前工具可尝试处理的 Unity Mono 游戏目录。",
                ]
            )

        def _format_runtime_inspection(self, result: dict[str, object]) -> str:
            managed_files = result.get("managed_files", [])
            font_files = result.get("font_files", [])
            return "\n".join(
                [
                    "运行时检查通过",
                    f"运行时根目录: {result.get('root', '未知')}",
                    f"Managed 文件数: {len(managed_files) if isinstance(managed_files, list) else '未知'}",
                    f"字体文件数: {len(font_files) if isinstance(font_files, list) else '未知'}",
                    "建议下一步: 保存翻译配置并先做一次干运行安装。",
                ]
            )

        def _format_runtime_import(self, result: dict[str, object]) -> str:
            managed_files = result.get("managed_files", [])
            font_files = result.get("font_files", [])
            return "\n".join(
                [
                    "运行时导入完成",
                    f"运行时根目录: {result.get('root', '未知')}",
                    f"Managed 文件数: {len(managed_files) if isinstance(managed_files, list) else '未知'}",
                    f"字体文件数: {len(font_files) if isinstance(font_files, list) else '未知'}",
                    "建议下一步: 检查运行时 -> 保存配置 -> 干运行安装。",
                ]
            )

    def _to_pretty_json(data: object) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()
