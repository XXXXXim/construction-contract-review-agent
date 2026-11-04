"""합성 평가셋: 재현성, 라벨 수, 변형이 실제로 본문을 바꿨는지."""

import hashlib
import random
import sys
from pathlib import Path

import yaml

from contract_review.nodes.split_clauses import split_clauses
from contract_review.schemas import EvalCase, ParsedDocument
from contract_review.standards import load_standard_clauses

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_synthetic import MUTATIONS, PARTY_SUBS, STANDARD_DOC, _apply, build_contract  # noqa: E402


def _digest(seed: int) -> str:
    std = load_standard_clauses()[STANDARD_DOC]
    rng = random.Random(seed)
    h = hashlib.sha256()
    for i in range(1, 4):
        text, cases = build_contract(i, rng, std, 8, 10)
        h.update(text.encode())
        h.update(str([c.model_dump() for c in cases]).encode())
    return h.hexdigest()


def test_generation_is_deterministic() -> None:
    assert _digest(20261104) == _digest(20261104)
    assert _digest(20261104) != _digest(1)


def test_every_mutation_pattern_exists_and_changes_text() -> None:
    by_id = {c.clause_id: c for c in load_standard_clauses()[STANDARD_DOC]}
    for m in MUTATIONS:
        assert _apply(m, by_id[m.clause_id].text) != by_id[m.clause_id].text


def test_committed_cases_match_contracts() -> None:
    """커밋된 eval/cases 가 커밋된 data/synthetic 과 맞고, 라벨이 20개 이상이다."""
    total = 0
    for yml in sorted((ROOT / "eval" / "cases").glob("synthetic_contract_*.yaml")):
        cases = [EvalCase.model_validate(c) for c in yaml.safe_load(yml.read_text())["cases"]]
        text = (ROOT / "data" / "synthetic" / f"{yml.stem}.txt").read_text()
        clauses = {
            c.clause_id: c
            for c in split_clauses(ParsedDocument(doc_id=yml.stem, text=text, pages=1))
        }
        std = {c.clause_id: c for c in load_standard_clauses()[STANDARD_DOC]}
        for case in cases:
            assert case.clause_id in clauses, case
            # 변형 조항은 (갑/을 치환만 한) 표준 원문과 달라야 한다
            expected_normal = std[case.standard_clause_id].text
            for a, b in PARTY_SUBS:
                expected_normal = expected_normal.replace(a, b)
            body = clauses[case.clause_id].text.split(")", 1)[1]
            assert body != expected_normal.split(")", 1)[1]
        # 정상(변형 없음) 조항이 변형 조항보다 많아야 오탐을 잴 수 있다
        assert len(clauses) - len(cases) > len(cases)
        total += len(cases)
    assert total >= 20
