from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GameInfo:
    game_dir: Path
    exe_path: Path
    exe_name: str
    data_dir: Path
    managed_dir: Path
    engine: str
    architecture: str
    is_unity_mono: bool
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RuntimeInfo:
    root: Path
    auto_translator_dir: Path
    rei_patcher_dir: Path
    managed_files: list[Path]
    font_files: list[Path]


@dataclass(slots=True)
class InstallPlan:
    game: GameInfo
    runtime: RuntimeInfo
    target_language: str
    operations: list[str]


@dataclass(slots=True)
class LLMProviderSettings:
    api_base: str = "https://api.openai.com/v1/chat/completions"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    system_prompt: str = (
        "You are a professional video game translator. "
        "Translate the user text into the target language accurately, naturally, "
        "and concisely. Preserve speaker tone, special symbols, line breaks, and placeholders. "
        "Return only the translated text."
    )


@dataclass(slots=True)
class MachineProviderSettings:
    provider: str = "deepl"
    api_base: str = "https://api-free.deepl.com/v2/translate"
    api_key: str = ""


@dataclass(slots=True)
class TranslationSettings:
    mode: str = "llm"
    local_host: str = "127.0.0.1"
    local_port: int = 14366
    request_timeout_sec: int = 60
    llm: LLMProviderSettings = field(default_factory=LLMProviderSettings)
    machine: MachineProviderSettings = field(default_factory=MachineProviderSettings)

    def local_endpoint_url(self) -> str:
        return f"http://{self.local_host}:{self.local_port}/translate"

    def healthcheck_url(self) -> str:
        return f"http://{self.local_host}:{self.local_port}/health"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TranslationSettings":
        if not data:
            return cls()
        llm_data = data.get("llm") or {}
        machine_data = data.get("machine") or {}
        return cls(
            mode=data.get("mode", "llm"),
            local_host=data.get("local_host", "127.0.0.1"),
            local_port=int(data.get("local_port", 14366)),
            request_timeout_sec=int(data.get("request_timeout_sec", 60)),
            llm=LLMProviderSettings(
                api_base=llm_data.get("api_base", "https://api.openai.com/v1/chat/completions"),
                api_key=llm_data.get("api_key", ""),
                model=llm_data.get("model", "gpt-4.1-mini"),
                system_prompt=llm_data.get(
                    "system_prompt",
                    LLMProviderSettings().system_prompt,
                ),
            ),
            machine=MachineProviderSettings(
                provider=machine_data.get("provider", "deepl"),
                api_base=machine_data.get("api_base", "https://api-free.deepl.com/v2/translate"),
                api_key=machine_data.get("api_key", ""),
            ),
        )
