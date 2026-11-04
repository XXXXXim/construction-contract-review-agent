"""문자열 비교용 정규화. 인용 검증·규칙 패턴·fake 판정이 모두 이 함수로 비교한다.

PDF/HWP 원문과 LLM 출력은 같은 문장이라도 문장부호 코드가 다르다 (예: 원문 'ㆍ' U+318D vs LLM '·' U+00B7,
'「」' vs '""', 전각 괄호). 이런 차이로 진짜 인용을 버리지 않도록 비교 전에 한 가지 형태로 맞춘다.
"""

from __future__ import annotations

import re
import unicodedata

# 가운뎃점·중점 계열 → '·'
_DOTS = "ㆍᆞ·‧・•∙"  # ㆍ(U+318D) 는 NFKC 후 ᆞ(U+119E) 가 되므로 둘 다
# 따옴표·낫표 계열 → '"'
_QUOTES = "“”„‟「」『』〈〉《》\"'‘’‚‛`´"
# 대시 계열 → '-'
_DASHES = "‐‑‒–—―－~∼〜"
_TRANS = str.maketrans({**{c: "·" for c in _DOTS}, **{c: '"' for c in _QUOTES}, **{c: "-" for c in _DASHES}})
_WS = re.compile(r"\s+")
_ELLIPSIS = re.compile(r"\.{3,}|…+")

# 조항 머리: 제1조(목적) / 제 1 조 (목적) / 제1조【목적】 / 제1조의2[목적]
# (괄호 없는 '제1조 목적' 줄은 split_clauses 의 ARTICLE_BARE_RE 가 처리)
HEADER_RE = re.compile(r"^\s*제\s*\d+\s*조(?:\s*의\s*\d+)?\s*(?:[(（【\[][^)）】\]]*[)）】\]])?\s*")


def canon(text: str) -> str:
    """NFKC + 문장부호 통일 + 공백 전부 제거."""
    # NFKC 가 ㆍ 를 ᆞ 로 바꾸므로 정규화 전후 모두 문장부호를 맞춘다
    text = unicodedata.normalize("NFKC", text.translate(_TRANS)).translate(_TRANS)
    return _WS.sub("", text)


def strip_header(text: str) -> str:
    """'제n조(제목)' 머리를 뗀다. 계약서는 조 번호가 표준과 달라 비교에서 제외한다."""
    return HEADER_RE.sub("", text, count=1)


def quote_segments(quote: str) -> list[str]:
    """LLM 이 '…'로 줄여 인용한 경우 조각으로 나눈다. 각 조각이 원문에 있어야 한다."""
    return [canon(s) for s in _ELLIPSIS.split(quote) if canon(s)]


def contains_quote(haystack: str, quote: str, min_len: int = 8) -> bool:
    """quote(…로 줄인 인용 포함)가 haystack 에 실제로 있는가. 조각마다 min_len 이상이어야 한다."""
    segs = quote_segments(quote)
    if not segs or any(len(s) < min_len for s in segs):
        return False
    hay = canon(haystack)
    return all(s in hay for s in segs)
