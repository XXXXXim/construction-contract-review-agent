"""LangGraph StateGraph 조립.

PDF → parse → split_clauses → retrieve_standard → rule_check → llm_judge → report

설정(PipelineConfig)에 따라 세 경로:
- baseline: parse → judge_whole (조항 전체를 LLM 한 번에) → report
- v1:       parse → split → retrieve(BM25) → judge (규칙 X, 근거 검증 X) → report
- v2:       parse → split → retrieve(하이브리드/BM25) → rule_check → judge (근거 검증 O) → report
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from contract_review.citation_check import annotate
from contract_review.config import Settings, load_settings
from contract_review.llm import JudgeLLM, get_llm
from contract_review.nodes.llm_judge import dedupe_findings, llm_judge, rule_hit_to_finding
from contract_review.nodes.parse import parse_document
from contract_review.nodes.report import render_markdown
from contract_review.nodes.retrieve_standard import retrieve_standard
from contract_review.nodes.rule_check import rule_check
from contract_review.nodes.split_clauses import split_clauses
from contract_review.retrieval import StandardIndex, make_embedder
from contract_review.schemas import (
    Clause,
    Finding,
    ParsedDocument,
    ReportStats,
    RetrievedRef,
    ReviewReport,
    RuleHit,
)


class PipelineConfig(BaseModel):
    name: str = "v2"
    split: bool = True  # False = baseline (조항 전체를 한 번에)
    use_rules: bool = True
    verify_evidence: bool = True
    use_embeddings: bool = True  # 키 없으면 자동 BM25
    check_citations: bool = False  # FR-19: 근거·설명문 속 조문 인용을 원문과 대조해 리포트에 표시 (판정은 바꾸지 않음)
    top_k: int = 3


CONFIGS: dict[str, PipelineConfig] = {
    "baseline": PipelineConfig(
        name="baseline", split=False, use_rules=False, verify_evidence=False, use_embeddings=False
    ),
    "v1": PipelineConfig(name="v1", use_rules=False, verify_evidence=False, use_embeddings=False),
    "v2": PipelineConfig(name="v2", check_citations=True),
}


class ReviewState(TypedDict, total=False):
    pdf_path: str
    contract_id: str
    doc: ParsedDocument
    clauses: list[Clause]
    refs: dict[str, list[RetrievedRef]]
    rule_hits: dict[str, list[RuleHit]]
    findings: list[Finding]
    stats: ReportStats
    report: ReviewReport
    report_md: str


class Pipeline:
    def __init__(
        self,
        config: PipelineConfig | str = "v2",
        settings: Settings | None = None,
        llm: JudgeLLM | None = None,
        index: StandardIndex | None = None,
    ) -> None:
        self.config = CONFIGS[config] if isinstance(config, str) else config
        self.settings = settings or load_settings()
        self.llm = llm or get_llm(self.settings)
        if index is None:
            emb = make_embedder(self.settings.embedding_provider) if self.config.use_embeddings else None
            index = StandardIndex.build(embedder=emb)
        self.index = index
        self.graph = self._build()

    # ── 노드 ──
    def n_parse(self, s: ReviewState) -> ReviewState:
        doc = parse_document(s["pdf_path"], doc_id=s.get("contract_id"))
        return {
            "doc": doc,
            "contract_id": doc.doc_id,
            "stats": ReportStats(retrieval_mode=self.index.mode),
        }

    def n_split(self, s: ReviewState) -> ReviewState:
        clauses = split_clauses(s["doc"])
        s["stats"].clause_count = len(clauses)
        return {"clauses": clauses}

    def n_retrieve(self, s: ReviewState) -> ReviewState:
        return {"refs": {c.clause_id: retrieve_standard(c, self.index, k=self.config.top_k) for c in s["clauses"]}}

    def n_rules(self, s: ReviewState) -> ReviewState:
        if not self.config.use_rules:
            return {"rule_hits": {}}
        return {"rule_hits": {c.clause_id: rule_check(c, s["refs"][c.clause_id]) for c in s["clauses"]}}

    def n_judge(self, s: ReviewState) -> ReviewState:
        findings: list[Finding] = []
        st = s["stats"]
        clauses = s["clauses"]

        def judge(c: Clause):  # 조항마다 독립 호출이라 병렬로 돌린다 (LLM_CONCURRENCY, 기본 4)
            hits = s["rule_hits"].get(c.clause_id, [])
            return hits, llm_judge(c, s["refs"][c.clause_id], hits, self.llm, verify=self.config.verify_evidence)

        workers = max(1, int(os.getenv("LLM_CONCURRENCY", "4"))) if self.settings.llm_provider != "fake" else 1
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(judge, clauses))  # 순서 유지 → 결과가 결정적
        for c, (hits, res) in zip(clauses, results, strict=True):
            findings += [rule_hit_to_finding(h, c) for h in hits]
            st.llm_calls += 1
            st.input_tokens += res.input_tokens
            st.output_tokens += res.output_tokens
            st.dropped_findings += res.dropped
            st.llm_errors += res.error
            st.unparsed_responses += res.unparsed
            findings += res.findings
        findings = dedupe_findings(findings)  # 같은 조항·카테고리는 규칙 판정 우선
        if self.config.check_citations:
            full = {c.clause_id: c.text for c in clauses}
            findings = [annotate(f, full.get(f.clause_id)) for f in findings]
        return {"findings": findings}

    def n_judge_whole(self, s: ReviewState) -> ReviewState:
        """baseline: 계약서 전체를 한 조항처럼 LLM 에 한 번에 넣는다. 검색·규칙·검증 없음."""
        from contract_review.nodes.llm_judge import build_baseline_prompt, parse_baseline

        doc = s["doc"]
        clauses = split_clauses(doc)  # 지표 계산용 clause_id 는 유지
        st = s["stats"]
        st.clause_count = len(clauses)
        st.llm_calls += 1
        try:
            raw, tin, tout = self.llm.complete(build_baseline_prompt(doc, self.index))
        except Exception:  # noqa: BLE001
            st.llm_errors += 1
            return {"clauses": clauses, "findings": []}
        st.input_tokens += tin
        st.output_tokens += tout
        found = parse_baseline(raw, {c.clause_id: c for c in clauses})
        st.unparsed_responses += found is None
        return {"clauses": clauses, "findings": found or []}

    def n_report(self, s: ReviewState) -> ReviewState:
        report = ReviewReport(
            contract_id=s["contract_id"],
            generated_at=datetime.now(),
            config=self.config.name,
            findings=s["findings"],
            stats=s["stats"],
        )
        return {"report": report, "report_md": render_markdown(report)}

    def _build(self):
        g = StateGraph(ReviewState)
        g.add_node("parse", self.n_parse)
        g.add_node("report", self.n_report)
        g.set_entry_point("parse")
        if self.config.split:
            g.add_node("split_clauses", self.n_split)
            g.add_node("retrieve_standard", self.n_retrieve)
            g.add_node("rule_check", self.n_rules)
            g.add_node("llm_judge", self.n_judge)
            g.add_edge("parse", "split_clauses")
            g.add_edge("split_clauses", "retrieve_standard")
            g.add_edge("retrieve_standard", "rule_check")
            g.add_edge("rule_check", "llm_judge")
            g.add_edge("llm_judge", "report")
        else:
            g.add_node("judge_whole", self.n_judge_whole)
            g.add_edge("parse", "judge_whole")
            g.add_edge("judge_whole", "report")
        g.add_edge("report", END)
        return g.compile()

    def run(self, path: str | Path, contract_id: str | None = None) -> ReviewState:
        t0 = time.perf_counter()
        init: ReviewState = {"pdf_path": str(path)}
        if contract_id:
            init["contract_id"] = contract_id
        out: ReviewState = self.graph.invoke(init)
        out["report"].stats.elapsed_sec = round(time.perf_counter() - t0, 2)
        out["report_md"] = render_markdown(out["report"])
        return out
