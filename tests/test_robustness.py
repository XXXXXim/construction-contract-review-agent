"""결함 분석(2026-11-04)에서 찾은 문제들의 회귀 테스트."""

import json
from dataclasses import dataclass

import pytest

from contract_review.llm import CachedLLM
from contract_review.nodes.llm_judge import _parse, dedupe_findings, llm_judge, parse_baseline
from contract_review.nodes.retrieve_standard import retrieve_standard
from contract_review.nodes.split_clauses import split_clauses
from contract_review.retrieval import StandardIndex
from contract_review.schemas import Category, Clause, Finding, ParsedDocument, RetrievedRef, RiskLevel
from contract_review.standards import find_clause
from contract_review.textnorm import canon, contains_quote


# ── 결함 1: 조항 머리 형식 ──
@pytest.mark.parametrize(
    "header",
    ["제1조(목적)", "제 1 조 (목적)", "제1조 【목적】", "제1조[목적]", "제1조（목적）", "제1조 목적"],
)
def test_split_accepts_header_variants(header: str) -> None:
    text = f"{header}\n이 계약은 목적을 정한다.\n제2조(정의) 용어를 정한다."
    cs = split_clauses(ParsedDocument(doc_id="t", text=text, pages=1))
    assert [c.clause_id for c in cs] == ["제1조", "제2조"]
    assert cs[0].title == "목적"


def test_split_spaced_sub_article() -> None:
    cs = split_clauses(ParsedDocument(doc_id="t", text="제 3 조 의 2 (특례) 본문", pages=1))
    assert [c.clause_id for c in cs] == ["제3조의2"]


@pytest.mark.parametrize(
    "line",
    ["제4조 제2항을 준용한다.", "제5조 및 제6조에 따른다", "제7조에 따른 금액", "제8조 또는 제9조"],
)
def test_split_does_not_treat_references_as_headers(line: str) -> None:
    text = f"제1조(목적) 본문\n{line}"
    cs = split_clauses(ParsedDocument(doc_id="t", text=text, pages=1))
    assert [c.clause_id for c in cs] == ["제1조"]
    assert line.split()[0] in cs[0].text


# ── 결함 2: 문장부호 차이로 진짜 인용을 버림 ──
def test_quote_match_ignores_punctuation_variants() -> None:
    std = "어음할인료ㆍ수수료의 지급 및 「하도급거래 공정화에 관한 법률」 제13조"
    assert contains_quote(std, "어음할인료·수수료의 지급 및 '하도급거래 공정화에 관한 법률' 제13조")
    assert contains_quote(std, "어음할인료ㆍ수수료의 지급 … 공정화에 관한 법률")  # 생략 인용
    assert not contains_quote(std, "어음할인료ㆍ수수료의 지급 … 날조된 문장입니다")
    assert not contains_quote(std, "지급")  # 너무 짧은 인용
    assert canon("（가）") == canon("(가)")


def test_judge_keeps_real_quote_with_different_middle_dot() -> None:
    std = find_clause("ftc_standard_subcontract", "제56조")
    assert std is not None and "ㆍ" in std.text  # 원문은 U+318D ("관리ㆍ사용")
    ref = RetrievedRef(source_doc=std.doc_id, clause_id=std.clause_id, title=std.title, text=std.text, score=1.0)
    sent = next(s for s in std.text.split("\n") if "ㆍ" in s)[:80].replace("ㆍ", "·")  # LLM 은 U+00B7 로 씀
    clause = Clause(doc_id="t", clause_id="제3조", title="지체상금", text="제3조(지체상금) 지체상금을 청구한다.")
    stub = _Stub(
        [
            {
                "clause_id": "제3조",
                "category": "delay_penalty",
                "risk_level": "high",
                "standard_ref": f"{std.doc_id} {std.clause_id}",
                "deviation_summary": "x",
                "evidence_quote": sent,
            }
        ]
    )
    res = llm_judge(clause, [ref], [], stub, verify=True)
    assert res.dropped == 0 and len(res.findings) == 1


# ── 결함 5·7: JSON 파싱 ──
F = {
    "clause_id": "제1조",
    "category": "termination",
    "risk_level": "high",
    "standard_ref": "a 제1조",
    "deviation_summary": "x",
    "evidence_quote": "y",
}


def test_parse_variants() -> None:
    arr = json.dumps([F], ensure_ascii=False)
    assert _parse(arr) == [F]
    assert _parse(f"```json\n{arr}\n```") == [F]
    assert _parse("설명입니다.\n" + arr) == [F]
    assert _parse(json.dumps({"findings": [F]}, ensure_ascii=False)) == [F]
    assert _parse(json.dumps(F, ensure_ascii=False)) == [F]
    assert _parse("[]") == [] and _parse("문제 없음 []") == []
    assert _parse("죄송하지만 판단할 수 없습니다") is None


def test_parse_recovers_truncated_array() -> None:
    two = json.dumps([F, {**F, "clause_id": "제2조"}], ensure_ascii=False)
    truncated = two[:-1] + ', {"clause_id": "제3조", "category": "termi'
    got = _parse(truncated)
    assert [d["clause_id"] for d in got] == ["제1조", "제2조"]


def test_parse_baseline_handles_spaced_clause_id_and_unparsable() -> None:
    clauses = {"제1조": Clause(doc_id="t", clause_id="제1조", text="제1조(목적) x")}
    got = parse_baseline(json.dumps([{**F, "clause_id": "제 1 조"}], ensure_ascii=False), clauses)
    assert got and got[0].clause_id == "제1조"
    assert parse_baseline("모르겠습니다", clauses) is None


# ── 결함 6: 호출 실패가 평가 전체를 멈춤 ──
@dataclass
class _Stub:
    payload: list[dict]
    name: str = "stub"

    def complete(self, prompt: str) -> tuple[str, int, int]:
        return json.dumps(self.payload, ensure_ascii=False), 3, 2


@dataclass
class _Boom:
    name: str = "boom"
    calls: int = 0

    def complete(self, prompt: str) -> tuple[str, int, int]:
        self.calls += 1
        raise RuntimeError("429 rate limited")


def test_llm_error_is_isolated_per_clause() -> None:
    index = StandardIndex.build()
    clause = Clause(doc_id="t", clause_id="제1조", title="지체상금", text="제1조(지체상금) 지체상금을 청구한다.")
    res = llm_judge(clause, retrieve_standard(clause, index), [], _Boom())
    assert res.error and res.findings == []


def test_cached_llm_reuses_response(tmp_path) -> None:
    inner = _Stub([F])
    llm = CachedLLM(inner, tmp_path)
    a = llm.complete("p")
    b = llm.complete("p")
    assert a == b and llm.hits == 1 and len(list(tmp_path.iterdir())) == 1


# ── 결함 8: 중복 finding ──
def _f(src: str, risk: RiskLevel, cat: Category = Category.TERMINATION) -> Finding:
    return Finding(
        clause_id="제1조",
        category=cat,
        risk_level=risk,
        contract_text="",
        standard_ref="",
        deviation_summary="",
        evidence_quote="",
        source=src,
    )


def test_dedupe_prefers_rule_then_higher_risk() -> None:
    out = dedupe_findings([_f("llm", RiskLevel.HIGH), _f("rule", RiskLevel.MEDIUM), _f("llm", RiskLevel.LOW)])
    assert len(out) == 1 and out[0].source == "rule"
    out = dedupe_findings(
        [_f("llm", RiskLevel.LOW), _f("llm", RiskLevel.HIGH), _f("llm", RiskLevel.LOW, Category.OTHER)]
    )
    assert len(out) == 2 and {f.risk_level for f in out} == {RiskLevel.HIGH, RiskLevel.LOW}


# ── 11/08 드라이런: claude-sonnet-5-5 는 temperature 지정 시 호출 자체를 거부 ──
def test_anthropic_client_does_not_set_temperature(monkeypatch) -> None:
    """FR-11. 네트워크 호출 없이 클라이언트 설정만 확인한다."""
    from contract_review.config import Settings
    from contract_review.llm import get_llm

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-dummy")
    monkeypatch.delenv("LLM_CACHE", raising=False)
    llm = get_llm(Settings(llm_provider="anthropic"))
    assert llm.model.temperature is None
    assert llm.model.max_tokens >= 16000
