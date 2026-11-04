"""검색 평가 (M3): 합성 계약서 조항 → 정답 표준 조항이 top-k 안에 드는 비율.

두 집합으로 잰다:
- labeled: eval/cases 의 변형 라벨 24개 (본문이 표준과 다른 조항)
- all: 합성 계약서의 전체 조항 (clause_map, 정상 조항 포함)

사용: .venv/bin/python -m contract_review.eval_retrieval [--doc-filter ftc_standard_subcontract]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from contract_review.config import load_settings
from contract_review.nodes.parse import parse_document
from contract_review.nodes.retrieve_standard import retrieve_standard
from contract_review.nodes.split_clauses import split_clauses
from contract_review.retrieval import StandardIndex, make_embedder

ROOT = Path(__file__).resolve().parents[2]
STANDARD_DOC = "ftc_standard_subcontract"


def load_queries() -> list[dict]:
    out: list[dict] = []
    for yml in sorted((ROOT / "eval" / "cases").glob("synthetic_contract_*.yaml")):
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        labeled = {c["clause_id"] for c in data["cases"]}
        doc = parse_document(ROOT / "data" / "synthetic" / f"{yml.stem}.txt", doc_id=yml.stem)
        clauses = {c.clause_id: c for c in split_clauses(doc)}
        for cid, std_cid in data["clause_map"].items():
            out.append({"clause": clauses[cid], "gold": (STANDARD_DOC, std_cid), "labeled": cid in labeled})
    return out


def evaluate(
    index: StandardIndex,
    queries: list[dict],
    ks: tuple[int, ...] = (1, 3, 5),
    doc_filter: str | None = None,
    hard: bool = False,
) -> dict:
    """hard=True: 제목을 지우고 본문 앞 200자만 질의 (제목 복사 효과를 뺀 어려운 설정)."""
    kmax = max(ks)
    hits = {("all", k): 0 for k in ks} | {("labeled", k): 0 for k in ks}
    n_all = n_lab = 0
    t0 = time.perf_counter()
    for q in queries:
        clause = q["clause"]
        if hard:
            body = clause.text.split(")", 1)[-1][:200]
            clause = clause.model_copy(update={"title": "", "text": body})
        refs = retrieve_standard(clause, index, k=kmax, doc_filter=doc_filter)
        got = [(r.source_doc, r.clause_id) for r in refs]
        n_all += 1
        n_lab += q["labeled"]
        for k in ks:
            hit = q["gold"] in got[:k]
            hits[("all", k)] += hit
            hits[("labeled", k)] += hit and q["labeled"]
    elapsed = time.perf_counter() - t0
    return {
        "mode": index.mode,
        "hard": hard,
        "doc_filter": doc_filter,
        "n_all": n_all,
        "n_labeled": n_lab,
        **{f"hit@{k}_all": round(hits[("all", k)] / n_all, 4) for k in ks},
        **{f"hit@{k}_labeled": round(hits[("labeled", k)] / n_lab, 4) for k in ks},
        "sec_per_query": round(elapsed / n_all, 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-filter", default=None)
    ap.add_argument("--hard", action="store_true")
    args = ap.parse_args()
    settings = load_settings()
    index = StandardIndex.build(embedder=make_embedder(settings.embedding_provider))
    result = evaluate(index, load_queries(), doc_filter=args.doc_filter, hard=args.hard)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
