"""평가 하네스 자체가 끝까지 돌고 지표를 계산하는지 (fake 판정기)."""

from contract_review import eval as ev


def test_run_eval_v2_and_baseline_produce_metrics() -> None:
    r = ev.run_eval("v2", "fake")
    assert r["labels"] == 24 and r["contracts"] == 3
    for k in ("recall", "precision", "citation_accuracy", "retrieval_hit3"):
        assert r[k] is not None and 0.0 <= r[k] <= 1.0
    assert r["llm_errors"] == 0 and r["unparsed_responses"] == 0
    md = ev.render_result(r)
    assert "Recall" in md and "LLM 호출 실패" in md
    b = ev.run_eval("baseline", "fake")
    assert b["retrieval_hit3"] is None and b["avg_llm_calls"] == 1


def test_precision_counts_unique_clause_category(monkeypatch) -> None:
    from datetime import datetime

    from contract_review.schemas import Category, EvalCase, Finding, ReviewReport, RiskLevel

    f = Finding(
        clause_id="제1조",
        category=Category.TERMINATION,
        risk_level=RiskLevel.HIGH,
        contract_text="",
        standard_ref="표준하도급계약서 제58조",
        deviation_summary="",
        evidence_quote="",
    )
    rep = ReviewReport(contract_id="c", generated_at=datetime.now(), config="x", findings=[f, f, f])
    case = EvalCase(
        contract_id="c",
        clause_id="제1조",
        category=Category.TERMINATION,
        expected_risk=RiskLevel.HIGH,
        injected_change="x",
        standard_clause_id="제58조",
    )
    s = ev.score(rep, [case], None)
    assert s["findings"] == 1 and s["tp"] == 1 and s["cite_ok"] == 1


def test_results_keep_findings_detail_for_error_analysis() -> None:
    """FR-13. 결과 파일만으로 오탐·인용을 분석할 수 있어야 한다."""
    r = ev.run_eval("v2", "fake")
    detail = r["per_contract"]["synthetic_contract_01"]["findings_detail"]
    assert detail and {"clause_id", "standard_ref", "label"} <= set(detail[0])


def test_run_eval_on_dataset_v2() -> None:
    r = ev.run_eval("v2", "fake", dataset="v2")
    assert r["dataset"] == "set-v2" and r["labels"] == 24
