"""합성 평가셋 생성기 (M2). 시드 고정 → 언제 돌려도 같은 파일이 나온다.

입력: data/raw 표준하도급계약서 본문 60개 조항 (실제 원문)
출력:
  data/synthetic/synthetic_contract_NN.txt   합성 계약서 3개 (**synthetic**, 실제 계약서 아님)
  eval/cases/synthetic_contract_NN.yaml      정답 라벨 (변형 주입 조항)

생성 방식 (전부 결정적):
  1. 표준 본문에서 변형 대상이 아닌 조항 중 일부를 무작위로 **삭제**하고 조 번호를 다시 매긴다
     (실제 계약서처럼 표준과 번호가 어긋나게 해서 검색이 번호만 보고 맞히지 못하게 함).
  2. 변형 카탈로그(MUTATIONS)에서 계약서마다 8개를 뽑아 조항 본문에 **주입**한다.
     각 변형은 원문에 패턴이 실제로 있어야 하고, 적용 후 본문이 반드시 달라져야 한다 (assert).
  3. 당사자 명칭을 "원사업자"→"갑", "수급사업자"→"을"로 바꾼다 (실무 계약서 관행).
  나머지 조항은 표준 그대로 = 정상 조항 (오탐 측정용).

사용: .venv/bin/python scripts/make_synthetic.py [--seed 20261104] [--n 3] [--k 8]
"""

from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from contract_review.schemas import Category, Clause, EvalCase, RiskLevel
from contract_review.standards import load_standard_clauses

ROOT = Path(__file__).resolve().parents[1]
# 평가셋 버전. v1 은 결과 재현을 위해 그대로 둔다 (CLAUDE.md 규칙 9).
# v2 = v1 과 같은 시드·같은 변형·같은 삭제 추첨 + 조문 참조 재번호 버그 수정 (2026-11-08)
DATASETS = {
    "v1": {"out": ROOT / "data" / "synthetic", "cases": ROOT / "eval" / "cases", "fix_refs": False},
    "v2": {"out": ROOT / "data" / "synthetic_v2", "cases": ROOT / "eval" / "cases_v2", "fix_refs": True},
}
OUT_DIR = DATASETS["v1"]["out"]
CASES_DIR = DATASETS["v1"]["cases"]

# 조문 참조: "제11조", "제40조를 준용" 등. 바로 앞이 「…법」·시행령·고시면 외부 법령 참조라 건드리지 않는다.
_REF_RE = re.compile(r"제(\d+)조(?!의)")
_EXTERNAL_BEFORE = re.compile(r"(」|법|령|규칙|고시)\s*$")


def _internal_refs(body: str) -> list[re.Match[str]]:
    return [m for m in _REF_RE.finditer(body) if not _EXTERNAL_BEFORE.search(body[max(0, m.start() - 14) : m.start()])]


def _split_header(text: str) -> tuple[str, str]:
    """'제n조(제목) 본문' → ('제n조(제목)', ' 본문'). 참조 치환은 본문에만 한다."""
    i = text.index(")") + 1
    return text[:i], text[i:]


def _remap_refs(text: str, old_to_new: dict[str, str]) -> str:
    """본문의 계약서 내부 조문 참조를 새 번호로 한 번에 바꾼다 (연쇄 치환 방지)."""
    head, body = _split_header(text)
    out, last = [], 0
    for m in _internal_refs(body):
        new = old_to_new.get(m.group(0))
        if new is None:
            continue
        out.append(body[last : m.start()])
        out.append(new)
        last = m.end()
    out.append(body[last:])
    return head + "".join(out)


STANDARD_DOC = "ftc_standard_subcontract"


@dataclass(frozen=True)
class Mutation:
    id: str
    clause_id: str  # 표준하도급계약서 본문 조항
    category: Category
    risk: RiskLevel
    pattern: str  # 원문에 반드시 존재해야 하는 정규식
    replacement: str
    change: str  # 사람이 읽는 설명 (injected_change)


# 변형 카탈로그. pattern 은 data/raw 표준하도급계약서 본문에서 확인한 문자열이다.
MUTATIONS: list[Mutation] = [
    # ── 대금 지급 기한 (제40조, 제53조) ──
    Mutation(
        "pay_60_to_90",
        "제40조",
        Category.PAYMENT_DEADLINE,
        RiskLevel.HIGH,
        r"목적물 인수일부터 60일을 초과하지 아니한다",
        "목적물 인수일부터 90일을 초과하지 아니한다",
        "지급기일 상한 60일 → 90일",
    ),
    Mutation(
        "pay_owner_15_to_45",
        "제40조",
        Category.PAYMENT_DEADLINE,
        RiskLevel.HIGH,
        r"지급받은 날부터 15일\(대금의 지급기일이 그 전에 도래하는 경우에는 그 지급기일\) 이내",
        "지급받은 날부터 45일 이내",
        "발주자 기성금 수령 후 지급기한 15일 → 45일",
    ),
    Mutation(
        "pay_cash_ratio_removed",
        "제40조",
        Category.PAYMENT_DEADLINE,
        RiskLevel.HIGH,
        r"받은 현금비율 이상으로 지급한다",
        "받은 현금비율과 관계없이 전액 어음으로 지급할 수 있다",
        "현금비율 유지 의무 삭제, 전액 어음 지급 허용",
    ),
    Mutation(
        "pay_late_damages_removed",
        "제40조",
        Category.PAYMENT_DEADLINE,
        RiskLevel.MEDIUM,
        r"⑩ 원사업자가 정당한 사유가 없이 제1항 단서를 위반하여 하도급대금을 지급하는 경우에는 그 초과기간에 대하여 지연배상금을 지급한다\.",
        "⑩ 원사업자의 하도급대금 지급 지연에 대하여는 지연배상금을 지급하지 아니한다.",
        "지급 지연 시 지연배상금 조항 삭제",
    ),
    Mutation(
        "guarantee_30_to_90",
        "제53조",
        Category.PAYMENT_DEADLINE,
        RiskLevel.MEDIUM,
        r"원사업자는 계약체결일부터 30일 이내에 수급사업자에게",
        "원사업자는 계약체결일부터 90일 이내에 수급사업자에게",
        "대금지급보증 기한 30일 → 90일",
    ),
    # ── 설계변경과 대금 조정 (제35조) ──
    Mutation(
        "dc_adjust_30_to_90",
        "제35조",
        Category.DESIGN_CHANGE,
        RiskLevel.MEDIUM,
        r"증액 또는 감액받은 날부터 30일 이내에 한다",
        "증액 또는 감액받은 날부터 90일 이내에 한다",
        "설계변경 대금 조정 기한 30일 → 90일",
    ),
    Mutation(
        "dc_increase_optional",
        "제35조",
        Category.DESIGN_CHANGE,
        RiskLevel.HIGH,
        r"내용과 비율에 따라 하도급대금을 증액한다\.",
        "내용과 비율에 따라 하도급대금을 증액할 수 있다.",
        "증액 의무 → 원사업자 재량",
    ),
    Mutation(
        "dc_pay_15_to_60",
        "제35조",
        Category.DESIGN_CHANGE,
        RiskLevel.MEDIUM,
        r"수령한 날부터 15일 이내에 수급사업자에게 증액한 하도급대금을 지급한다",
        "수령한 날부터 60일 이내에 수급사업자에게 증액한 하도급대금을 지급한다",
        "증액분 지급 기한 15일 → 60일",
    ),
    Mutation(
        "dc_newitem_50_to_10",
        "제35조",
        Category.DESIGN_CHANGE,
        RiskLevel.MEDIUM,
        r"합한 금액의 100분의 50이내에서",
        "합한 금액의 100분의 10이내에서",
        "발주자 요구 설계변경 신규비목 단가 협의 범위 50% → 10%",
    ),
    # ── 지체상금 (제56조) ──
    Mutation(
        "delay_exemptions_removed",
        "제56조",
        Category.DELAY_PENALTY,
        RiskLevel.HIGH,
        r"③ 원사업자는 다음 각 호의 어느 하나에 해당한 경우 그 해당 일수를 제1항의 지체일수에 산입하지 아니한다\.",
        "③ 지체의 사유를 불문하고 모든 지체일수를 제1항의 지체일수에 산입한다. 다음 각 호의 경우에도 같다.",
        "불가항력 등 지체일수 불산입 사유 삭제",
    ),
    Mutation(
        "delay_no_partial_deduction",
        "제56조",
        Category.DELAY_PENALTY,
        RiskLevel.MEDIUM,
        r"그 부분에 상당하는 금액을 대금에서 공제한 금액을 기준으로 지체상금을 계산한다",
        "그 부분의 인수 여부와 관계없이 계약금액 전체를 기준으로 지체상금을 계산한다",
        "기성 인수 부분 공제 없이 전체 금액 기준 지체상금",
    ),
    Mutation(
        "delay_unilateral_offset",
        "제56조",
        Category.DELAY_PENALTY,
        RiskLevel.MEDIUM,
        r"그 밖의 예치금에서 합의 후 공제할 수 있다",
        "그 밖의 예치금에서 수급사업자의 동의 없이 임의로 공제할 수 있다",
        "지체상금 공제 시 합의 요건 삭제",
    ),
    # ── 하자담보 책임 (제57조) ──
    Mutation(
        "defect_period_cap_removed",
        "제57조",
        Category.DEFECT_LIABILITY,
        RiskLevel.HIGH,
        r"⑤ 이 계약에서 정한 하자담보책임기간이 「건설산업기본법」 등 관련 법령에서 정한 하자담보책임기간 보다 더 장기인 경우에는 「건설산업기본법」 등에서 정한 기간으로 한다\.",
        "⑤ 이 계약에서 정한 하자담보책임기간은 「건설산업기본법」 등 관련 법령에서 정한 기간보다 장기이더라도 그대로 적용한다.",
        "하자담보책임기간 법정 상한 적용 조항 삭제",
    ),
    Mutation(
        "defect_refund_10_to_90",
        "제57조",
        Category.DEFECT_LIABILITY,
        RiskLevel.MEDIUM,
        r"청구가 있는 날부터 10일 이내에 수급사업자에게 제1항의 하자보수보증금을 반환한다",
        "청구가 있는 날부터 90일 이내에 수급사업자에게 제1항의 하자보수보증금을 반환한다",
        "하자보수보증금 반환 기한 10일 → 90일",
    ),
    Mutation(
        "defect_exemptions_removed",
        "제57조",
        Category.DEFECT_LIABILITY,
        RiskLevel.HIGH,
        r"④ 제3항에도 불구하고 다음 각 호의 어느 하나의 사유로 발생한 하자에 대하여 원사업자는 수급사업자에게 그 하자 보수를 청구할 수 없다\.",
        "④ 제3항의 하자에는 다음 각 호의 사유로 발생한 하자를 포함하며, 수급사업자는 원인을 불문하고 모든 하자를 보수한다.",
        "원사업자 제공 자재·지시로 인한 하자 면책 삭제",
    ),
    # ── 계약 해제·해지 (제58조) ──
    Mutation(
        "term_one_sided",
        "제58조",
        Category.TERMINATION,
        RiskLevel.HIGH,
        r"① 원사업자 또는 수급사업자는 다음 각 호의 어느 하나에 해당하는 경우에는 서면으로",
        "① 원사업자는 다음 각 호의 어느 하나에 해당하는 경우에는 서면으로",
        "해제·해지권을 원사업자에게만 부여",
    ),
    Mutation(
        "term_40_to_70",
        "제58조",
        Category.TERMINATION,
        RiskLevel.MEDIUM,
        r"하도급대금이 100분의 40 이상 감소한 경우",
        "하도급대금이 100분의 70 이상 감소한 경우",
        "수급사업자 해지 사유(대금 감소) 40% → 70%",
    ),
    Mutation(
        "term_applies_to_completed",
        "제58조",
        Category.TERMINATION,
        RiskLevel.HIGH,
        r"다만, 기성부분에 대해서는 해제하지 아니한다\.",
        "기성부분에 대해서도 해제할 수 있다.",
        "기성부분 해제 금지 삭제",
    ),
    Mutation(
        "term_damages_one_sided",
        "제58조",
        Category.TERMINATION,
        RiskLevel.MEDIUM,
        r"⑤ 원사업자 또는 수급사업자는 상대방에 대하여 해제 또는 해지로 인해 발생한 손해배상을 청구할 수 있다\.",
        "⑤ 원사업자는 수급사업자에 대하여 해제 또는 해지로 인해 발생한 손해배상을 청구할 수 있다.",
        "해지 손해배상 청구권을 원사업자에게만 부여",
    ),
    # ── 부당 특약·책임 전가 (제47조, 제22조) ──
    Mutation(
        "unfair_civil_complaint_cost",
        "제47조",
        Category.UNFAIR_SPECIAL_TERMS,
        RiskLevel.HIGH,
        r"2\. 원사업자가 부담하여야 할 민원처리, 산업재해 등과 관련된 비용을 수급사업자에게 부담시키는 약정",
        "2. 민원처리, 산업재해 등과 관련된 비용은 수급사업자가 전액 부담한다.",
        "민원·산재 비용 수급사업자 전가",
    ),
    Mutation(
        "unfair_no_adjust_request",
        "제47조",
        Category.UNFAIR_SPECIAL_TERMS,
        RiskLevel.HIGH,
        r"7\. 계약기간 중 수급사업자가 「하도급거래 공정화에 관한 법률」 제16조의2에 따라 하도급대금 조정을 신청할 수 있는 권리를 제한하는 약정",
        "7. 수급사업자는 계약기간 중 하도급대금의 조정을 신청하지 아니한다.",
        "하도급대금 조정 신청권 포기",
    ),
    Mutation(
        "unfair_safety_cost",
        "제22조",
        Category.UNFAIR_SPECIAL_TERMS,
        RiskLevel.HIGH,
        r"제22조\(산업안전보건관리비\) ",
        "제22조(산업안전보건관리비) 산업안전보건관리비는 수급사업자가 전액 부담하며 원사업자는 이를 계상하지 아니한다. ",
        "산업안전보건관리비 수급사업자 전액 부담",
    ),
    # ── 손해배상 한도 (제54조) ──
    Mutation(
        "damages_treble_to_single",
        "제54조",
        Category.DAMAGES_CAP,
        RiskLevel.MEDIUM,
        r"손해의 3배를 넘지 아니하는 범위에서 배상을 청구할 수 있다",
        "실제 발생한 손해액을 넘지 아니하는 범위에서 배상을 청구할 수 있다",
        "원사업자 위반 시 3배 배상 → 1배",
    ),
    Mutation(
        "damages_cap_5pct",
        "제54조",
        Category.DAMAGES_CAP,
        RiskLevel.HIGH,
        r"① 원사업자 또는 수급사업자가 이 계약을 위반하여 상대방에게 손해를 입힌 경우 그 손해를 배상할 책임이 있다\.",
        "① 원사업자 또는 수급사업자가 이 계약을 위반하여 상대방에게 손해를 입힌 경우 그 손해를 배상할 책임이 있다. 다만, 원사업자의 배상책임은 어떠한 경우에도 하도급대금의 100분의 5를 초과하지 아니한다.",
        "원사업자 배상책임 상한 5% 신설",
    ),
    Mutation(
        "damages_sub_strict",
        "제54조",
        Category.DAMAGES_CAP,
        RiskLevel.MEDIUM,
        r"제3자와 연대하여 책임을 진다\. 다만, 수급사업자 및 제3자가 고의 또는 과실 없음을 증명한 경우에는 그러하지 아니하다\.",
        "제3자와 연대하여 고의·과실 유무를 불문하고 책임을 진다.",
        "수급사업자 무과실 면책 삭제",
    ),
]

PARTY_SUBS = [("원사업자", "갑"), ("수급사업자", "을")]


def _apply(m: Mutation, text: str) -> str:
    assert re.search(m.pattern, text), f"{m.id}: 원문에 패턴 없음 ({m.clause_id})"
    new = re.sub(m.pattern, m.replacement, text, count=1)
    assert new != text, f"{m.id}: 적용 후 본문이 그대로"
    return new


def _renumber(text: str, old_id: str, new_id: str) -> str:
    assert text.startswith(old_id), (old_id, text[:20])
    return new_id + text[len(old_id) :]


def build_contract(
    idx: int, rng: random.Random, standard: list[Clause], k: int, drop: int, fix_refs: bool = False
) -> tuple[str, list[EvalCase], dict[str, str]]:
    """(계약서 텍스트, 변형 라벨, 전체 조항 매핑 {합성 clause_id: 표준 clause_id})"""
    contract_id = f"synthetic_contract_{idx:02d}"
    # 1) 변형 선택: 조항당 최대 1개 (평가 매칭 키가 조항+카테고리라서)
    pool = MUTATIONS[:]
    rng.shuffle(pool)
    chosen: list[Mutation] = []
    used: set[str] = set()
    for m in pool:
        if m.clause_id not in used:
            chosen.append(m)
            used.add(m.clause_id)
        if len(chosen) == k:
            break
    # 2) 변형 대상이 아니고 제1·2조(목적·정의)가 아닌 조항 중 drop 개 삭제
    droppable = [c.clause_id for c in standard if c.clause_id not in used and c.clause_id not in {"제1조", "제2조"}]
    dropped = set(rng.sample(droppable, drop))
    if fix_refs:
        # v2: 남은 조항이 참조하는 조항은 삭제를 취소한다 (추첨 자체는 v1 과 같게 유지 → 난수 흐름 동일)
        changed = True
        while changed:
            changed = False
            for c in standard:
                if c.clause_id in dropped:
                    continue
                for m in _internal_refs(_split_header(c.text)[1]):
                    if m.group(0) in dropped:
                        dropped.discard(m.group(0))
                        changed = True
    kept = [c for c in standard if c.clause_id not in dropped]
    old_to_new = {c.clause_id: f"제{n}조" for n, c in enumerate(kept, start=1)}
    # 3) 재번호 + 변형 주입 + 당사자 명칭 치환
    by_clause = {m.clause_id: m for m in chosen}
    cases: list[EvalCase] = []
    clause_map: dict[str, str] = {}
    parts = [
        f"하도급계약서 ({contract_id}, SYNTHETIC — 평가용 합성 데이터, 실제 계약 아님)",
        "본 문서는 공정거래위원회 건설업종 표준하도급계약서(2024.12.24)를 바탕으로 자동 생성되었다.",
        "",
    ]
    for n, c in enumerate(kept, start=1):
        new_id = f"제{n}조"
        clause_map[new_id] = c.clause_id
        text = _renumber(c.text, c.clause_id, new_id)
        if c.clause_id in by_clause:
            m = by_clause[c.clause_id]
            # 변형 패턴은 표준 번호 기준이라 재번호 전에 맞춰 적용
            text = _renumber(_apply(m, c.text), c.clause_id, new_id)
            cases.append(
                EvalCase(
                    contract_id=contract_id,
                    clause_id=new_id,
                    category=m.category,
                    expected_risk=m.risk,
                    injected_change=m.change,
                    mutation_id=m.id,
                    standard_doc=STANDARD_DOC,
                    standard_clause_id=c.clause_id,
                )
            )
        if fix_refs:
            text = _remap_refs(text, old_to_new)
        for a, b in PARTY_SUBS:
            text = text.replace(a, b)
        parts.append(text)
        parts.append("")
    return "\n".join(parts), cases, clause_map


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--n", type=int, default=3, help="계약서 수")
    ap.add_argument("--k", type=int, default=8, help="계약서당 변형 수")
    ap.add_argument("--drop", type=int, default=10, help="계약서당 삭제할 정상 조항 수")
    ap.add_argument("--dataset", default="v1", choices=list(DATASETS))
    args = ap.parse_args()

    ds = DATASETS[args.dataset]
    out_dir, cases_dir = ds["out"], ds["cases"]
    standard = load_standard_clauses()[STANDARD_DOC]
    out_dir.mkdir(parents=True, exist_ok=True)
    cases_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    total = 0
    for i in range(1, args.n + 1):
        text, cases, clause_map = build_contract(i, rng, standard, args.k, args.drop, fix_refs=ds["fix_refs"])
        (out_dir / f"synthetic_contract_{i:02d}.txt").write_text(text, encoding="utf-8")
        (cases_dir / f"synthetic_contract_{i:02d}.yaml").write_text(
            yaml.safe_dump(
                {"cases": [c.model_dump(mode="json") for c in cases], "clause_map": clause_map},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        total += len(cases)
        print(
            f"{out_dir.name}/synthetic_contract_{i:02d}.txt: 조항 {text.count(chr(10) + '제')}개, 변형 {len(cases)}개"
        )
    print(f"총 라벨 {total}개 (dataset={args.dataset}, seed={args.seed})")


if __name__ == "__main__":
    main()
