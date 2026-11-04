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
from contract_review.standards import DOC_LABELS
from contract_review.textnorm import contains_quote

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


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
_FLAT_OBJ_RE = re.compile(r"\{[^{}]*\}", re.S)  # finding 은 중첩 없는 평평한 객체
_REF_RE = re.compile(r"(\w+)\s+(제\d+조(?:의\d+)?)")


@dataclass
class JudgeResult:
    findings: list[Finding]
    dropped: int
    input_tokens: int
    output_tokens: int
    error: bool = False
    unparsed: bool = False


def _from_json(data: object) -> list[dict] | None:
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        # {"findings": [...]} 처럼 감싼 경우, 또는 finding 하나만 객체로 준 경우
        for v in data.values():
            if isinstance(v, list) and all(isinstance(x, dict) for x in v):
                return v
        if "category" in data:
            return [data]
        return []
    return None


def _parse(raw: str) -> list[dict] | None:
    """LLM 응답에서 finding dict 목록을 꺼낸다. 하나도 못 읽으면 None.

    1) 코드펜스 제거 2) 전체를 JSON 으로 3) 첫 '['/'{' 부터 JSON 으로
    4) 잘린 응답(max_tokens) 복구: 평평한 객체 {...} 를 하나씩 읽는다.
    """
    text = raw.strip()
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    if text in ("", "[]"):
        return []
    candidates = [text]
    starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
    if starts:
        candidates.append(text[min(starts) :])
    for cand in candidates:
        try:
            got = _from_json(json.loads(cand))
        except json.JSONDecodeError:
            continue
        if got is not None:
            return got
    objs: list[dict] = []
    for m in _FLAT_OBJ_RE.finditer(text):
        try:
            d = json.loads(m.group())
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and "category" in d:
            objs.append(d)
    return objs or None


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    """(clause_id, category) 당 하나만 남긴다. 규칙 판정 > 높은 위험도 > 먼저 나온 것."""
    best: dict[tuple[str, Category], Finding] = {}
    for f in findings:
        key = (f.clause_id, f.category)
        cur = best.get(key)
        if cur is None or (f.source == "rule", f.risk_level.rank) > (cur.source == "rule", cur.risk_level.rank):
            best[key] = f
    return list(best.values())


def llm_judge(
    clause: Clause,
    refs: list[RetrievedRef],
    rule_hits: list[RuleHit],
    llm: JudgeLLM,
    verify: bool = True,
) -> JudgeResult:
    if not refs:
        return JudgeResult([], 0, 0, 0)
    try:
        raw, tin, tout = llm.complete(build_prompt(clause, refs, rule_hits))
    except Exception:  # noqa: BLE001 — 재시도 후에도 실패한 호출 하나가 전체 평가를 멈추지 않게
        return JudgeResult([], 0, 0, 0, error=True)
    by_ref = {(r.source_doc, r.clause_id): r for r in refs}
    findings: list[Finding] = []
    dropped = 0
    parsed = _parse(raw)
    for d in parsed or []:
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
        if verify and (ref is None or not contains_quote(ref.text, quote)):
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
    return JudgeResult(findings, dropped, tin, tout, unparsed=parsed is None)


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


def parse_baseline(raw: str, clauses: dict[str, Clause]) -> list[Finding] | None:
    """None = JSON 을 하나도 못 읽음."""
    parsed = _parse(raw)
    if parsed is None:
        return None
    out: list[Finding] = []
    for d in parsed:
        cid = re.sub(r"\s+", "", str(d.get("clause_id", "")))
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
    return dedupe_findings(out)
