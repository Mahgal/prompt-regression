"""Model providers.

Two built-ins:

* ``mock`` — deterministic, offline, zero cost. Rules are documented below
  and in the README so demo outputs are predictable and tests can rely on them.
* ``openai-compatible`` — POSTs to any OpenAI-compatible ``/chat/completions``
  endpoint using only the standard library. The API key is read from an
  environment variable at call time; it is never stored, logged or defaulted
  to a literal value anywhere in this codebase.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    pass


class BaseProvider(ABC):
    name = "base"

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """Predictable fake answers. Rules, checked in order (case-insensitive):

    1. prompt mentions JSON          -> a fixed valid-JSON object
    2. prompt mentions sentiment     -> positive / negative / neutral
       (looks for love/great/excellent vs. hate/terrible/awful in the prompt)
    3. prompt mentions Spanish + translate -> a short Spanish greeting
    4. prompt asks the capital of France   -> sentence naming Paris
    5. prompt mentions summarise/summarize -> a one-line summary (<= 120 chars)
    6. prompt mentions hello / greet       -> a greeting containing "Hello"
    7. fallback                      -> "Mock response to: <first 80 chars>"
    """

    name = "mock"

    def generate(self, prompt: str) -> str:
        low = prompt.lower()
        if "json" in low:
            return '{"status": "ok", "result": "success", "count": 42}'
        if "sentiment" in low:
            if any(w in low for w in ("love", "great", "excellent", "wonderful")):
                return "positive"
            if any(w in low for w in ("hate", "terrible", "awful", "worst")):
                return "negative"
            return "neutral"
        if "translate" in low and "spanish" in low:
            return "Hola, gracias por tu mensaje."
        if "capital" in low and "france" in low:
            return "The capital of France is Paris."
        if "summar" in low:  # summarise / summarize / summary
            return "Summary: The main point is concise and clear."
        if "hello" in low or "greet" in low:
            return "Hello! Welcome, nice to meet you."
        return f"Mock response to: {prompt.strip()[:80]}"


class OpenAICompatibleProvider(BaseProvider):
    """Call any OpenAI-compatible chat-completions endpoint over HTTP.

    Parameters are configuration only — the key comes from ``api_key_env``
    (default ``OPENAI_API_KEY``) read from the process environment.
    """

    name = "openai-compatible"

    def __init__(self, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini",
                 api_key_env: str = "OPENAI_API_KEY",
                 timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        api_key = os.environ.get(self.api_key_env, "")
        if not api_key:
            raise ProviderError(
                f"environment variable {self.api_key_env} is not set; "
                "export it in your shell before using the openai-compatible provider"
            )
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"request to {self.base_url} failed: {exc}") from exc
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected response shape from endpoint: {exc}") from exc


def get_provider(name: str, **kwargs) -> BaseProvider:
    if name == "mock":
        return MockProvider()
    if name == "openai-compatible":
        return OpenAICompatibleProvider(**{k: v for k, v in kwargs.items() if v is not None})
    raise ProviderError(f"unknown provider {name!r} (choose: mock, openai-compatible)")
