"""split_clauses 노드: ParsedDocument → list[Clause].

"제n조(제목)" 또는 "제n조의m(제목)" 패턴이 **줄 머리**에 올 때 새 조항이 시작된다.

실제 원문에서 확인한 특이 케이스와 처리:
- 한 파일 안에 문서가 여러 개 (표준하도급계약서 HWP: 본문 + 비밀유지계약서 + 변경계약서 +
  연동계약서…, 국토부 고시 PDF: 고시 본문 3개조 + 별표 계약서). 조 번호가 다시 1로 돌아가면
  새 `section`으로 본다 (main → annex1 → annex2 …).
- 법령 PDF의 "부칙": `부칙` 줄부터 section="부칙".
- 법령 PDF의 장래 시행 조문: 같은 번호가 두 번 나오고 뒤 것이 "[시행일: 2027. 9. 9.] 제22조"로
  끝난다 → section="future", 마커 줄은 본문에서 제거.
- "제n장 …" 장 제목 줄과 "<표>", "<그림>" 자리표시 줄은 버린다.
"""

from __future__ import annotations

import re
from collections import Counter

from contract_review.schemas import Clause, ParsedDocument

ARTICLE_RE = re.compile(r"^\s*제(\d+)조(?:의(\d+))?\s*\(([^)]{1,60})\)\s*(.*)$")
CHAPTER_RE = re.compile(r"^\s*제\d+장\s")
ADDENDUM_RE = re.compile(r"^\s*부\s*칙(\s|<|$)")
FUTURE_RE = re.compile(r"^\s*\[시행일:\s*[\d.\s]+\]\s*제\d+조(?:의\d+)?\s*$")
PLACEHOLDER_RE = re.compile(r"^\s*<(표|그림)>\s*$")


def _article_num(m: re.Match[str]) -> tuple[int, int]:
    return int(m.group(1)), int(m.group(2) or 0)


def split_clauses(doc: ParsedDocument) -> list[Clause]:
    clauses: list[Clause] = []
    section = "main"
    annex_count = 0
    seen_in_section = 0  # 현재 section에서 만난 조항 수
    loose_text = False  # 조항 밖의 본문(예: 부칙 "이 고시는 발령한 날부터 시행한다")
    cur: dict[str, str] | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal cur, buf
        if cur is None:
            return
        lines = [ln for ln in buf if ln.strip()]
        sec = cur["section"]
        if lines and FUTURE_RE.match(lines[-1]):
            lines = lines[:-1]
            sec = "future"
        body = "\n".join(lines).strip()
        clauses.append(
            Clause(
                doc_id=doc.doc_id,
                clause_id=cur["clause_id"],
                title=cur["title"],
                text=body,
                section=sec,
            )
        )
        cur, buf = None, []

    for line in doc.text.splitlines():
        if PLACEHOLDER_RE.match(line):
            continue
        if ADDENDUM_RE.match(line):
            flush()
            section, seen_in_section, loose_text = "부칙", 0, False
            continue
        if CHAPTER_RE.match(line):
            flush()
            continue
        m = ARTICLE_RE.match(line)
        if m:
            flush()
            num = _article_num(m)
            # 조 번호가 1로 되돌아가면 새 문서(별첨)로 본다
            # (국토부 고시는 조항 없는 "부칙" 문장 뒤에 별표 계약서 제1조가 다시 시작한다)
            restart = seen_in_section > 0 or (section == "부칙" and loose_text)
            if num == (1, 0) and restart:
                annex_count += 1
                section, seen_in_section = f"annex{annex_count}", 0
            seen_in_section += 1
            loose_text = False
            suffix = f"의{num[1]}" if num[1] else ""
            cur = {
                "clause_id": f"제{num[0]}조{suffix}",
                "title": m.group(3).strip(),
                "section": section,
            }
            buf = [line.strip()]
            continue
        if cur is not None:
            buf.append(line)
        elif line.strip():
            loose_text = True
    flush()
    return clauses


def body_clauses(clauses: list[Clause]) -> list[Clause]:
    """조항 수가 가장 많은 section = 그 파일의 본문. 표준 조항 인덱스는 본문만 쓴다."""
    if not clauses:
        return []
    counts = Counter(c.section for c in clauses if c.section != "future")
    main = counts.most_common(1)[0][0]
    return [c for c in clauses if c.section == main]
