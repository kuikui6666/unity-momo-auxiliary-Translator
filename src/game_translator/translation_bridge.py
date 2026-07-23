from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .cache_store import TranslationCacheStore
from .models import TranslationSettings


class TranslationBridgeServer:
    def __init__(self, settings_provider) -> None:
        self._settings_provider = settings_provider
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._cache_store = TranslationCacheStore()

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        settings = self._settings_provider()
        handler = self._build_handler()
        server = ThreadingHTTPServer((settings.local_host, settings.local_port), handler)
        server.bridge = self  # type: ignore[attr-defined]
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        settings: TranslationSettings = self._settings_provider()
        backend_fingerprint = _build_backend_fingerprint(settings)
        cache_key = self._cache_store.build_cache_key(
            mode=settings.mode,
            source_lang=source_lang,
            target_lang=target_lang,
            text=text,
            backend_fingerprint=backend_fingerprint,
        )
        cached = self._cache_store.get(cache_key)
        if cached is not None:
            return cached

        if settings.mode == "llm":
            translated = _translate_via_llm(text, source_lang, target_lang, settings)
        else:
            translated = _translate_via_machine(text, source_lang, target_lang, settings)

        self._cache_store.put(
            cache_key=cache_key,
            source_text=text,
            translation=translated,
            metadata={
                "mode": settings.mode,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "backend": backend_fingerprint,
            },
        )
        return translated

    def _build_handler(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/health":
                    self._write_json({"status": "ok"})
                    return
                if parsed.path != "/translate":
                    self.send_error(404, "Not Found")
                    return
                query = urllib.parse.parse_qs(parsed.query)
                text = query.get("text", [""])[0]
                source_lang = query.get("from", ["auto"])[0]
                target_lang = query.get("to", ["zh"])[0]
                try:
                    result = bridge.translate(text, source_lang, target_lang)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(result.encode("utf-8"))
                except Exception as exc:  # noqa: BLE001
                    self._write_json({"error": str(exc)}, status=500)

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return

            def _write_json(self, payload: dict[str, object], status: int = 200) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        return Handler


def _translate_via_llm(
    text: str,
    source_lang: str,
    target_lang: str,
    settings: TranslationSettings,
) -> str:
    if not settings.llm.api_key:
        raise ValueError("当前是大模型模式，但还没有配置 API Key。")
    if not settings.llm.api_base:
        raise ValueError("当前是大模型模式，但还没有配置 API Base。")

    prompt = (
        f"Source language: {source_lang}\n"
        f"Target language: {target_lang}\n"
        f"Text:\n{text}"
    )
    body = {
        "model": settings.llm.model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": settings.llm.system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    response = _post_json(
        url=settings.llm.api_base,
        body=body,
        headers={
            "Authorization": f"Bearer {settings.llm.api_key}",
        },
        timeout=settings.request_timeout_sec,
    )
    try:
        return response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"大模型响应格式无法解析: {response}") from exc


def _translate_via_machine(
    text: str,
    source_lang: str,
    target_lang: str,
    settings: TranslationSettings,
) -> str:
    provider = settings.machine.provider.lower()
    if provider == "deepl":
        return _translate_via_deepl(text, source_lang, target_lang, settings)
    if provider == "libretranslate":
        return _translate_via_libretranslate(text, source_lang, target_lang, settings)
    raise ValueError(f"不支持的机翻提供方: {settings.machine.provider}")


def _translate_via_deepl(
    text: str,
    source_lang: str,
    target_lang: str,
    settings: TranslationSettings,
) -> str:
    if not settings.machine.api_key:
        raise ValueError("当前是机翻模式，但 DeepL API Key 为空。")
    if not settings.machine.api_base:
        raise ValueError("当前是机翻模式，但 DeepL API Base 为空。")

    payload: dict[str, str] = {
        "auth_key": settings.machine.api_key,
        "text": text,
        "target_lang": _normalize_deepl_lang(target_lang, is_target=True),
    }
    normalized_source = _normalize_deepl_lang(source_lang, is_target=False)
    if normalized_source and normalized_source != "AUTO":
        payload["source_lang"] = normalized_source

    response = _post_form(
        url=settings.machine.api_base,
        body=payload,
        timeout=settings.request_timeout_sec,
    )
    try:
        return response["translations"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"DeepL 响应格式无法解析: {response}") from exc


def _translate_via_libretranslate(
    text: str,
    source_lang: str,
    target_lang: str,
    settings: TranslationSettings,
) -> str:
    if not settings.machine.api_base:
        raise ValueError("当前是机翻模式，但 LibreTranslate API Base 为空。")

    payload = {
        "q": text,
        "source": _normalize_basic_lang(source_lang, default="auto"),
        "target": _normalize_basic_lang(target_lang, default="zh"),
        "format": "text",
    }
    if settings.machine.api_key:
        payload["api_key"] = settings.machine.api_key

    response = _post_json(
        url=settings.machine.api_base,
        body=payload,
        timeout=settings.request_timeout_sec,
    )
    try:
        return str(response["translatedText"]).strip()
    except (KeyError, TypeError) as exc:
        raise ValueError(f"LibreTranslate 响应格式无法解析: {response}") from exc


def _post_json(
    *,
    url: str,
    body: dict[str, object],
    timeout: int,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    request_headers = {
        "Content-Type": "application/json",
        **(headers or {}),
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"远端接口返回 HTTP {exc.code}: {detail}") from exc


def _post_form(
    *,
    url: str,
    body: dict[str, str],
    timeout: int,
) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(body).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"远端接口返回 HTTP {exc.code}: {detail}") from exc


def _normalize_basic_lang(lang: str, default: str) -> str:
    value = (lang or default).strip().lower()
    if not value:
        return default
    return value


def _normalize_deepl_lang(lang: str, *, is_target: bool) -> str:
    value = (lang or "auto").strip().lower()
    mapping = {
        "auto": "AUTO",
        "zh": "ZH-HANS" if is_target else "ZH",
        "zh-cn": "ZH-HANS" if is_target else "ZH",
        "zh-tw": "ZH-HANT" if is_target else "ZH",
        "en": "EN",
        "ja": "JA",
        "ko": "KO",
        "de": "DE",
        "fr": "FR",
        "ru": "RU",
    }
    return mapping.get(value, value.upper())


def _build_backend_fingerprint(settings: TranslationSettings) -> str:
    if settings.mode == "llm":
        return "|".join(
            [
                "llm",
                settings.llm.api_base.strip(),
                settings.llm.model.strip(),
            ]
        )
    return "|".join(
        [
            "machine",
            settings.machine.provider.strip().lower(),
            settings.machine.api_base.strip(),
        ]
    )
