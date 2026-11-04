from contract_review.nodes.retrieve_standard import retrieve_standard
from contract_review.nodes.rule_check import rule_check
from contract_review.retrieval import StandardIndex
from contract_review.schemas import Category, Clause, RiskLevel
from contract_review.standards import load_standard_clauses


def _std(cid: str) -> Clause:
    return next(c for c in load_standard_clauses()["ftc_standard_subcontract"] if c.clause_id == cid)


def test_rule_detects_longer_payment_deadline() -> None:
    index = StandardIndex.build()
    text = _std("제40조").text.replace("인수일부터 60일을 초과하지 아니한다", "인수일부터 90일을 초과하지 아니한다")
    text = text.replace("원사업자", "갑").replace("수급사업자", "을")
    clause = Clause(doc_id="t", clause_id="제7조", title="하도급대금의 지급 등", text=text)
    hits = rule_check(clause, retrieve_standard(clause, index))
    assert [h.category for h in hits] == [Category.PAYMENT_DEADLINE]
    h = hits[0]
    assert h.observed_value == "90일" and h.threshold_value == "60일"
    assert h.risk_level == RiskLevel.HIGH  # 출처가 하도급법
    assert h.threshold_source.startswith("하도급법")


def test_rule_silent_on_unchanged_clause_and_lower_multiplier_flagged() -> None:
    index = StandardIndex.build()
    same = _std("제40조")
    assert rule_check(same, retrieve_standard(same, index)) == []
    text = _std("제54조").text.replace("손해의 3배를 넘지 아니하는", "손해의 1배를 넘지 아니하는")
    clause = Clause(doc_id="t", clause_id="제9조", title="손해배상", text=text)
    hits = rule_check(clause, retrieve_standard(clause, index))
    assert [h.category for h in hits] == [Category.DAMAGES_CAP]
    assert hits[0].risk_level == RiskLevel.HIGH
