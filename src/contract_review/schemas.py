"""노드 입출력과 리포트의 pydantic 스키마 (docs/SPEC.md 2·4절)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = "본 리포트는 법률 자문이 아닌 검토 보조 도구의 출력입니다. 최종 판단은 법률 전문가의 검토를 거치십시오."


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
    threshold_source: str  # 예: "하도급법 제13조"
    evidence_quote: str
    standard_doc: str = ""  # 인용이 있는 기준 문서 doc_id
    standard_clause_id: str = ""
    description: str = ""


class CitationIssue(BaseModel):
    """조문 인용 검증 결과 하나 (contract_review.citation_check, FR-19)."""

    kind: Literal[
        "missing_article", "missing_paragraph", "number_mismatch", "title_mismatch", "unsourced_number", "out_of_scope"
    ]
    ref: str  # 예: "하도급법 제15조(감액금지)"
    detail: str = ""

    @property
    def is_error(self) -> bool:
        return self.kind in {"missing_article", "missing_paragraph", "number_mismatch", "title_mismatch"}


class Finding(BaseModel):
    clause_id: str
    category: Category
    risk_level: RiskLevel
    contract_text: str
    standard_ref: str
    deviation_summary: str
    evidence_quote: str  # 기준 문서에 실제로 있는 문자열이어야 함 (코드 검증)
    source: str = Field(default="llm", pattern="^(rule|llm)$")
    citation_issues: list[CitationIssue] = []  # v2: 근거·설명문 속 조문 인용을 원문과 대조한 결과


class ReportStats(BaseModel):
    clause_count: int = 0
    elapsed_sec: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    dropped_findings: int = 0  # evidence_quote 검증 실패로 버린 수
    llm_errors: int = 0  # 재시도 후에도 실패한 LLM 호출 수 (해당 조항은 판정 없음)
    unparsed_responses: int = 0  # JSON 을 하나도 못 읽은 응답 수
    retrieval_mode: str = ""


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
    clause_id: str  # 합성 계약서 안의 조항 ID (재번호 적용 후)
    category: Category
    expected_risk: RiskLevel
    injected_change: str
    mutation_id: str = ""
    standard_doc: str = "ftc_standard_subcontract"  # 정답 표준 문서
    standard_clause_id: str = ""  # 정답 표준 조항 (citation accuracy, hit@3 에 사용). 빈 값이면 두 지표에서 제외
    # set-public: 실질상 함께 맞다고 볼 카테고리 (실행 전 고정). 합성셋은 비어 있어 기존과 동일하게 채점된다
    acceptable_categories: list[Category] = []
    source: str = ""  # 실제 문구의 출처 (의결번호, 쪽)

    def matches(self, clause_id: str, category: Category) -> bool:
        return clause_id == self.clause_id and (category == self.category or category in self.acceptable_categories)
