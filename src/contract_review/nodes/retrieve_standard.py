"""retrieve_standard 노드: Clause → 대응 표준 조항 top-k (RetrievedRef)."""

from __future__ import annotations

from contract_review.retrieval import StandardIndex, query_text
from contract_review.schemas import Clause, RetrievedRef


def retrieve_standard(
    clause: Clause, index: StandardIndex, k: int = 3, doc_filter: str | None = None
) -> list[RetrievedRef]:
    return index.search(query_text(clause), k=k, doc_filter=doc_filter)
