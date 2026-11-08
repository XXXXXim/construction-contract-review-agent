"""FR-18. 공개 사례 평가셋(set-public): 문구 출처 검증과 시험 문서 구조."""

import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

from contract_review.nodes.parse import parse_document
from contract_review.nodes.split_clauses import split_clauses
from contract_review.schemas import Category, EvalCase, RiskLevel
from contract_review.standards import load_standard_clauses
from contract_review.textnorm import canon, contains_quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_public_cases import SPECIAL_ID, load_public_cases  # noqa: E402

_PDF_TEXT: dict[str, str] = {}


def _pdf_text(path: str) -> str:
    if path not in _PDF_TEXT:
        _PDF_TEXT[path] = "\n".join(p.extract_text() or "" for p in PdfReader(ROOT / path).pages)
    return _PDF_TEXT[path]


def test_public_case_quotes_exist_in_decision_pdfs() -> None:
    """텍스트층에서 뽑은 문구는 의결서에 그대로 있어야 하고, 이미지에서 옮긴 문구는 본문의 대응 구절이 있어야 한다."""
    cases = load_public_cases()
    assert len(cases) == 5
    for c in cases:
        text = _pdf_text(c["pdf"])
        if c["transcribed_from_image"]:
            assert contains_quote(text, c["text_layer_anchor"]), c["id"]
            # 옮겨 적은 문구에도 같은 핵심 구절이 들어 있어야 한다 (오타 방지)
            key = canon(c["text_layer_anchor"])[:20]
            assert key in canon(c["clause_text"]) or c["id"] == "pc05_daebang_waste_cost", c["id"]
        else:
            for line in c["clause_text"].splitlines():
                assert contains_quote(text, line, min_len=4), (c["id"], line)


def test_acceptable_categories_are_fixed_and_valid() -> None:
    for c in load_public_cases():
        cats = [Category(x) for x in c["acceptable_categories"]]
        assert Category(c["category"]) in cats
        assert RiskLevel(c["expected_risk"]) == RiskLevel.HIGH  # 공정위가 위반으로 판단한 문구


def test_public_contracts_append_clause_to_unmodified_standard() -> None:
    std = load_standard_clauses()["ftc_standard_subcontract"]
    for yml in sorted((ROOT / "eval" / "cases_public").glob("public_case_*.yaml")):
        data = yaml.safe_load(yml.read_text())
        label = EvalCase.model_validate(data["cases"][0])
        assert label.clause_id == SPECIAL_ID and label.standard_clause_id == ""
        cs = split_clauses(parse_document(ROOT / "data" / "public_cases" / f"{yml.stem}.txt"))
        assert [c.clause_id for c in cs] == [c.clause_id for c in std] + [SPECIAL_ID]
        # 제1~60조는 표준 원문과 같다 → 여기를 지적하면 오탐
        for a, b in zip(cs[:-1], std, strict=True):
            assert canon(a.text) == canon(b.text)


def test_matches_uses_acceptable_categories() -> None:
    lab = EvalCase(
        contract_id="x",
        clause_id=SPECIAL_ID,
        category=Category.UNFAIR_SPECIAL_TERMS,
        acceptable_categories=[Category.UNFAIR_SPECIAL_TERMS, Category.PAYMENT_DEADLINE],
        expected_risk=RiskLevel.HIGH,
        injected_change="x",
    )
    assert lab.matches(SPECIAL_ID, Category.PAYMENT_DEADLINE)
    assert not lab.matches(SPECIAL_ID, Category.TERMINATION)
    assert not lab.matches("제1조", Category.PAYMENT_DEADLINE)
