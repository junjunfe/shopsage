"""OpenAI-compatible structured-output boundary with a deterministic offline fallback."""
from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelProvider:
    """Production deployments can implement complete() with OpenAI, Azure or vLLM.

    Business agents never call a provider directly: they request a Pydantic schema here,
    which keeps malformed model output outside the domain layer.
    """
    def __init__(self) -> None:
        self.base_url = os.getenv("SHOPGUIDE_MODEL_BASE_URL")
        self.api_key = os.getenv("SHOPGUIDE_MODEL_API_KEY")
        self.model = os.getenv("SHOPGUIDE_MODEL_NAME")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def complete(self, _prompt: str, schema: type[T]) -> T | None:
        # Network clients are deliberately not invoked in the offline demo. A real adapter
        # belongs here and must parse/validate against `schema` before returning data.
        return None
