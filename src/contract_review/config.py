"""환경변수 기반 설정. API 키 값은 절대 출력하지 않는다."""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

LLMProvider = Literal["fake", "openai", "anthropic"]
EmbeddingProvider = Literal["none", "openai"]


class Settings(BaseModel):
    llm_provider: LLMProvider = "fake"
    embedding_provider: EmbeddingProvider = "none"
    has_openai_key: bool = False
    has_anthropic_key: bool = False

    def __repr__(self) -> str:  # 키 자체는 보관하지 않음
        return (
            f"Settings(llm={self.llm_provider}, emb={self.embedding_provider}, "
            f"openai_key={'set' if self.has_openai_key else 'unset'}, "
            f"anthropic_key={'set' if self.has_anthropic_key else 'unset'})"
        )


def load_settings() -> Settings:
    load_dotenv(override=False)
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "fake"),  # type: ignore[arg-type]
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "none"),  # type: ignore[arg-type]
        has_openai_key=bool(os.getenv("OPENAI_API_KEY")),
        has_anthropic_key=bool(os.getenv("ANTHROPIC_API_KEY")),
    )
