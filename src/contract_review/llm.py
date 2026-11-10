"""LLM provider 팩토리와 FakeLLM.

- `JudgeLLM` 프로토콜: 프롬프트 문자열 → (응답 텍스트, 입력 토큰, 출력 토큰)
- `fake`: API 키 없이 돌아가는 결정적 판정기. 계약서 조항과 표준 조항(top-1)의 문장 단위 차이를 찾아
  JSON finding 을 만든다. 테스트와 키 없는 환경의 기본값.
- `openai` / `anthropic`: langchain 채팅 모델. 키는 환경변수에서만 읽는다.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from contract_review.config import Settings
from contract_review.textnorm import canon, strip_header

_LOCK = threading.Lock()
DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-sonnet-5-5"}
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "5"))
# baseline 은 계약서 전체에 대한 지적을 한 번에 출력하므로 넉넉히 (잘리면 _parse 가 부분 복구)
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16000"))
CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "llm"


class JudgeLLM(Protocol):
    name: str

    def complete(self, prompt: str) -> tuple[str, int, int]: ...


@dataclass
class LangChainLLM:
    """langchain 채팅 모델 래퍼. 429/5xx 재시도는 모델의 max_retries(지수 백오프)가 맡는다.

    graph.n_judge 가 여러 스레드에서 동시에 부르므로 카운터는 락으로 보호한다.
    """

    name: str
    model: object  # BaseChatModel
    truncated_calls: int = 0  # max_tokens 에 걸려 잘린 응답 수

    def complete(self, prompt: str) -> tuple[str, int, int]:
        msg = self.model.invoke(prompt)  # type: ignore[attr-defined]
        meta = getattr(msg, "response_metadata", None) or {}
        if meta.get("stop_reason") == "max_tokens" or meta.get("finish_reason") == "length":
            with _LOCK:
                self.truncated_calls += 1
        usage = getattr(msg, "usage_metadata", None) or {}
        content = msg.content
        if isinstance(content, list):  # anthropic 블록 형식
            content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        return str(content), int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))


@dataclass
class CachedLLM:
    """프롬프트 → 응답 디스크 캐시 (LLM_CACHE=1). 평가 재실행 비용을 0 으로.

    캐시 적중 시 토큰 수는 원래 호출의 값을 돌려준다 (비용 지표 유지). 처리 시간은 의미가 없어지므로
    시간 비교가 필요한 평가는 캐시를 끄고 돌린다.
    """

    inner: JudgeLLM
    cache_dir: Path
    hits: int = 0

    @property
    def name(self) -> str:
        return self.inner.name

    @property
    def truncated_calls(self) -> int:
        return getattr(self.inner, "truncated_calls", 0)

    def complete(self, prompt: str) -> tuple[str, int, int]:
        key = hashlib.sha256(f"{self.inner.name}\n{prompt}".encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            with _LOCK:
                self.hits += 1
            return d["text"], d["input_tokens"], d["output_tokens"]
        text, tin, tout = self.inner.complete(prompt)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{threading.get_ident()}.tmp")  # 동시 쓰기 대비: 임시 파일 후 교체
        tmp.write_text(
            json.dumps({"text": text, "input_tokens": tin, "output_tokens": tout}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
        return text, tin, tout


_SENT = re.compile(r"(?<=[.。])\s+|\n")
_PARTY = re.compile(r"원사업자|수급사업자|발주자|도급인|수급인|갑|을")


_strip_header = strip_header


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(_strip_header(text)) if len(s.strip()) >= 8]


def _norm(s: str) -> str:
    return _PARTY.sub("P", canon(s))


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
    llm = _make_llm(settings)
    if settings.llm_provider != "fake" and os.getenv("LLM_CACHE", "0") == "1":
        return CachedLLM(llm, CACHE_DIR)
    return llm


def _make_llm(settings: Settings) -> JudgeLLM:
    p = settings.llm_provider
    if p == "fake":
        return FakeLLM()
    if p == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("LLM_PROVIDER=openai 인데 OPENAI_API_KEY 가 없음")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:  # 선택 설치 (pyproject [embedding])
            raise RuntimeError(
                "LLM_PROVIDER=openai 에는 langchain-openai 가 필요합니다: pip install -e '.[embedding]'"
            ) from e

        model = os.getenv("OPENAI_MODEL", DEFAULT_MODELS["openai"])
        return LangChainLLM(
            name=f"openai:{model}",
            model=ChatOpenAI(
                model=model, temperature=0, max_retries=MAX_RETRIES, timeout=120, max_tokens=MAX_OUTPUT_TOKENS
            ),
        )
    if p == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("LLM_PROVIDER=anthropic 인데 ANTHROPIC_API_KEY 가 없음")
        from langchain_anthropic import ChatAnthropic

        model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODELS["anthropic"])
        return LangChainLLM(
            name=f"anthropic:{model}",
            model=ChatAnthropic(
                # claude-sonnet-5-5 는 temperature 를 기본값 외로 지정하면 거부한다 (11/08 드라이런에서 확인).
                # baseline 은 출력이 길어서 timeout 을 넉넉히 둔다.
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                max_retries=MAX_RETRIES,
                timeout=600,
            ),
        )
    raise ValueError(f"알 수 없는 LLM_PROVIDER: {p}")
