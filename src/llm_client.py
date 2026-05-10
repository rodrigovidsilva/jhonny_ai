from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class LLMClient(Protocol):
    provider: str

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> str:
        ...


class LLMNotConfiguredError(RuntimeError):
    pass


class DatabricksLLMClient:
    """Small Databricks Model Serving chat client.

    Databricks serving endpoints expose an OpenAI-compatible `/invocations`
    payload for chat models. Keeping this behind `LLMClient` lets us swap the
    provider without changing the retail agent orchestration.
    """

    def __init__(
        self,
        host: str,
        token: str,
        endpoint: str,
        timeout_seconds: int = 45,
    ) -> None:
        self.provider = "databricks"
        self.host = host.rstrip("/")
        self.token = token
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "DatabricksLLMClient":
        host = os.getenv("DATABRICKS_HOST", "").strip()
        token = os.getenv("DATABRICKS_TOKEN", "").strip()
        endpoint = os.getenv("DATABRICKS_MODEL_ENDPOINT", "").strip()
        if not host or not token or not endpoint:
            raise LLMNotConfiguredError(
                "Set DATABRICKS_HOST, DATABRICKS_TOKEN, and DATABRICKS_MODEL_ENDPOINT to enable LLM calls."
            )
        return cls(host=host, token=token, endpoint=endpoint)

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> str:
        url = f"{self.host}/serving-endpoints/{self.endpoint}/invocations"
        payload = {
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": temperature,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Databricks LLM request failed: {exc.code} {body}") from exc

        return self._extract_text(raw)

    def _extract_text(self, response: dict) -> str:
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content

        predictions = response.get("predictions")
        if isinstance(predictions, list) and predictions:
            first = predictions[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                content = first.get("content") or first.get("text")
                if isinstance(content, str):
                    return content

        raise RuntimeError(f"Unable to parse Databricks LLM response: {response}")


class OpenAILLMClient:
    """Small OpenAI Chat Completions client for the Jhonny assistant."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: int = 45,
    ) -> None:
        self.provider = "openai"
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "OpenAILLMClient":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        if not api_key:
            raise LLMNotConfiguredError("Set OPENAI_API_KEY to enable OpenAI LLM calls.")
        return cls(api_key=api_key, model=model)

    def complete(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": temperature,
        }
        body_bytes = json.dumps(payload).encode("utf-8")

        # Retry on 429 (rate limit) and 5xx (transient server errors) with
        # exponential backoff. This dramatically reduces fallbacks under load.
        max_retries = 4
        base_delay = 1.5
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body_bytes,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                choices = raw.get("choices")
                if isinstance(choices, list) and choices:
                    message = choices[0].get("message", {})
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                raise RuntimeError(f"Unable to parse OpenAI LLM response: {raw}")
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_exc = RuntimeError(f"OpenAI LLM request failed: {exc.code} {body}")
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt < max_retries:
                        time.sleep(base_delay * (2 ** attempt))
                        continue
                raise last_exc from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_exc = RuntimeError(f"OpenAI LLM request transport error: {exc}")
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise last_exc from exc
        raise last_exc or RuntimeError("OpenAI LLM call failed after retries")
