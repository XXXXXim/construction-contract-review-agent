"""LLM provider 팩토리와 FakeLLM.

- `JudgeLLM` 프로토콜: 프롬프트 문자열 → (응답 텍스트, 입력 토큰, 출력 토큰)
- `fake`: API 키 없이 돌아가는 결정적 판정기. 계약서 조항과 표준 조항(top-1)의 문장 단위 차이를 찾아
  JSON finding 을 만든다. 테스트와 키 없는 환경의 기본값.
- `openai` / `anthropic`: langchain 채팅 모델. 키는 환경변수에서만 읽는다.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

from contract_review.config import Settings

DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-sonnet-4-5"}


class JudgeLLM(Protocol):
    name: str

    def complete(self, prompt: str) -> tuple[str, int, int]: ...


@dataclass
class LangChainLLM:
    name: str
    model: object  # BaseChatModel

    def complete(self, prompt: str) -> tuple[str, int, int]:
        msg = self.model.invoke(prompt)  # type: ignore[attr-defined]
        usage = getattr(msg, "usage_metadata", None) or {}
        text = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
        return text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))


_SENT = re.compile(r"(?<=[.。])\s+|\n")
_PARTY = re.compile(r"원사업자|수급사업자|발주자|도급인|수급인|갑|을")


_HEADER = re.compile(r"^\s*제\d+조(?:의\d+)?\s*\([^)]*\)\s*")


def _strip_header(text: str) -> str:
    """'제n조(제목)' 머리를 뗀다. 계약서는 조 번호가 표준과 달라서 비교에서 제외."""
    return _HEADER.sub("", text, count=1)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(_strip_header(text)) if len(s.strip()) >= 8]


def _norm(s: str) -> str:
    return _PARTY.sub("P", re.sub(r"\s+", "", s))


@dataclass
class FakeLLM:
    """결정적 판정기. 프롬프트 안의 <contract>/<standard …> 블록을 읽어 문장 차이를 finding 으로 낸다.

    프롬프트 형식은 nodes/llm_judge.py 의 build_prompt 와 맞춰져 있다 (테스트가 이를 검증).
    """

    name: str = "fake"

    def complete(self, prompt: str) -> tuple[str, int, int]:
        contract = re.search(r"<contract clause_id=\"([^\"]+)\">\n(.*?)\n</contract>", prompt, re.S)
        standards = re.findall(
            r"<standard doc=\"([^\"]+)\" clause_id=\"([^\"]+)\" category=\"([^\"]+)\">\n(.*?)\n</standard>",
            prompt,
            re.S,
        )
        if not contract or not standards:
            return "[]", 0, 0
        clause_id, ctext = contract.group(1), contract.group(2)
        doc, std_cid, category, stext = standards[0]  # top-1 과만 비교
        cnorm = _norm(_strip_header(ctext))
        changed = [s for s in _sentences(stext) if _norm(s) not in cnorm]
        if not changed or category == "other":
            return "[]", 0, 0
        quote = changed[0]
        finding = {
            "clause_id": clause_id,
            "category": category,
            "risk_level": "medium",
            "standard_ref": f"{doc} {std_cid}",
            "deviation_summary": f"표준 조항의 문장이 계약서에서 바뀌거나 빠짐 (fake 판정, 문장 {len(changed)}개 차이)",
            "evidence_quote": quote,
        }
        return json.dumps([finding], ensure_ascii=False), 0, 0


def get_llm(settings: Settings) -> JudgeLLM:
    p = settings.llm_provider
    if p == "fake":
        return FakeLLM()
    if p == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("LLM_PROVIDER=openai 인데 OPENAI_API_KEY 가 없음")
        from langchain_openai import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", DEFAULT_MODELS["openai"])
        return LangChainLLM(name=f"openai:{model}", model=ChatOpenAI(model=model, temperature=0))
    if p == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("LLM_PROVIDER=anthropic 인데 ANTHROPIC_API_KEY 가 없음")
        from langchain_anthropic import ChatAnthropic

        model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODELS["anthropic"])
        return LangChainLLM(
            name=f"anthropic:{model}",
            model=ChatAnthropic(model=model, temperature=0, max_tokens=4096),
        )
    raise ValueError(f"알 수 없는 LLM_PROVIDER: {p}")
