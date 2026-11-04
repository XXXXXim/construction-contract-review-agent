"""기준 문서(data/raw) 3종을 파싱해 본문 조항을 돌려주는 공용 로더.

검색 인덱스와 근거 검증이 쓴다.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from contract_review.nodes.parse import parse_document
from contract_review.nodes.split_clauses import body_clauses, split_clauses
from contract_review.schemas import Clause

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"

SOURCES: dict[str, Path] = {
    "subcontract_act": RAW / "subcontract_act_20261002.pdf",
    "ftc_standard_subcontract": RAW / "ftc_standard_subcontract_construction_20241224.txt",
    "molit_standard_contract": RAW / "molit_standard_contract_private_2026-34.pdf",
}

# 리포트에 쓰는 한국어 문서명
DOC_LABELS: dict[str, str] = {
    "subcontract_act": "하도급법",
    "ftc_standard_subcontract": "표준하도급계약서",
    "molit_standard_contract": "표준도급계약서",
}

_WS = re.compile(r"\s+")


def normalize_ws(text: str) -> str:
    """공백·줄바꿈을 전부 제거. 인용문 검증은 이 형태로 비교한다 (PDF 줄바꿈 차이 흡수)."""
    return _WS.sub("", text)


@lru_cache(maxsize=1)
def load_standard_clauses() -> dict[str, list[Clause]]:
    """doc_id → 본문 조항 리스트."""
    return {
        doc_id: body_clauses(split_clauses(parse_document(path, doc_id=doc_id))) for doc_id, path in SOURCES.items()
    }


def find_clause(doc_id: str, clause_id: str) -> Clause | None:
    for c in load_standard_clauses().get(doc_id, []):
        if c.clause_id == clause_id:
            return c
    return None


def quote_in_clause(quote: str, doc_id: str, clause_id: str) -> bool:
    """quote 가 해당 기준 조항 본문에 실제로 있는지 (공백 무시)."""
    c = find_clause(doc_id, clause_id)
    return c is not None and normalize_ws(quote) in normalize_ws(c.text)


def quote_in_any_standard(quote: str) -> tuple[str, str] | None:
    """quote 가 기준 문서 어딘가에 있으면 (doc_id, clause_id)를 돌려준다."""
    q = normalize_ws(quote)
    if len(q) < 8:
        return None
    for doc_id, clauses in load_standard_clauses().items():
        for c in clauses:
            if q in normalize_ws(c.text):
                return doc_id, c.clause_id
    return None
