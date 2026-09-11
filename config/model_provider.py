"""OpenAI-compatible inference boundary with a deterministic offline fallback."""
from __future__ import annotations

import json
import os
from typing import TypeVar
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelProvider:
    """Provide validated inference and embedding access through OpenAI-compatible APIs."""
    def __init__(self) -> None:
        self.base_url = os.getenv("SHOPGUIDE_MODEL_BASE_URL")
        self.api_key = os.getenv("SHOPGUIDE_MODEL_API_KEY")
        self.model = os.getenv("SHOPGUIDE_MODEL_NAME")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def _post(self, path: str, payload: dict) -> dict | None:
        if not self.enabled:
            return None
        request = Request(
            f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError):
            return None

    def complete(self, prompt: str, schema: type[T]) -> T | None:
        """Returns validated structured output or None so callers can use the rule fallback."""
        result = self._post("chat/completions", {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only JSON that matches the requested schema."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        })
        if not result:
            return None
        try:
            content = result["choices"][0]["message"]["content"]
            return schema.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    def embed(self, text: str) -> list[float] | None:
        result = self._post("embeddings", {"model": os.getenv("SHOPGUIDE_EMBEDDING_MODEL", self.model), "input": text})
        try:
            return result["data"][0]["embedding"] if result else None
        except (KeyError, IndexError, TypeError):
            return None
