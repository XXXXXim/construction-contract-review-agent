"""저장된 실제 LLM 평가 결과(eval/results/*.json)의 finding 에 조문 인용 검증(FR-19)을 돌린다. API 호출 없음.

- 평가셋 × 구성별 최신 결과만 쓴다.
- 검사 대상 텍스트 = standard_ref + deviation_summary. 단, 결과 파일의 deviation_summary 는 앞 300자만 저장돼 있어
  그 뒤의 인용은 검사하지 못한다 (과소 집계).
- 주의: 검사기 기준은 이 결과들에서 사람이 찾은 오류로 정했다. 여기 숫자는 검사기 정확도의 독립 증거가 아니다.

사용: .venv/bin/python scripts/audit_citations.py [--llm-filter anthropic] [--out docs/citation_audit.md]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from contract_review.citation_check import ERROR_KINDS, check_text
from contract_review.eval import DATASETS
from contract_review.nodes.parse import parse_document
from contract_review.nodes.split_clauses import split_clauses

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"
ORDER = {"baseline": 0, "v1": 1, "v2": 2}
KIND_KO = {
    "missing_article": "없는 조",
    "missing_paragraph": "없는 항",
    "number_mismatch": "숫자 불일치",
    "title_mismatch": "내용·번호 불일치",
    "unsourced_number": "출처 없는 숫자",
    "out_of_scope": "범위 밖 법령",
}


def _contract_clauses(dataset: str, contract_id: str) -> dict[str, str]:
    syn_dir = DATASETS[dataset][1]
    doc = parse_document(syn_dir / f"{contract_id}.txt", doc_id=contract_id)
    return {c.clause_id: c.text for c in split_clauses(doc)}


def latest_results(llm_filter: str) -> list[dict]:
    latest: dict[tuple[str, str], dict] = {}
    for p in sorted(RESULTS.glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if not r.get("llm", "").startswith(llm_filter):
            continue
        if "findings_detail" not in next(iter(r["per_contract"].values()), {}):
            continue
        key = (r.get("dataset", "set-v1"), r["config"])
        if key not in latest or (r["date"], r.get("run_at", "")) >= (
            latest[key]["date"],
            latest[key].get("run_at", ""),
        ):
            latest[key] = r
    return sorted(latest.values(), key=lambda r: (r.get("dataset", "set-v1"), ORDER.get(r["config"], 9)))


def audit(r: dict) -> dict:
    dataset = r.get("dataset", "set-v1").removeprefix("set-")
    kinds: Counter[str] = Counter()
    checked = findings = 0
    errors: list[str] = []
    warnings: list[str] = []
    for cid, p in r["per_contract"].items():
        clauses = _contract_clauses(dataset, cid)
        for d in p["findings_detail"]:
            findings += 1
            if d.get("source") == "rule":
                continue  # 규칙 판정은 원문 인용 기준값으로 만들어져 검사 대상 아님 (파이프라인과 같은 기준)
            res = check_text(f"{d['standard_ref']} | {d['deviation_summary']}", clauses.get(d["clause_id"], ""))
            checked += len(res.checked)
            for i in res.issues:
                kinds[i.kind] += 1
                line = f"{cid} {d['clause_id']} [{d['category']}] {KIND_KO[i.kind]}: `{i.ref[:80]}` — {i.detail[:90]}"
                if i.kind in ERROR_KINDS:
                    errors.append(line)
                elif i.kind == "unsourced_number":
                    warnings.append(line)
    return {
        "dataset": r.get("dataset", "set-v1"),
        "config": r["config"],
        "findings": findings,
        "checked": checked,
        "errors": sum(kinds[k] for k in ERROR_KINDS),
        "kinds": kinds,
        "error_lines": errors,
        "warning_lines": warnings,
    }


def render(rows: list[dict], llm: str) -> str:
    out = [
        f"# 조문 인용 검증 결과 (FR-19, {llm})",
        "",
        "> `scripts/audit_citations.py` 자동 생성. 저장된 평가 결과의 finding(근거 + 설명문 앞 300자)을"
        " 원문과 대조했다.",
        "> 검사기 기준은 이 결과들에서 사람이 찾은 오류로 정했으므로, 아래 숫자는 검사기 정확도의 독립 증거가 아니다.",
        "",
        "| 평가셋 | config | finding | 대조한 인용 | **오류** | 없는 조·항 | 숫자 불일치 | 내용·번호 불일치 "
        "| 출처 없는 숫자(경고) | 범위 밖 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for a in rows:
        k = a["kinds"]
        out.append(
            f"| {a['dataset']} | {a['config']} | {a['findings']} | {a['checked']} | **{a['errors']}** | "
            f"{k['missing_article'] + k['missing_paragraph']} | {k['number_mismatch']} | {k['title_mismatch']} | "
            f"{k['unsourced_number']} | {k['out_of_scope']} |"
        )
    out += ["", "## 오류 목록", ""]
    for a in rows:
        if a["error_lines"]:
            out.append(f"### {a['dataset']} · {a['config']}")
            out += [f"- {line}" for line in a["error_lines"]]
            out.append("")
    out += ["## 출처 없는 숫자 (경고)", ""]
    for a in rows:
        if a["warning_lines"]:
            out.append(f"### {a['dataset']} · {a['config']}")
            out += [f"- {line}" for line in a["warning_lines"]]
            out.append("")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-filter", default="anthropic")
    ap.add_argument("--out", default="docs/citation_audit.md")
    args = ap.parse_args()
    rows = [audit(r) for r in latest_results(args.llm_filter)]
    text = render(rows, args.llm_filter)
    (ROOT / args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
