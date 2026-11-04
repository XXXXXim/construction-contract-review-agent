"""data/raw/ 원문 3종을 파싱해 section별 조항 수와 본문 조항 제목 표를 출력한다 (M1 DoD).

사용: .venv/bin/python scripts/inspect_raw.py [--out docs/raw_clauses.md]
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from contract_review.nodes.parse import parse_document
from contract_review.nodes.split_clauses import body_clauses, split_clauses
from contract_review.standards import SOURCES


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/raw_clauses.md")
    args = ap.parse_args()

    lines = ["# data/raw 조항 분할 결과 (scripts/inspect_raw.py 자동 생성)", ""]
    for doc_id, path in SOURCES.items():
        doc = parse_document(path, doc_id=doc_id)
        clauses = split_clauses(doc)
        body = body_clauses(clauses)
        counts = Counter(c.section for c in clauses)
        lines += [
            f"## {doc_id} (`{path.name}`, {doc.pages}p)",
            "",
            "| section | 조항 수 |",
            "|---|---|",
            *[f"| {s} | {n} |" for s, n in counts.items()],
            "",
            f"본문({body[0].section if body else '-'}) {len(body)}개 조항:",
            "",
            "| clause_id | title | 글자 수 |",
            "|---|---|---|",
            *[f"| {c.clause_id} | {c.title} | {len(c.text)} |" for c in body],
            "",
        ]
    out = "\n".join(lines)
    print(out)
    Path(args.out).write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
