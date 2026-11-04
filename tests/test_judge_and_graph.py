import json
from dataclasses import dataclass
from pathlib import Path

from contract_review.config import Settings
from contract_review.graph import Pipeline
from contract_review.llm import FakeLLM
from contract_review.nodes.llm_judge import build_prompt, llm_judge
from contract_review.nodes.retrieve_standard import retrieve_standard
from contract_review.retrieval import StandardIndex
from contract_review.schemas import DISCLAIMER, Category, Clause

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class StubLLM:
    payload: list[dict]
    name: str = "stub"

    def complete(self, prompt: str) -> tuple[str, int, int]:
        return json.dumps(self.payload, ensure_ascii=False), 10, 5


def _clause() -> Clause:
    return Clause(
        doc_id="t",
        clause_id="제3조",
        title="지체상금",
        text="제3조(지체상금) 을이 계약 이행을 지체하면 갑은 지체일수에 요율을 곱한 지체상금을 청구할 수 있다.",
    )


def test_fabricated_evidence_is_dropped_but_real_quote_kept() -> None:
    index = StandardIndex.build()
    clause = _clause()
    refs = retrieve_standard(clause, index)
    real = "수급사업자가 정당한 사유없이 계약의 이행을 지체한 경우"
    stub = StubLLM(
        [
            {
                "clause_id": "제3조",
                "category": "delay_penalty",
                "risk_level": "high",
                "standard_ref": "ftc_standard_subcontract 제56조",
                "deviation_summary": "진짜",
                "evidence_quote": real,
            },
            {
                "clause_id": "제3조",
                "category": "delay_penalty",
                "risk_level": "high",
                "standard_ref": "ftc_standard_subcontract 제56조",
                "deviation_summary": "지어냄",
                "evidence_quote": "지체상금은 계약금액의 100분의 30을 상한으로 한다",
            },
        ]
    )
    res = llm_judge(clause, refs, [], stub, verify=True)
    assert len(res.findings) == 1 and res.dropped == 1
    assert res.findings[0].standard_ref == "표준하도급계약서 제56조"
    assert res.input_tokens == 10 and res.output_tokens == 5
    # 검증을 끄면(v1) 둘 다 남는다
    assert len(llm_judge(clause, refs, [], stub, verify=False).findings) == 2


def test_fake_llm_reads_prompt_format_and_finds_diff() -> None:
    index = StandardIndex.build()
    clause = _clause()
    raw, _, _ = FakeLLM().complete(build_prompt(clause, retrieve_standard(clause, index), []))
    data = json.loads(raw)
    assert data and data[0]["category"] == "delay_penalty"
    assert data[0]["standard_ref"] == "ftc_standard_subcontract 제56조"


def test_e2e_v2_with_fake_llm_on_synthetic_contract() -> None:
    settings = Settings(llm_provider="fake", embedding_provider="none")
    pipe = Pipeline("v2", settings=settings)
    out = pipe.run(ROOT / "data" / "synthetic" / "synthetic_contract_01.txt")
    report = out["report"]
    assert report.stats.clause_count == 50
    assert report.disclaimer == DISCLAIMER and DISCLAIMER in out["report_md"]
    assert report.findings, "fake 판정기라도 변형 조항은 잡아야 한다"
    assert any(f.source == "rule" for f in report.findings)
    assert report.stats.llm_calls == 50
    # 모든 finding 의 근거는 기준 문서에 실제로 있다 (v2 검증)
    from contract_review.standards import quote_in_any_standard

    assert all(quote_in_any_standard(f.evidence_quote) for f in report.findings)


def test_baseline_graph_runs_with_fake_llm() -> None:
    settings = Settings(llm_provider="fake", embedding_provider="none")
    out = Pipeline("baseline", settings=settings).run(ROOT / "data" / "synthetic" / "synthetic_contract_02.txt")
    assert out["report"].config == "baseline" and out["report"].stats.llm_calls == 1
    assert Category  # enum import 사용
