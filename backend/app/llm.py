"""LLM layer: free OpenRouter models in order, Gemini last. See ARCHITECTURE.md section 12."""
import json
import re
import threading
import time

import httpx

from app import config


class LLMUnavailable(Exception):
    pass


class Stats:
    """Per-request counters, shared by all nodes through the graph config."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.calls = 0
        self.models: list[str] = []
        self.skipped: list[str] = []
        self.saved: dict = {}

    def ok(self, model: str) -> None:
        with self.lock:
            self.calls += 1
            self.models.append(model)

    def skip(self, model: str, why: str) -> None:
        with self.lock:
            self.skipped.append(f"{model}: {why}"[:160])


_SEM = threading.Semaphore(config.MAX_CONCURRENCY)
_cool: dict[str, float] = {}  # model -> time until which it is skipped after a failure
COOLDOWN = 60


def _providers() -> list[tuple[str, str, str]]:
    out = []
    if config.OPENROUTER_API_KEY:
        out += [(config.OPENROUTER_URL, config.OPENROUTER_API_KEY, m) for m in config.OPENROUTER_MODELS]
    if config.GOOGLE_API_KEY:
        out.append((config.GEMINI_URL, config.GOOGLE_API_KEY, config.MODEL_NAME))
    return out


def _post(url: str, key: str, model: str, messages: list, tools: list | None) -> dict:
    body = {"model": model, "messages": messages, "temperature": 0.2}
    if tools:
        body["tools"] = tools
    with _SEM:
        r = httpx.post(url, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=75)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    content = re.sub(r"<think>.*?</think>", "", msg.get("content") or "", flags=re.S).strip()
    calls = msg.get("tool_calls") or None
    if not content and not calls:
        raise ValueError("empty answer")
    return {"role": "assistant", "content": content, "tool_calls": calls}


def run(messages: list, stats: Stats, tools: list | None = None, accept=None):
    """Try each model in order. `accept(msg)` may raise to reject a bad answer (e.g. invalid JSON)."""
    for url, key, model in _providers():
        last = url == config.GEMINI_URL
        if not last and _cool.get(model, 0) > time.time():
            stats.skip(model, "cooling down")
            continue
        attempts = 2 if last else 1  # Gemini is the last resort, retry once on 503
        for attempt in range(attempts):
            try:
                msg = _post(url, key, model, messages, tools)
                out = accept(msg) if accept else msg
                stats.ok(model)
                return out
            except Exception as e:  # noqa: BLE001 - any failure means "try the next model"
                stats.skip(model, f"{type(e).__name__} {str(e)[:80]}")
                if not last:
                    _cool[model] = time.time() + COOLDOWN
                if attempt + 1 < attempts:
                    time.sleep(3)
    raise LLMUnavailable("all models failed")


def parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object")
    return json.loads(text[start : end + 1])
