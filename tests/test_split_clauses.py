from pathlib import Path

import pytest

from contract_review.nodes.parse import parse_document
from contract_review.nodes.split_clauses import body_clauses, split_clauses
from contract_review.schemas import ParsedDocument

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

SAMPLE = """
머리말
제1장 총칙
제1조(목적) 이 계약은 목적을 정한다.
둘째 줄.
<표>
제2조(정의) 용어를 정한다.
제2조의2(추가) 끼어든 조.
제3조(기한) 기한을 정한다.
[시행일: 2027. 9. 9.] 제3조
제4조(해지) 해지를 정한다.
제4조 제2항을 준용한다.
부칙 <제1호>
제1조(시행일) 공포한 날부터 시행한다.
별첨
제1조(목적) 별첨 계약서의 목적.
제2조(정의) 별첨 정의.
"""


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument(doc_id="t", text=text, pages=1)


def test_split_basic_ids_titles_and_text() -> None:
    cs = split_clauses(_doc(SAMPLE))
    main = [c for c in cs if c.section == "main"]
    assert [c.clause_id for c in main] == ["제1조", "제2조", "제2조의2", "제4조"]
    assert main[0].title == "목적"
    assert main[0].text == "제1조(목적) 이 계약은 목적을 정한다.\n둘째 줄."
    # 줄 머리에 "제4조 제2항…"처럼 제목 괄호가 없는 참조는 새 조항이 아니다
    assert "준용한다" in main[3].text


def test_future_marker_moves_clause_to_future_section() -> None:
    cs = split_clauses(_doc(SAMPLE))
    fut = [c for c in cs if c.section == "future"]
    assert [c.clause_id for c in fut] == ["제3조"]
    assert "[시행일" not in fut[0].text


def test_addendum_and_annex_sections() -> None:
    cs = split_clauses(_doc(SAMPLE))
    assert [c.clause_id for c in cs if c.section == "부칙"] == ["제1조"]
    assert [c.clause_id for c in cs if c.section == "annex1"] == ["제1조", "제2조"]
    assert [c.clause_id for c in body_clauses(cs)] == ["제1조", "제2조", "제2조의2", "제4조"]


def test_parse_rejects_unknown_suffix(tmp_path: Path) -> None:
    p = tmp_path / "a.hwp"
    p.write_bytes(b"x")
    with pytest.raises(ValueError):
        parse_document(p)


@pytest.mark.parametrize(
    ("filename", "expected_body", "spot"),
    [
        ("ftc_standard_subcontract_construction_20241224.txt", 60, ("제56조", "지체상금")),
        ("subcontract_act_20261002.pdf", None, ("제13조", "하도급대금의 지급 등")),
        ("molit_standard_contract_private_2026-34.pdf", 43, ("제30조", "지체상금")),
    ],
)
def test_real_sources_split(filename: str, expected_body: int | None, spot: tuple[str, str]) -> None:
    doc = parse_document(RAW / filename)
    cs = split_clauses(doc)
    body = body_clauses(cs)
    if expected_body is not None:
        assert len(body) == expected_body
    else:
        assert len(body) >= 60
    by_id = {c.clause_id: c for c in body}
    assert by_id[spot[0]].title == spot[1]
    # 본문 안에서 clause_id 는 유일해야 한다
    assert len(by_id) == len(body)


def test_law_future_versions_are_separated() -> None:
    cs = split_clauses(parse_document(RAW / "subcontract_act_20261002.pdf"))
    future_ids = {c.clause_id for c in cs if c.section == "future"}
    assert {"제22조", "제29조", "제35조"} <= future_ids
    assert len([c for c in cs if c.section == "부칙"]) >= 1


def test_molit_contract_body_is_annex_after_addendum() -> None:
    cs = split_clauses(parse_document(RAW / "molit_standard_contract_private_2026-34.pdf"))
    assert len([c for c in cs if c.section == "main"]) == 3  # 고시 본문
    assert len([c for c in cs if c.section == "부칙"]) == 0  # 부칙에는 조항이 없다
    assert body_clauses(cs)[0].section == "annex1"  # 별표 계약서


def test_molit_layout_extraction_keeps_spaces() -> None:
    doc = parse_document(RAW / "molit_standard_contract_private_2026-34.pdf")
    assert "지체상금" in doc.text
    # 일반 추출이면 "공사기간산정기준을포함" 처럼 붙어 나온다
    assert "공사기간 산정기준을" in doc.text
