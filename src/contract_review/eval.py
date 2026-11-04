"""평가 하네스 (M5): 합성 계약서 3개를 파이프라인에 넣고 eval/cases 라벨과 비교한다.

지표 (docs/SPEC.md 7절)
- recall            = 잡아낸 라벨 수 / 라벨 수            (매칭 키: contract_id, clause_id, category)
- precision         = 라벨과 일치한 finding 수 / 전체 finding 수
- citation_accuracy = TP 중 standard_ref 가 정답 표준 조항을 가리킨 비율
- retrieval_hit3    = 라벨 조항 중 정답 표준 조항이 검색 top-3 에 든 비율 (baseline 은 검색 없음 → null)
- risk_match        = TP 중 위험도까지 맞춘 비율 (보조 지표)
- 계약서당 평균 처리 시간·토큰. 비용은 PRICE_IN_PER_1M / PRICE_OUT_PER_1M 환경변수가 있을 때만 계산

사용: .venv/bin/python -m contract_review.eval --config v2 [--llm fake|openai|anthropic]
      .venv/bin/python -m contract_review.eval --compare   # eval/results/*.json 을 표로
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

import yaml

from contract_review.config import load_settings
from contract_review.graph import CONFIGS, Pipeline
from contract_review.schemas import EvalCase, ReviewReport

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "eval" / "cases"
SYN = ROOT / "data" / "synthetic"
RESULTS = ROOT / "eval" / "results"


def load_cases() -> dict[str, list[EvalCase]]:
    out: dict[str, list[EvalCase]] = {}
    for yml in sorted(CASES.glob("synthetic_contract_*.yaml")):
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        out[yml.stem] = [EvalCase.model_validate(c) for c in data["cases"]]
    return out


def score(report: ReviewReport, cases: list[EvalCase], refs: dict | None) -> dict:
    labels = {(c.clause_id, c.category): c for c in cases}
    # (clause_id, category) 단위로 센다. 같은 키의 중복 finding 이 precision 을 부풀리지 않게
    uniq: dict[tuple, object] = {}
    for f in report.findings:
        if f.risk_level.value != "none":
            uniq.setdefault((f.clause_id, f.category), f)
    findings = list(uniq.values())
    tp_keys: set[tuple[str, str]] = set()
    tp_findings = []
    for f in findings:
        key = (f.clause_id, f.category)
        if key in labels:
            tp_keys.add(key)
            tp_findings.append((f, labels[key]))
    cite_ok = sum(1 for f, c in tp_findings if c.standard_clause_id in f.standard_ref)
    risk_ok = sum(1 for f, c in tp_findings if f.risk_level == c.expected_risk)
    hit3 = None
    if refs is not None:
        hits = 0
        for c in cases:
            got = [(r.source_doc, r.clause_id) for r in refs.get(c.clause_id, [])[:3]]
            hits += (c.standard_doc, c.standard_clause_id) in got
        hit3 = hits / len(cases) if cases else None
    return {
        "labels": len(cases),
        "findings": len(findings),
        "tp": len(tp_keys),
        "tp_findings": len(tp_findings),
        "cite_ok": cite_ok,
        "risk_ok": risk_ok,
        "hit3": hit3,
        "elapsed_sec": report.stats.elapsed_sec,
        "input_tokens": report.stats.input_tokens,
        "output_tokens": report.stats.output_tokens,
        "llm_calls": report.stats.llm_calls,
        "dropped": report.stats.dropped_findings,
        "llm_errors": report.stats.llm_errors,
        "unparsed": report.stats.unparsed_responses,
        "missed": [
            f"{c.clause_id}/{c.category.value} ({c.mutation_id})"
            for c in cases
            if (c.clause_id, c.category) not in tp_keys
        ],
        "false_positives": [
            f"{f.clause_id}/{f.category.value}" for f in findings if (f.clause_id, f.category) not in labels
        ],
    }


def aggregate(per: dict[str, dict], config: str, llm_name: str, retrieval_mode: str) -> dict:
    n = len(per)
    s = {
        k: sum(p[k] for p in per.values())
        for k in (
            "labels",
            "findings",
            "tp",
            "tp_findings",
            "cite_ok",
            "risk_ok",
            "input_tokens",
            "output_tokens",
            "llm_calls",
            "dropped",
            "llm_errors",
            "unparsed",
        )
    }
    hit3s = [p["hit3"] for p in per.values() if p["hit3"] is not None]
    price_in, price_out = os.getenv("PRICE_IN_PER_1M"), os.getenv("PRICE_OUT_PER_1M")
    cost = None
    if price_in and price_out:
        cost = (s["input_tokens"] * float(price_in) + s["output_tokens"] * float(price_out)) / 1e6 / n
    return {
        "date": date.today().isoformat(),
        "config": config,
        "llm": llm_name,
        "retrieval": retrieval_mode,
        "contracts": n,
        "labels": s["labels"],
        "findings": s["findings"],
        "recall": round(s["tp"] / s["labels"], 4) if s["labels"] else None,
        "precision": round(s["tp_findings"] / s["findings"], 4) if s["findings"] else None,
        "citation_accuracy": round(s["cite_ok"] / s["tp_findings"], 4) if s["tp_findings"] else None,
        "risk_match": round(s["risk_ok"] / s["tp_findings"], 4) if s["tp_findings"] else None,
        "retrieval_hit3": round(sum(hit3s) / len(hit3s), 4) if hit3s else None,
        "avg_sec_per_contract": round(sum(p["elapsed_sec"] for p in per.values()) / n, 2),
        "avg_input_tokens": s["input_tokens"] // n,
        "avg_output_tokens": s["output_tokens"] // n,
        "avg_llm_calls": s["llm_calls"] / n,
        "dropped_findings": s["dropped"],
        "llm_errors": s["llm_errors"],
        "unparsed_responses": s["unparsed"],
        "avg_cost_usd": round(cost, 4) if cost is not None else None,
        "per_contract": per,
    }


def _fmt(v: object) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def render_result(r: dict) -> str:
    lines = [
        f"# 평가 결과: {r['config']} ({r['date']})",
        "",
        f"- LLM: `{r['llm']}` · 검색: `{r['retrieval']}` · 계약서 {r['contracts']}개 · "
        f"라벨 {r['labels']}개 · finding {r['findings']}개",
        "",
        "| 지표 | 값 |",
        "|---|---|",
        f"| Recall | {_fmt(r['recall'])} |",
        f"| Precision | {_fmt(r['precision'])} |",
        f"| Citation accuracy | {_fmt(r['citation_accuracy'])} |",
        f"| Retrieval hit@3 | {_fmt(r['retrieval_hit3'])} |",
        f"| Risk match (보조) | {_fmt(r['risk_match'])} |",
        f"| 계약서당 처리 시간(초) | {_fmt(r['avg_sec_per_contract'])} |",
        f"| 계약서당 토큰 (입력/출력) | {r['avg_input_tokens']:,} / {r['avg_output_tokens']:,} |",
        f"| 계약서당 LLM 호출 | {_fmt(r['avg_llm_calls'])} |",
        f"| 근거 검증으로 제외된 finding | {r['dropped_findings']} |",
        f"| LLM 호출 실패 / JSON 파싱 실패 | {r.get('llm_errors', 0)} / {r.get('unparsed_responses', 0)} |",
        f"| max_tokens 로 잘린 응답 / 캐시 적중 | {r.get('truncated_calls', 0)} / {r.get('cache_hits', 0)} |",
        f"| 계약서당 비용(USD) | {_fmt(r['avg_cost_usd'])} |",
        "",
        "## 계약서별",
        "",
        "| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |",
        "|---|---|---|---|---|---|",
    ]
    for cid, p in r["per_contract"].items():
        lines.append(
            f"| {cid} | {p['labels']} | {p['findings']} | {p['tp']} | {', '.join(p['missed']) or '-'} | "
            f"{', '.join(p['false_positives']) or '-'} |"
        )
    return "\n".join(lines) + "\n"


def run_eval(config: str, llm_provider: str | None = None) -> dict:
    settings = load_settings()
    if llm_provider:
        settings = settings.model_copy(update={"llm_provider": llm_provider})
    pipe = Pipeline(CONFIGS[config], settings=settings)
    per: dict[str, dict] = {}
    for cid, cases in load_cases().items():
        out = pipe.run(SYN / f"{cid}.txt", contract_id=cid)
        per[cid] = score(out["report"], cases, out.get("refs") if pipe.config.split else None)
    r = aggregate(per, config, pipe.llm.name, pipe.index.mode)
    r["truncated_calls"] = getattr(pipe.llm, "truncated_calls", 0)
    r["cache_hits"] = getattr(pipe.llm, "hits", 0)
    if r["llm_errors"] or r["unparsed_responses"] or r["truncated_calls"]:
        print(
            f"⚠️ LLM 실패 {r['llm_errors']} · 파싱 실패 {r['unparsed_responses']} · 잘림 {r['truncated_calls']}"
            " — 이 결과의 recall 은 실패만큼 과소평가됨"
        )
    return r


def save_result(r: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    stem = f"{r['date']}_{r['config']}_{r['llm'].replace(':', '-').replace('/', '-')}"
    (RESULTS / f"{stem}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    md = RESULTS / f"{stem}.md"
    md.write_text(render_result(r), encoding="utf-8")
    return md


def render_compare(results: list[dict]) -> str:
    cols = [
        "recall",
        "precision",
        "citation_accuracy",
        "retrieval_hit3",
        "risk_match",
        "avg_sec_per_contract",
        "avg_input_tokens",
        "avg_llm_calls",
        "dropped_findings",
    ]
    head = "| config | LLM | " + " | ".join(cols) + " |"
    sep = "|---|---|" + "---|" * len(cols)
    rows = [f"| {r['config']} | {r['llm']} | " + " | ".join(_fmt(r.get(c)) for c in cols) + " |" for r in results]
    return "\n".join([f"# baseline / v1 / v2 비교 ({date.today().isoformat()})", "", head, sep, *rows]) + "\n"


def compare(llm_filter: str | None = None) -> Path:
    results = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESULTS.glob("*.json"))]
    if llm_filter:
        results = [r for r in results if r["llm"].startswith(llm_filter)]
    order = {"baseline": 0, "v1": 1, "v2": 2}
    results.sort(key=lambda r: (r["llm"], order.get(r["config"], 9), r["date"]))
    out = RESULTS / f"{date.today().isoformat()}_compare{'_' + llm_filter if llm_filter else ''}.md"
    out.write_text(render_compare(results), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="v2", choices=list(CONFIGS))
    ap.add_argument("--llm", default=None, choices=["fake", "openai", "anthropic"])
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--llm-filter", default=None)
    args = ap.parse_args()
    if args.compare:
        p = compare(args.llm_filter)
        print(p.read_text(encoding="utf-8"))
        return
    r = run_eval(args.config, args.llm)
    p = save_result(r)
    print(p.read_text(encoding="utf-8"))
    print(f"저장: {p}")


if __name__ == "__main__":
    main()
