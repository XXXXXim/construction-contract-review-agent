"""parse 노드: PDF/TXT 파일 → ParsedDocument.

- PDF는 pypdf로 텍스트를 뽑는다. 국토부 고시 PDF처럼 일반 추출에서 띄어쓰기가
  사라지는 파일은 `layout` 모드로 다시 뽑는다 (자동 판별).
- 스캔 PDF(OCR)는 비범위. 텍스트가 거의 없으면 ValueError.
- 페이지 머리글/꼬리글(법제처 헤더, "- 2 -" 쪽번호)은 제거한다.
"""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from contract_review.schemas import ParsedDocument

# 국가법령정보센터 PDF 머리글: "법제처    1    국가법령정보센터"
_LAW_HEADER = re.compile(r"^\s*법제처\s+\d+\s+국가법령정보센터\s*$")
# 국토부 고시 PDF 쪽번호: "- 2 -"
_PAGE_NO = re.compile(r"^\s*-\s*\d+\s*-\s*$")
_HANGUL = re.compile(r"[가-힣]")


def _space_ratio(text: str) -> float:
    """한글 글자 수 대비 공백 수. 띄어쓰기가 사라진 추출 결과를 판별하는 데 쓴다."""
    hangul = len(_HANGUL.findall(text))
    if hangul == 0:
        return 1.0
    return text.count(" ") / hangul


def _clean_lines(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if _LAW_HEADER.match(line) or _PAGE_NO.match(line):
            continue
        # layout 모드가 만드는 연속 공백을 하나로
        out.append(re.sub(r"[ \t　]{2,}", " ", line).rstrip())
    return "\n".join(out)


def extract_pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    pages = [p.extract_text() or "" for p in reader.pages]
    text = "\n".join(pages)
    # 띄어쓰기가 거의 없으면 layout 모드로 재추출 (국토부 고시 PDF 대응)
    # 실측: 하도급법 PDF 0.42, 국토부 고시 PDF 0.16 (layout 모드 0.56)
    if _space_ratio(text) < 0.25:
        pages = [p.extract_text(extraction_mode="layout") or "" for p in reader.pages]
        text = "\n".join(pages)
    return text, len(reader.pages)


def parse_document(path: str | Path, doc_id: str | None = None) -> ParsedDocument:
    path = Path(path)
    doc_id = doc_id or path.stem
    if path.suffix.lower() == ".pdf":
        raw, pages = extract_pdf_text(path)
    elif path.suffix.lower() in {".txt", ".md"}:
        raw, pages = path.read_text(encoding="utf-8"), 1
    else:
        raise ValueError(f"지원하지 않는 형식: {path.suffix} (pdf/txt만 지원, HWP는 txt로 변환)")

    text = _clean_lines(raw)
    if len(_HANGUL.findall(text)) < 50:
        raise ValueError(f"{path.name}: 추출된 텍스트가 거의 없음 (스캔 PDF는 비범위)")
    return ParsedDocument(doc_id=doc_id, text=text, pages=pages)
