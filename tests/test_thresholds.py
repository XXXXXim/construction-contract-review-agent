"""기준값 하나하나가 원문에 실제로 있는 문장을 출처로 갖는지 검증한다 (CLAUDE.md 규칙 1)."""

import pytest

from contract_review.schemas import Category
from contract_review.standards import quote_in_clause
from contract_review.thresholds import load_thresholds, thresholds_for


@pytest.mark.parametrize("t", load_thresholds(), ids=lambda t: t.id)
def test_threshold_quote_exists_in_source(t) -> None:
    assert quote_in_clause(t.quote, t.source_doc, t.clause_id), (
        f"{t.id}: 인용문이 {t.source_doc} {t.clause_id} 본문에 없음"
    )
    if t.standard_ref:
        r = t.standard_ref
        assert quote_in_clause(r.quote, r.source_doc, r.clause_id), (
            f"{t.id}: standard_ref 인용문이 {r.source_doc} {r.clause_id} 본문에 없음"
        )


def test_numeric_thresholds_cover_rule_categories() -> None:
    assert {t.id for t in thresholds_for(Category.PAYMENT_DEADLINE)} >= {
        "payment_deadline_days",
        "payment_after_owner_days",
    }
    assert any(t.id == "design_change_adjust_days" for t in thresholds_for(Category.DESIGN_CHANGE))


def test_todo_values_are_excluded_from_rule_thresholds() -> None:
    ids = {t.id for t in thresholds_for(Category.DELAY_PENALTY)}
    assert "delay_penalty_rate" not in ids  # TODO(source-needed) 는 규칙에 쓰지 않는다
