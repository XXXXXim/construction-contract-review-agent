"""조문 인용 검증 (FR-19).

LLM 이 지적의 근거(standard_ref)와 설명문(deviation_summary)에 적은 조문 인용을 data/raw 원문과 대조한다.

검사 (심각도):
- missing_article   (error)   인용한 조가 원문에 없다              예: 하도급법 제99조
- missing_paragraph (error)   인용한 항이 그 조에 없다             예: 제13조 제15항
- number_mismatch   (error)   괄호 속 숫자가 인용한 조·항에 없다    예: 제13조 제6항(…15일 이내 지급)
- title_mismatch    (error)   괄호 속 설명이 인용한 조·항 내용과 안 맞는다  예: 제15조(감액금지)
- unsourced_number  (warning) 설명문 속 숫자가 계약서 조항·인용한 조문·규칙 기준값 어디에도 없다
- out_of_scope      (info)    원문이 없는 법령(민법, 건설산업기본법, 시행령 등) → 검사하지 않음

못 하는 것: 번호만 대고 설명이 없는 인용이 지적과 관련 있는지(관련성)는 판단하지 않는다.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

from pydantic import BaseModel

from contract_review.schemas import CitationIssue, Clause, Finding
from contract_review.standards import load_standard_clauses
from contract_review.textnorm import canon
from contract_review.thresholds import load_thresholds

ERROR_KINDS = {"missing_article", "missing_paragraph", "number_mismatch", "title_mismatch"}


class CitationCheck(BaseModel):
    checked: list[str] = []  # 원문과 대조한 인용
    issues: list[CitationIssue] = []

    @property
    def errors(self) -> list[CitationIssue]:
        return [i for i in self.issues if i.is_error]


# ── 문서 이름 → doc_id ──
# "하도급법 시행령"처럼 원문이 없는 하위 법령은 범위 밖으로 먼저 걸러낸다.
_OUT_OF_SCOPE = re.compile(
    r"(하도급(?:거래 공정화에 관한 )?법(?:률)?\s*시행(?:령|규칙)|민법|건설산업기본법|건산법|약관(?:규제)?법|"
    r"약관의 규제에 관한 법률|국가(?:를 당사자로 하는 )?계약(?:에 관한)? ?법(?:률)?|시행령|시행규칙|심사지침|고시)"
)
_DOC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("subcontract_act", re.compile(r"「?하도급거래 공정화에 관한 법률」?|하도급법|같은 법(?!\s*시행)")),
    ("molit_standard_contract", re.compile(r"(?:민간건설공사\s*)?표준도급계약서")),
    ("ftc_standard_subcontract", re.compile(r"(?:건설업종\s*)?표준하도급계약서|표준계약서")),
]
DOC_LABEL = {
    "subcontract_act": "하도급법",
    "molit_standard_contract": "표준도급계약서",
    "ftc_standard_subcontract": "표준하도급계약서",
}

# 조 인용 하나: 제13조의2 제1항·제3항 제2호 (설명)
_ART = re.compile(
    r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?"
    r"((?:\s*제?\s*\d+\s*항(?:\s*[·ㆍ,]\s*제?\s*\d+\s*항)*)?)"
    r"(?:\s*제?\s*\d+\s*호(?:\s*[·ㆍ,]\s*제?\s*\d+\s*호)*)?"
    r"(?:\s*\(([^()]{1,120})\))?"
)
_CHAIN_SEP = re.compile(r"\s*(?:[·ㆍ,]|및|와|과|또는)\s*")
_PARA_NUM = re.compile(r"(\d+)\s*항")
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

# 숫자 표현: 15일, 60일, 10%, 100분의 40, 3배, 2개월, 4년, 연 15.5%
_NUM = re.compile(r"(?:100분의\s*(\d+(?:\.\d+)?))|(\d+(?:\.\d+)?)\s*(%|퍼센트|일|개월|년|배)")
_STOP = {
    "등",
    "및",
    "의",
    "이내",
    "관한",
    "따른",
    "경우",
    "조항",
    "규정",
    "원칙",
    "관련",
    "내용",
    "의무",
    "사항",
    "기준",
    "대한",
    "위한",
    "또는",
    "같은",
    "해당",
    "모든",
    "그",
    "이",
    "수",
    "것",
    "때",
    "통상",
    "수준",
}


def _norm_numbers(text: str) -> set[str]:
    """숫자 표현을 비교용 키로: '100분의 40' 과 '40%' 를 같은 것으로 본다."""
    out: set[str] = set()
    for m in _NUM.finditer(text):
        if m.group(1):
            out.add(f"{m.group(1)}%")
        else:
            unit = "%" if m.group(3) in ("%", "퍼센트") else m.group(3)
            out.add(f"{m.group(2)}{unit}")
    return out


def _paragraphs(text: str) -> dict[int, str]:
    """조 본문을 항(①②…)별로 나눈다. 항 표시가 없으면 빈 dict."""
    idx = [(i, _CIRCLED.index(ch) + 1) for i, ch in enumerate(text) if ch in _CIRCLED]
    out: dict[int, str] = {}
    for k, (pos, n) in enumerate(idx):
        end = idx[k + 1][0] if k + 1 < len(idx) else len(text)
        out.setdefault(n, text[pos:end])
    return out


@lru_cache(maxsize=1)
def _index() -> dict[str, dict[str, Clause]]:
    return {d: {c.clause_id: c for c in cs} for d, cs in load_standard_clauses().items()}


@lru_cache(maxsize=1)
def _threshold_numbers() -> set[str]:
    nums: set[str] = set()
    for t in load_thresholds():
        nums |= _norm_numbers(t.quote)
    return nums


def _kw_ratio(desc: str, target: str) -> float:
    """괄호 속 설명의 핵심어 중 대상 텍스트에 있는 비율.
    핵심어는 2-gram 의 60% 이상이 대상에 있으면 '있다'고 본다 (조사·어미 차이 흡수)."""
    tgt = canon(target)
    words = [w for w in re.findall(r"[가-힣A-Za-z]{2,}", desc) if w not in _STOP]
    if not words:
        return 1.0
    hit = 0
    for w in words:
        grams = [w[i : i + 2] for i in range(len(w) - 1)]
        if sum(g in tgt for g in grams) / len(grams) >= 0.6:
            hit += 1
    return hit / len(words)


# 판정 기준 (tests/test_citation_check.py 의 실제 오류·정상 인용으로 정함)
TITLE_OK = 0.5  # 설명이 인용한 조 제목과 (가중) 이 정도 맞으면 정상
OTHER_TITLE_MATCH = 0.6  # 다른 조 제목과 (가중) 이 정도 이상 맞으면 '번호를 잘못 붙임'
CONTENT_MIN = 0.25  # 제목과 안 맞는 서술형 설명은 본문과 이 정도는 맞아야 함 (아주 동떨어진 경우만 잡는다)


def _words(desc: str) -> list[str]:
    return [w for w in re.findall(r"[가-힣A-Za-z]{2,}", desc) if w not in _STOP]


def _has(word: str, target_canon: str) -> bool:
    grams = [word[i : i + 2] for i in range(len(word) - 1)]
    return sum(g in target_canon for g in grams) / len(grams) >= 0.6


def _weighted_title_ratio(doc: str, desc: str, title: str) -> float:
    """제목 비교용 가중 비율. '부당한', '금지'처럼 그 법의 조 제목 여러 개에 나오는 단어는 가볍게,
    '감액'처럼 드문 단어는 무겁게 본다 (IDF, 문서별 조 제목 기준)."""
    words = _words(desc)
    if not words:
        return 1.0
    titles = [canon(c.title) for c in _index()[doc].values()]
    n = len(titles)
    tgt = canon(title)
    total = hit = 0.0
    for w in words:
        df = sum(_has(w, t) for t in titles)
        weight = math.log((n + 1) / (df + 1)) + 0.1
        total += weight
        hit += weight if _has(w, tgt) else 0.0
    return hit / total


def _title_problem(doc: str, art: str, desc: str, title: str, unit: str) -> str | None:
    """설명(desc)이 인용한 조와 안 맞으면 이유를, 맞으면 None."""
    own = _weighted_title_ratio(doc, desc, title)
    if own >= TITLE_OK:
        return None
    best_id, best = max(
        ((cid, _weighted_title_ratio(doc, desc, c.title)) for cid, c in _index()[doc].items() if cid != art),
        key=lambda x: x[1],
        default=("", 0.0),
    )
    if best >= OTHER_TITLE_MATCH and best > own:
        return f"설명이 {best_id}({_index()[doc][best_id].title}) 제목과 일치. 원문 {art} 제목: {title}"
    if _kw_ratio(desc, f"{title} {unit}") < CONTENT_MIN:
        return f"설명과 {art} 내용이 거의 겹치지 않음. 원문 제목: {title}"
    return None


def _find_doc_mentions(text: str) -> list[tuple[int, int, str | None]]:
    """(시작, 끝, doc_id|None) 목록. None = 범위 밖 법령."""
    spans: list[tuple[int, int, str | None]] = []
    taken: list[tuple[int, int]] = []

    def free(a: int, b: int) -> bool:
        return all(b <= x or a >= y for x, y in taken)

    for m in _OUT_OF_SCOPE.finditer(text):
        spans.append((m.start(), m.end(), None))
        taken.append((m.start(), m.end()))
    for doc, pat in _DOC_PATTERNS:
        for m in pat.finditer(text):
            if free(m.start(), m.end()):
                spans.append((m.start(), m.end(), doc))
                taken.append((m.start(), m.end()))
    return sorted(spans)


def _citations(text: str) -> list[tuple[str | None, re.Match[str]]]:
    """문서 이름 바로 뒤에 이어지는 조 인용 사슬만 뽑는다 (계약서 자기 조항 언급은 제외)."""
    out: list[tuple[str | None, re.Match[str]]] = []
    for _, end, doc in _find_doc_mentions(text):
        pos = end
        # 문서 이름 뒤의 (건설업종, 2024.12.24) 같은 괄호, 「」, 공백, '상'·'의' 건너뛰기
        skip = re.compile(r"\s*(?:\([^()]{0,40}\))?\s*(?:상|의)?\s*")
        pos = skip.match(text, pos).end()
        while True:
            m = _ART.match(text, pos)
            if not m:
                break
            out.append((doc, m))
            sep = _CHAIN_SEP.match(text, m.end())
            if not sep or not _ART.match(text, sep.end()):
                break
            pos = sep.end()
    return out


def check_text(text: str, contract_text: str = "") -> CitationCheck:
    """standard_ref + deviation_summary 를 이어 붙인 텍스트를 검사한다."""
    result = CitationCheck()
    idx = _index()
    cited_texts: list[str] = []
    for doc, m in _citations(text):
        art = f"제{m.group(1)}조" + (f"의{m.group(2)}" if m.group(2) else "")
        desc = (m.group(4) or "").strip()
        label = m.group(0).strip()
        if doc is None:
            result.issues.append(CitationIssue(kind="out_of_scope", ref=label, detail="원문 없는 법령"))
            continue
        ref = f"{DOC_LABEL[doc]} {label}"
        clause = idx[doc].get(art)
        if clause is None:
            result.issues.append(
                CitationIssue(kind="missing_article", ref=ref, detail=f"{DOC_LABEL[doc]}에 {art} 없음")
            )
            continue
        result.checked.append(ref)
        paras = [int(p) for p in _PARA_NUM.findall(m.group(3) or "")]
        by_para = _paragraphs(clause.text)
        unit = clause.text
        if paras == [1] and not by_para:
            paras = []  # 항이 하나뿐인 조(① 표시 없음)를 '제1항'으로 인용한 것은 오류가 아니다
        if paras:
            missing = [p for p in paras if p not in by_para]
            if missing:
                result.issues.append(
                    CitationIssue(kind="missing_paragraph", ref=ref, detail=f"{art}에 제{missing[0]}항 없음")
                )
                continue
            unit = "\n".join(by_para[p] for p in paras)
        cited_texts.append(clause.text)
        if not desc:
            continue
        nums = _norm_numbers(desc) - _norm_numbers(clause.title)
        absent = sorted(n for n in nums if n not in _norm_numbers(unit))
        if absent:
            where = f"{art}" + (f" 제{'·'.join(map(str, paras))}항" if paras else "")
            result.issues.append(
                CitationIssue(kind="number_mismatch", ref=ref, detail=f"{where}에 {', '.join(absent)} 없음")
            )
        elif problem := _title_problem(doc, art, desc, clause.title, unit):
            result.issues.append(CitationIssue(kind="title_mismatch", ref=ref, detail=problem))
    # 설명문 속 숫자의 출처: 계약서 조항, 인용한 조문, 규칙 기준값 중 어디에도 없으면 경고
    known = _norm_numbers(contract_text) | _threshold_numbers()
    for t in cited_texts:
        known |= _norm_numbers(t)
    cited_spans = [m.span() for _, m in _citations(text)]
    for m in _NUM.finditer(text):
        if any(a <= m.start() < b for a, b in cited_spans):
            continue  # 괄호 속 숫자는 위에서 이미 검사
        key = next(iter(_norm_numbers(m.group(0))))
        if key not in known:
            ctx = text[max(0, m.start() - 15) : m.end() + 5].replace("\n", " ")
            result.issues.append(CitationIssue(kind="unsourced_number", ref=key, detail=f"…{ctx}…"))
    return result


def annotate(finding: Finding, contract_text: str | None = None) -> Finding:
    """finding 의 근거·설명문 인용을 검사해 citation_issues 를 채운 사본을 돌려준다 (범위 밖 법령은 기록하지 않음).

    - 규칙 판정(source=rule)은 원문 인용이 붙은 기준값으로 만들어지므로 검사하지 않는다.
    - contract_text 는 조항 전문을 넘긴다 (Finding.contract_text 는 앞 400자 발췌라 숫자 출처 확인에 부족).
    """
    if finding.source == "rule":
        return finding
    res = check_text(f"{finding.standard_ref} | {finding.deviation_summary}", contract_text or finding.contract_text)
    issues = [i for i in res.issues if i.kind != "out_of_scope"]
    return finding.model_copy(update={"citation_issues": issues})
