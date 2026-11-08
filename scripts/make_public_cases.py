"""공개 사례 평가셋(set-public) 생성기.

입력: data/public_cases/cases.yaml (공정위 의결서의 실제 계약 문구, 출처 포함)
출력:
  data/public_cases/public_case_NN.txt   시험용 계약서 = 표준하도급계약서(2024.12.24) 본문 60개 조항
                                         + 실제 문구를 "제61조(특약사항)"로 덧붙인 것
  eval/cases_public/public_case_NN.yaml  정답 라벨 (제61조) + clause_map

손대지 않은 표준 조항 60개를 지적하면 오탐으로 센다. 문구는 원문 그대로 넣는다 (가공 없음).
사용: .venv/bin/python scripts/make_public_cases.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

from contract_review.nodes.split_clauses import ARTICLE_RE
from contract_review.schemas import Category, EvalCase, RiskLevel
from contract_review.standards import load_standard_clauses

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "public_cases" / "cases.yaml"
OUT_DIR = ROOT / "data" / "public_cases"
CASES_DIR = ROOT / "eval" / "cases_public"
STANDARD_DOC = "ftc_standard_subcontract"
SPECIAL_ID = "제61조"


def load_public_cases() -> list[dict]:
    return yaml.safe_load(SRC.read_text(encoding="utf-8"))["cases"]


def _special_clause(text: str) -> list[str]:
    """원문이 '제9조 (최종정산 승인절차)'처럼 자체 조 머리로 시작하면 번호만 제61조로 바꾸고 제목은 살린다
    (표준 제9조와 번호 충돌 방지, 합성셋의 재번호와 같은 처리). 본문은 원문 그대로다."""
    first, _, rest = text.partition("\n")
    m = ARTICLE_RE.match(first)
    if m:
        return [f"{SPECIAL_ID}({m.group(3).strip()})", rest]
    return [f"{SPECIAL_ID}(특약사항)", text]


def build(case: dict, idx: int) -> tuple[str, EvalCase, dict[str, str]]:
    standard = load_standard_clauses()[STANDARD_DOC]
    contract_id = f"public_case_{idx:02d}"
    parts = [
        f"하도급계약서 ({contract_id}) — 평가용 시험 문서",
        "본문 제1조~제60조: 공정거래위원회 건설업종 표준하도급계약서(2024.12.24) 그대로.",
        f"제61조: 공정위 {case['decision']} 에 인용된 실제 계약 문구 그대로 ({case['location']}).",
        "",
        *[c.text + "\n" for c in standard],
        *_special_clause(case["clause_text"]),
        "",
    ]
    label = EvalCase(
        contract_id=contract_id,
        clause_id=SPECIAL_ID,
        category=Category(case["category"]),
        acceptable_categories=[Category(c) for c in case["acceptable_categories"]],
        expected_risk=RiskLevel(case["expected_risk"]),
        injected_change=f"[{case['id']}] {case['ftc_judgment']}",
        mutation_id=case["id"],
        standard_doc=STANDARD_DOC,
        standard_clause_id="",  # 실제 특약은 대응하는 표준 조항이 정해져 있지 않다 → citation·hit@3 대상 아님
        source=f"{case['decision']} / {case['location']}",
    )
    clause_map = {c.clause_id: c.clause_id for c in standard} | {SPECIAL_ID: ""}
    return "\n".join(parts), label, clause_map


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_public_cases()
    for i, case in enumerate(cases, start=1):
        text, label, clause_map = build(case, i)
        (OUT_DIR / f"public_case_{i:02d}.txt").write_text(text, encoding="utf-8")
        (CASES_DIR / f"public_case_{i:02d}.yaml").write_text(
            yaml.safe_dump(
                {"cases": [label.model_dump(mode="json")], "clause_map": clause_map},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        print(f"public_case_{i:02d}: {case['id']} ({case['respondent']})")
    print(f"총 {len(cases)}건 (set-public)")


if __name__ == "__main__":
    main()
