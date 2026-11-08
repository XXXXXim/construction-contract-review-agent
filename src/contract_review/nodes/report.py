"""report 노드: ReviewReport → 한국어 마크다운 + JSON."""

from __future__ import annotations

import json
from pathlib import Path

from contract_review.nodes.rule_check import CATEGORY_LABEL
from contract_review.schemas import ReviewReport

RISK_LABEL = {"high": "🔴 높음", "medium": "🟠 중간", "low": "🟡 낮음", "none": "없음"}


def render_markdown(report: ReviewReport) -> str:
    fs = report.sorted_findings()
    counts = {lvl: sum(1 for f in fs if f.risk_level.value == lvl) for lvl in ("high", "medium", "low")}
    lines = [
        f"# 계약 검토 리포트: {report.contract_id}",
        "",
        f"> ⚠️ {report.disclaimer}",
        "",
        f"- 생성: {report.generated_at:%Y-%m-%d %H:%M} · 설정: `{report.config}` · "
        f"검색: {report.stats.retrieval_mode or '-'}",
        f"- 조항 {report.stats.clause_count}개 검토, 지적 {len(fs)}건 "
        f"(높음 {counts['high']} / 중간 {counts['medium']} / 낮음 {counts['low']})",
        f"- 처리 {report.stats.elapsed_sec:.1f}초 · LLM 호출 {report.stats.llm_calls}회 · "
        f"토큰 입력 {report.stats.input_tokens:,} / 출력 {report.stats.output_tokens:,} · "
        f"근거 검증 실패로 제외 {report.stats.dropped_findings}건 · "
        f"인용 확인 필요 {sum(1 for f in fs if f.citation_issues)}건",
        "",
        "## 요약",
        "",
        "| 위험도 | 조항 | 카테고리 | 판정 | 요지 |",
        "|---|---|---|---|---|",
    ]
    for f in fs:
        lines.append(
            f"| {RISK_LABEL[f.risk_level.value]} | {f.clause_id} | {CATEGORY_LABEL[f.category]} | "
            f"{'규칙' if f.source == 'rule' else 'LLM'} | {f.deviation_summary.replace('|', '/')} |"
        )
    lines += ["", "## 상세", ""]
    for i, f in enumerate(fs, 1):
        lines += [
            f"### {i}. {f.clause_id} · {CATEGORY_LABEL[f.category]} · {RISK_LABEL[f.risk_level.value]}",
            "",
            f"**편차:** {f.deviation_summary}",
            "",
            f"**근거 ({f.standard_ref}):**",
            "",
            f"> {f.evidence_quote}",
            "",
            *(
                ["**⚠️ 인용 확인 필요 (원문 대조):**", "", *[f"- `{i.ref}`: {i.detail}" for i in f.citation_issues], ""]
                if f.citation_issues
                else []
            ),
            "**계약서 원문 (발췌):**",
            "",
            "```",
            f.contract_text,
            "```",
            "",
        ]
    if not fs:
        lines.append("지적 사항이 없습니다.")
    return "\n".join(lines)


def write_report(report: ReviewReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"{report.contract_id}.report.md"
    js = out_dir / f"{report.contract_id}.report.json"
    md.write_text(render_markdown(report), encoding="utf-8")
    js.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return md, js
