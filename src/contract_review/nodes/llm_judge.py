"""llm_judge 노드: 조항 + 표준 조항 top-k + 규칙 결과 → Finding 리스트 (구조화 출력 + 근거 검증).

근거 검증 (verify=True):
- `evidence_quote` 는 LLM 이 `standard_ref` 로 지목한 **그 조항 본문에 실제로 있는 문자열**이어야 한다
  (공백 무시 비교). 없으면 그 finding 은 버리고 dropped 수를 센다.
- `standard_ref` 는 프롬프트에 준 표준 조항 중 하나여야 한다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from contract_review.llm import JudgeLLM
from contract_review.retrieval import StandardIndex
from contract_review.schemas import (
    Category,
    Clause,
    Finding,
    ParsedDocument,
    RetrievedRef,
    RiskLevel,
    RuleHit,
)
from contract_review.standards import DOC_LABELS, normalize_ws

# 표준하도급계약서 조항 → 검토 카테고리 (docs/SPEC.md 5절 표와 동일)
FTC_CLAUSE_CATEGORY: dict[str, Category] = {
    "제38조": Category.PAYMENT_DEADLINE,
    "제39조": Category.PAYMENT_DEADLINE,
    "제40조": Category.PAYMENT_DEADLINE,
    "제41조": Category.PAYMENT_DEADLINE,
    "제53조": Category.PAYMENT_DEADLINE,
    "제56조": Category.DELAY_PENALTY,
    "제57조": Category.DEFECT_LIABILITY,
    "제35조": Category.DESIGN_CHANGE,
    "제36조": Category.DESIGN_CHANGE,
    "제37조": Category.DESIGN_CHANGE,
    "제11조": Category.DESIGN_CHANGE,
    "제12조": Category.DESIGN_CHANGE,
    "제58조": Category.TERMINATION,
    "제47조": Category.UNFAIR_SPECIAL_TERMS,
    "제22조": Category.UNFAIR_SPECIAL_TERMS,
    "제33조": Category.UNFAIR_SPECIAL_TERMS,
    "제34조": Category.UNFAIR_SPECIAL_TERMS,
    "제54조": Category.DAMAGES_CAP,
    "제55조": Category.DAMAGES_CAP,
}

CATEGORY_GUIDE = """\
- payment_deadline: 대금·선급금·기성금 지급 기한, 지급 수단(현금비율·어음), 지연배상, 대금지급보증·계약이행보증
- delay_penalty: 지체상금 요율·산정 기준·면제 사유·공제 방식
- defect_liability: 하자담보책임 기간·범위·면책 사유·하자보수보증금
- design_change: 설계변경·물가변동에 따른 대금 조정 의무·기한·단가 기준
- termination: 계약 해제·해지 사유·절차·기성부분 처리·해지 손해배상
- unfair_special_terms: 비용·책임 전가, 법정 권리(대금 조정 신청 등) 포기, 일방적 결정권
- damages_cap: 손해배상 범위·배수·상한·무과실 책임
- other: 위에 해당하지 않음"""


def category_of_ref(ref: RetrievedRef) -> Category:
    if ref.source_doc == "ftc_standard_subcontract":
        return FTC_CLAUSE_CATEGORY.get(ref.clause_id, Category.OTHER)
    return Category.OTHER


def build_prompt(clause: Clause, refs: list[RetrievedRef], rule_hits: list[RuleHit]) -> str:
    std_blocks = "\n\n".join(
        f'<standard doc="{r.source_doc}" clause_id="{r.clause_id}" category="{category_of_ref(r).value}">\n'
        f"{r.text}\n</standard>"
        for r in refs
    )
    rule_block = (
        "\n".join(
            f"- [{h.category.value}] {h.description}: "
            f"계약서 {h.observed_value} vs 기준 {h.threshold_value} ({h.threshold_source})"
            for h in rule_hits
        )
        or "- 없음"
    )
    return f"""당신은 건설 하도급 계약 검토 보조 도구입니다. 아래 계약서 조항을 표준 조항과 비교해서
수급사업자(하도급 업체)에게 **불리하거나 표준에서 벗어난** 점만 찾으세요. 법률 자문이 아닙니다.

## 검토 카테고리
{CATEGORY_GUIDE}

## 위험도
- high: 하도급법 등 법령 기준 위반이 명백하거나 일방적 책임·권리 포기
- medium: 표준보다 불리하게 기한·비율·범위가 바뀌었으나 법령 위반은 불명확
- low: 표현·절차 차이로 해석 여지가 있는 경미한 편차

## 규칙 레이어가 이미 찾은 것 (중복 보고하지 마세요)
{rule_block}

## 계약서 조항
<contract clause_id="{clause.clause_id}">
{clause.text}
</contract>

## 대응 표준 조항 후보 (검색 상위, 첫 번째가 가장 유사)
{std_blocks}

## 출력 형식
JSON 배열만 출력하세요. 문제가 없으면 `[]`. 각 원소:
{{"clause_id": "{clause.clause_id}", "category": "<카테고리 enum>", "risk_level": "high|medium|low",
 "standard_ref": "<doc> <clause_id>  (위 standard 태그의 doc 과 clause_id 그대로)",
 "deviation_summary": "<무엇이 어떻게 다른지 한국어 1~3문장>",
 "evidence_quote": "<standard_ref 로 지목한 표준 조항 본문에서 그대로 복사한 문자열 (20~150자)>"}}
evidence_quote 는 반드시 해당 표준 조항 본문에 **글자 그대로** 있는 문장이어야 합니다. 지어내지 마세요.
"""


_JSON_RE = re.compile(r"\[.*\]", re.S)
_REF_RE = re.compile(r"(\w+)\s+(제\d+조(?:의\d+)?)")


@dataclass
class JudgeResult:
    findings: list[Finding]
    dropped: int
    input_tokens: int
    output_tokens: int


def _parse(raw: str) -> list[dict]:
    m = _JSON_RE.search(raw)
    if not m:
        return []
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)]


def llm_judge(
    clause: Clause,
    refs: list[RetrievedRef],
    rule_hits: list[RuleHit],
    llm: JudgeLLM,
    verify: bool = True,
) -> JudgeResult:
    if not refs:
        return JudgeResult([], 0, 0, 0)
    raw, tin, tout = llm.complete(build_prompt(clause, refs, rule_hits))
    by_ref = {(r.source_doc, r.clause_id): r for r in refs}
    findings: list[Finding] = []
    dropped = 0
    for d in _parse(raw):
        try:
            category = Category(d.get("category", "other"))
            risk = RiskLevel(d.get("risk_level", "medium"))
        except ValueError:
            dropped += 1
            continue
        if risk == RiskLevel.NONE:
            continue
        ref_m = _REF_RE.search(str(d.get("standard_ref", "")))
        quote = str(d.get("evidence_quote", "")).strip()
        ref = by_ref.get((ref_m.group(1), ref_m.group(2))) if ref_m else None
        if verify:
            if ref is None or len(normalize_ws(quote)) < 8 or normalize_ws(quote) not in normalize_ws(ref.text):
                dropped += 1
                continue
        label = (
            f"{DOC_LABELS.get(ref.source_doc, ref.source_doc)} {ref.clause_id}"
            if ref
            else str(d.get("standard_ref", ""))
        )
        findings.append(
            Finding(
                clause_id=clause.clause_id,
                category=category,
                risk_level=risk,
                contract_text=clause.text[:400],
                standard_ref=label,
                deviation_summary=str(d.get("deviation_summary", "")).strip(),
                evidence_quote=quote,
                source="llm",
            )
        )
    return JudgeResult(findings, dropped, tin, tout)


def rule_hit_to_finding(h: RuleHit, clause: Clause) -> Finding:
    return Finding(
        clause_id=h.clause_id,
        category=h.category,
        risk_level=h.risk_level,
        contract_text=clause.text[:400],
        standard_ref=f"{DOC_LABELS.get(h.standard_doc, h.standard_doc)} {h.standard_clause_id}",
        deviation_summary=(
            f"{h.description}: 계약서 {h.observed_value}, 기준 {h.threshold_value} ({h.threshold_source})"
        ),
        evidence_quote=h.evidence_quote,
        source="rule",
    )


# ── baseline: 계약서 전체를 한 번에 ──
def build_baseline_prompt(doc: ParsedDocument, index: StandardIndex | None = None) -> str:
    """단순 프롬프트. 검색·규칙·근거 검증 없이 '불리한 조항 찾아줘'."""
    return f"""당신은 건설 하도급 계약 검토 보조 도구입니다. 아래 하도급 계약서 전체를 읽고,
표준하도급계약서나 하도급법에 비해 수급사업자(하도급 업체)에게 불리한 조항을 찾아주세요.

## 검토 카테고리
{CATEGORY_GUIDE}

## 계약서
{doc.text}

## 출력 형식
JSON 배열만 출력하세요. 각 원소:
{{"clause_id": "제n조", "category": "<카테고리 enum>", "risk_level": "high|medium|low",
 "standard_ref": "<근거가 되는 표준계약서·법 조항>", "deviation_summary": "<한국어 1~3문장>",
 "evidence_quote": "<근거 문장>"}}
"""


def parse_baseline(raw: str, clauses: dict[str, Clause]) -> list[Finding]:
    out: list[Finding] = []
    for d in _parse(raw):
        cid = str(d.get("clause_id", "")).replace(" ", "")
        if cid not in clauses:
            continue
        try:
            category = Category(d.get("category", "other"))
            risk = RiskLevel(d.get("risk_level", "medium"))
        except ValueError:
            continue
        if risk == RiskLevel.NONE:
            continue
        out.append(
            Finding(
                clause_id=cid,
                category=category,
                risk_level=risk,
                contract_text=clauses[cid].text[:400],
                standard_ref=str(d.get("standard_ref", "")),
                deviation_summary=str(d.get("deviation_summary", "")),
                evidence_quote=str(d.get("evidence_quote", "")),
                source="llm",
            )
        )
    return out
