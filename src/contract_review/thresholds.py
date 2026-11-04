"""data/thresholds.yaml 로더. 기준값은 전부 원문 출처(문서·조항·인용)를 가진다."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from contract_review.schemas import Category

ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_PATH = ROOT / "data" / "thresholds.yaml"


class SourceRef(BaseModel):
    source_doc: str
    clause_id: str
    quote: str


class Threshold(BaseModel):
    id: str
    category: Category
    value: float | None  # None = TODO(source-needed)
    unit: str
    description: str
    source_doc: str
    clause_id: str
    quote: str
    standard_ref: SourceRef | None = None

    @property
    def source_label(self) -> str:
        return f"{self.source_doc} {self.clause_id}"


@lru_cache(maxsize=1)
def load_thresholds(path: Path = THRESHOLDS_PATH) -> list[Threshold]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Threshold.model_validate(t) for t in data["thresholds"]]


def thresholds_for(category: Category) -> list[Threshold]:
    return [t for t in load_thresholds() if t.category == category and t.value is not None]
