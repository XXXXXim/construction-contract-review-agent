"""FR-19. 조문 인용 검증. 아래 문장은 실제 평가에서 claude-sonnet-5-5 가 쓴 인용이다 (eval/results, 11/08)."""

import pytest

from contract_review.citation_check import check_text

# 원문 대조로 이미 오류로 확인한 인용 (README "baseline 의 법령 인용" 참고)
KNOWN_ERRORS = [
    ("하도급법 제13조 제6항(발주자로부터 대금 수령 후 15일 이내 지급)", "number_mismatch"),
    ("하도급법 제13조 제6항(발주자로부터 증액대금 수령 후 15일 이내 지급)", "number_mismatch"),
    ("하도급법 제12조의3(부당한 감액 금지)", "title_mismatch"),
    ("하도급법 제16조 제1항(증액받은 날부터 30일 이내 하도급대금 조정)", "number_mismatch"),
    ("하도급거래 공정화에 관한 법률 제13조(하도급대금의 지급), 같은 법 제15조(감액금지)", "title_mismatch"),
    # 합성 계약서의 자기 조항 번호를 표준 조항처럼 쓴 경우 (표준 제34조는 감액금지)
    ("표준하도급계약서 제34조(하도급대금의 지급 등) 현금비율 조항", "title_mismatch"),
    ("하도급법 제99조", "missing_article"),
    ("하도급법 제13조 제15항", "missing_paragraph"),
]

# 원문과 맞는 인용 (통과해야 한다)
KNOWN_CORRECT = [
    "하도급법 제13조 제4항(발주자로부터 받은 현금비율 이상 지급 원칙)",
    "하도급법 제3조의4(부당특약 금지)",
    "하도급법 제16조(설계변경 등에 따른 하도급대금 조정)",
    "하도급법 제13조의2(계약체결일부터 30일 이내 대금지급보증)",
    "하도급법 제13조 제1항(목적물 인수일부터 60일 이내 지급)",
    "하도급법 제6조(발주자로부터 받은 선급금은 15일 이내 지급)",
    "하도급법 제35조 제2항(부당감액·위탁취소·반품·부당대금결정·보복조치 등은 손해의 3배 이내 배상)",
    "표준하도급계약서(건설업종, 2024.12.24) 제40조 제1항·제2항·제9항(목적물 인수일부터 60일 이내 지급, "
    "발주자로부터 기성금을 받은 날부터 15일 이내 지급)",
    "표준하도급계약서 제57조",
    "표준하도급계약서 제47조 제2항 제1호·제7호·제8호 및 제3항 제1호(부당특약 무효)",
]


@pytest.mark.parametrize(("text", "kind"), KNOWN_ERRORS)
def test_known_citation_errors_are_caught(text: str, kind: str) -> None:
    r = check_text(text)
    assert kind in {i.kind for i in r.errors}, (text, r.issues)


@pytest.mark.parametrize("text", KNOWN_CORRECT)
def test_correct_citations_pass(text: str) -> None:
    r = check_text(text)
    assert r.errors == [], (text, r.errors)
    assert r.checked


def test_out_of_scope_laws_are_not_judged() -> None:
    r = check_text("민법 제390조, 약관규제법 제7조, 건설산업기본법 제34조 제6항, 하도급법 시행령 제6조의2")
    assert r.errors == [] and r.checked == []
    assert {i.kind for i in r.issues} == {"out_of_scope"}


def test_unsourced_number_warning() -> None:
    """set-public 실제 출력: 계약서는 10%, 인용 조문(표준 제57조)에도 3% 가 없다."""
    text = "표준하도급계약서 제57조 | 하도급법령은 하자보수보증금률 상한을 통상 3% 수준으로 두고 있어"
    contract = "최종 총계약금액의 10%에 해당하는 금원을 하자보수보증금으로 원사업자에게 예치하거나"
    r = check_text(text, contract)
    assert [i.ref for i in r.issues if i.kind == "unsourced_number"] == ["3%"]
    assert r.errors == []
    # 계약서에 있는 숫자는 경고하지 않는다
    assert not [i for i in check_text("총계약금액의 10%를 유보", contract).issues if i.kind == "unsourced_number"]


def test_contract_own_clause_mentions_are_not_treated_as_citations() -> None:
    """문서 이름 없이 '제30조 제7항은' 처럼 계약서 자기 조항을 말하는 건 검사 대상이 아니다."""
    r = check_text("제30조 제7항은 증액 대금 지급 기한을 15일에서 60일로 늘렸습니다.", "15일 60일")
    assert r.checked == [] and r.errors == []


def test_single_paragraph_article_cited_as_first_paragraph_is_ok() -> None:
    """표준하도급계약서 제45조처럼 ① 표시가 없는 조를 '제1항'으로 인용해도 '없는 항'이 아니다."""
    from contract_review.standards import find_clause

    assert "①" not in find_clause("ftc_standard_subcontract", "제45조").text
    assert not [i for i in check_text("표준하도급계약서 제45조 제1항").errors if i.kind == "missing_paragraph"]


def test_v2_report_marks_citation_issues_and_eval_counts_them() -> None:
    """FR-19 통합: v2 는 finding 에 인용 검사 결과를 붙이고, 평가 결과에는 인용 오류 수가 기록된다."""
    from contract_review import eval as ev
    from contract_review.citation_check import annotate
    from contract_review.schemas import Category, Finding, RiskLevel

    f = Finding(
        clause_id="제1조",
        category=Category.PAYMENT_DEADLINE,
        risk_level=RiskLevel.HIGH,
        contract_text="",
        standard_ref="하도급법 제15조(감액금지)",
        deviation_summary="",
        evidence_quote="",
    )
    assert [i.kind for i in annotate(f).citation_issues] == ["title_mismatch"]
    r = ev.run_eval("v2", "fake")
    assert "citation_errors" in r and "citation_checked" in r
    assert r["citation_errors"] == 0  # FakeLLM 은 검색된 표준 조항만 인용한다


def test_rule_findings_and_full_clause_text_avoid_false_unsourced_warnings() -> None:
    """11/08 통합 확인에서 발견: 400자 발췌 때문에 '90일'이 출처 없는 숫자로 잡혔고, 규칙 판정에도 경고가 붙었다."""
    from contract_review.citation_check import annotate
    from contract_review.schemas import Category, Finding, RiskLevel

    long_clause = "가" * 500 + " 증액받은 날부터 90일 이내에 한다"
    base = dict(
        clause_id="제1조",
        category=Category.DESIGN_CHANGE,
        risk_level=RiskLevel.HIGH,
        contract_text=long_clause[:400],
        standard_ref="표준하도급계약서 제35조",
        evidence_quote="",
    )
    rule = Finding(**base, deviation_summary="계약서 90일, 기준 30일 (하도급법 제16조)", source="rule")
    assert annotate(rule, long_clause).citation_issues == []
    llm = Finding(**base, deviation_summary="조정 기한을 90일로 늘렸다", source="llm")
    assert annotate(llm, long_clause).citation_issues == []  # 전문에는 90일이 있다
    assert [i.ref for i in annotate(llm).citation_issues] == ["90일"]  # 발췌만 보면 경고 (전문을 넘겨야 하는 이유)
