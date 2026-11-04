from datetime import datetime

import pytest
from pydantic import ValidationError

from contract_review.config import load_settings
from contract_review.schemas import (
    DISCLAIMER,
    Category,
    EvalCase,
    Finding,
    ReviewReport,
    RiskLevel,
)


def _finding(risk: RiskLevel) -> Finding:
    return Finding(
        clause_id="제1조",
        category=Category.PAYMENT_DEADLINE,
        risk_level=risk,
        contract_text="...",
        standard_ref="표준하도급계약서 제1조",
        deviation_summary="...",
        evidence_quote="...",
    )


def test_report_sorted_by_risk_and_has_disclaimer() -> None:
    report = ReviewReport(
        contract_id="c1",
        generated_at=datetime(2026, 11, 4),
        config="v2",
        findings=[_finding(RiskLevel.LOW), _finding(RiskLevel.HIGH), _finding(RiskLevel.MEDIUM)],
    )
    assert [f.risk_level for f in report.sorted_findings()] == [
        RiskLevel.HIGH,
        RiskLevel.MEDIUM,
        RiskLevel.LOW,
    ]
    assert report.disclaimer == DISCLAIMER


def test_finding_rejects_bad_source() -> None:
    with pytest.raises(ValidationError):
        Finding(**{**_finding(RiskLevel.LOW).model_dump(), "source": "guess"})


def test_eval_case_parses() -> None:
    case = EvalCase.model_validate(
        {
            "contract_id": "synthetic_01",
            "clause_id": "제5조",
            "category": "delay_penalty",
            "expected_risk": "high",
            "injected_change": "지체상금률 변경",
        }
    )
    assert case.category is Category.DELAY_PENALTY


def test_settings_default_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    s = load_settings()
    assert s.llm_provider == "fake"
    assert s.embedding_provider == "none"
