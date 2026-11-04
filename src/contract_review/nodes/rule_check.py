"""rule_check 노드: 숫자로 판정할 수 있는 항목을 LLM 없이 결정적으로 검사한다.

방법
1. 계약서 조항에 대응하는 표준 조항(검색 top-1, 표준하도급계약서)에 걸린 기준값(thresholds.yaml)을 모은다.
2. 기준값의 원문 인용(quote)에서 숫자 자리를 `(\\d+)`로 바꾼 패턴을 만든다. 당사자 명칭과 공백은 정규화한다.
3. 계약서 조항에서 그 패턴을 찾아 숫자를 읽고, `worse_if` 방향으로 기준값과 비교한다.
   - 문장이 아예 없으면(삭제·재작성) 규칙은 판단하지 않는다 → LLM 몫.
   - 숫자가 같으면 finding 없음. 불리하면 법령 출처는 high, 표준계약서 출처는 medium.
"""

from __future__ import annotations

import re

from contract_review.schemas import Category, Clause, RetrievedRef, RiskLevel, RuleHit
from contract_review.standards import DOC_LABELS
from contract_review.textnorm import canon
from contract_review.thresholds import Threshold, rule_thresholds

_PARTY = re.compile(r"원사업자|수급사업자|발주자|도급인|수급인|갑|을")

UNIT_LABEL = {
    "days": "일",
    "percent": "%",
    "percent_per_year": "%/년",
    "multiplier": "배",
    "years": "년",
}


def _norm(text: str) -> str:
    """공백 제거·문장부호 통일 + 당사자 명칭을 'P'로 치환."""
    return _PARTY.sub("P", canon(text))


def _pattern_for(quote: str, value: float) -> re.Pattern[str] | None:
    """인용문에서 기준값 숫자를 캡처 그룹으로 바꾼 정규식."""
    norm = _norm(quote)
    target = str(int(value))
    hits = [m for m in re.finditer(r"\d+", norm) if m.group() == target]
    if not hits:
        return None
    m = hits[-1]
    head, tail = re.escape(norm[: m.start()]), re.escape(norm[m.end() :])
    return re.compile(head + r"(\d+)" + tail)


def _ref_targets(t: Threshold) -> list[tuple[str, str, str]]:
    """(source_doc, clause_id, quote) — 표준계약서 쪽 인용이 있으면 그것을 우선 비교에 쓴다."""
    targets = [(t.source_doc, t.clause_id, t.quote)]
    if t.standard_ref:
        targets.insert(0, (t.standard_ref.source_doc, t.standard_ref.clause_id, t.standard_ref.quote))
    return targets


def _observe(pat: re.Pattern[str], standard: str, contract: str, value: float) -> int | None:
    """계약서에서 기준값 자리의 숫자를 읽는다.

    같은 문형이 한 조항에 여러 번 나올 수 있어(예: 손해의 3배 / 5배) 표준 조항에서의 등장 순서와
    맞춰 읽는다. 등장 횟수가 다르면(문장 삭제·추가) 기준값과 같은 숫자가 하나라도 있으면 정상으로 본다.
    """
    std_vals = [int(m.group(1)) for m in pat.finditer(standard)]
    con_vals = [int(m.group(1)) for m in pat.finditer(contract)]
    if not con_vals:
        return None
    target = int(value)
    if len(con_vals) == len(std_vals) and target in std_vals:
        return con_vals[std_vals.index(target)]
    return None if target in con_vals else con_vals[0]


def rule_check(clause: Clause, refs: list[RetrievedRef]) -> list[RuleHit]:
    if not refs:
        return []
    top = refs[0]  # top-1 표준 조항만 신뢰
    contract, standard = _norm(clause.text), _norm(top.text)
    hits: list[RuleHit] = []
    for t in rule_thresholds():
        for doc, cid, quote in _ref_targets(t):
            if (doc, cid) != (top.source_doc, top.clause_id):
                continue
            pat = _pattern_for(quote, t.value or 0)
            if pat is None:
                continue
            observed = _observe(pat, standard, contract, t.value or 0)
            if observed is None:
                break
            worse = (observed > t.value) if t.worse_if == "greater" else (observed < t.value)
            if not worse:
                break
            unit = UNIT_LABEL.get(t.unit, t.unit)
            hits.append(
                RuleHit(
                    clause_id=clause.clause_id,
                    category=t.category,
                    risk_level=(RiskLevel.HIGH if t.source_doc == "subcontract_act" else RiskLevel.MEDIUM),
                    observed_value=f"{observed}{unit}",
                    threshold_value=f"{int(t.value or 0)}{unit}",
                    threshold_source=f"{DOC_LABELS[t.source_doc]} {t.clause_id}",
                    evidence_quote=quote,
                    standard_doc=doc,
                    standard_clause_id=cid,
                    description=t.description,
                )
            )
            break
    return hits


CATEGORY_LABEL: dict[Category, str] = {
    Category.PAYMENT_DEADLINE: "대금 지급 기한",
    Category.DELAY_PENALTY: "지체상금",
    Category.DEFECT_LIABILITY: "하자담보 책임",
    Category.DESIGN_CHANGE: "설계변경과 대금 조정",
    Category.TERMINATION: "계약 해제·해지",
    Category.UNFAIR_SPECIAL_TERMS: "부당 특약·책임 전가",
    Category.DAMAGES_CAP: "손해배상 한도",
    Category.OTHER: "기타",
}
