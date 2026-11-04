"""노드 입출력과 리포트의 pydantic 스키마 (docs/SPEC.md 2·4절)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

DISCLAIMER = (
    "본 리포트는 법률 자문이 아닌 검토 보조 도구의 출력입니다. "
    "최종 판단은 법률 전문가의 검토를 거치십시오."
)


class Category(StrEnum):
    PAYMENT_DEADLINE = "payment_deadline"  # 대금 지급 기한
    DELAY_PENALTY = "delay_penalty"  # 지체상금
    DEFECT_LIABILITY = "defect_liability"  # 하자담보 책임
    DESIGN_CHANGE = "design_change"  # 설계변경과 대금 조정
    TERMINATION = "termination"  # 계약 해제·해지
    UNFAIR_SPECIAL_TERMS = "unfair_special_terms"  # 부당 특약·책임 전가
    DAMAGES_CAP = "damages_cap"  # 손해배상 한도
    OTHER = "other"


class RiskLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    @property
    def rank(self) -> int:
        """정렬용: 높을수록 위험."""
        return {"high": 3, "medium": 2, "low": 1, "none": 0}[self.value]


class ParsedDocument(BaseModel):
    doc_id: str
    text: str
    pages: int = Field(ge=0)


class Clause(BaseModel):
    doc_id: str
    clause_id: str  # 예: "제12조"
    title: str = ""
    text: str
    section: str = "main"  # main | annexN | 부칙 | future (split_clauses 참고)


class RetrievedRef(BaseModel):
    source_doc: str  # data/raw 파일명
    clause_id: str
    title: str = ""
    text: str
    score: float


class RuleHit(BaseModel):
    """결정적 규칙 판정 결과. 기준값은 반드시 원문 출처를 가진다."""

    clause_id: str
    category: Category
    risk_level: RiskLevel
    observed_value: str
    threshold_value: str
    threshold_source: str  # 예: "하도급법.pdf 제n조"
    evidence_quote: str


class Finding(BaseModel):
    clause_id: str
    category: Category
    risk_level: RiskLevel
    contract_text: str
    standard_ref: str
    deviation_summary: str
    evidence_quote: str  # 기준 문서에 실제로 있는 문자열이어야 함 (코드 검증)
    source: str = Field(default="llm", pattern="^(rule|llm)$")


class ReportStats(BaseModel):
    clause_count: int = 0
    elapsed_sec: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class ReviewReport(BaseModel):
    contract_id: str
    generated_at: datetime
    config: str
    findings: list[Finding]
    stats: ReportStats = ReportStats()
    disclaimer: str = DISCLAIMER

    def sorted_findings(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: f.risk_level.rank, reverse=True)


class EvalCase(BaseModel):
    """eval/cases/*.yaml 한 줄 (정답 라벨)."""

    contract_id: str
    clause_id: str
    category: Category
    expected_risk: RiskLevel
    injected_change: str
