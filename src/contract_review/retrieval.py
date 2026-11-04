"""표준 조항 검색 인덱스 (M3).

- BM25 (rank_bm25): 형태소 분석기 없이 한글을 다루기 위해 **어절 + 글자 2-gram** 토큰을 쓴다.
- 임베딩 (선택): EMBEDDING_PROVIDER=openai 이면 chromadb 인메모리 컬렉션에 OpenAI 임베딩을 넣고,
  BM25 결과와 **RRF(Reciprocal Rank Fusion)** 로 합친다. 임베딩을 못 쓰면 BM25만으로 동작한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from rank_bm25 import BM25Okapi

from contract_review.schemas import Clause, RetrievedRef
from contract_review.standards import load_standard_clauses

_TOKEN_RE = re.compile(r"[가-힣a-zA-Z0-9]+")
# 당사자 명칭은 계약서마다 다르므로(갑/을, 도급인/수급인) 검색에서는 중립화한다
_PARTY_ALIASES = {
    "원사업자": "당사자",
    "수급사업자": "당사자",
    "도급인": "당사자",
    "수급인": "당사자",
    "갑": "당사자",
    "을": "당사자",
    "발주자": "당사자",
}
# 거의 모든 조항에 나와 변별력이 없는 토큰
_STOP = {
    "당사자",
    "경우",
    "한다",
    "있다",
    "따라",
    "이",
    "그",
    "및",
    "또는",
    "등",
    "제",
    "조",
    "항",
    "호",
}


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for w in _TOKEN_RE.findall(text):
        w = _PARTY_ALIASES.get(w, w)
        if w in _STOP:
            continue
        tokens.append(w)
        if len(w) >= 3 and re.fullmatch(r"[가-힣]+", w):
            tokens.extend(w[i : i + 2] for i in range(len(w) - 1))
    return tokens


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


def make_embedder(provider: str) -> Embedder | None:
    """임베딩 provider 팩토리. 키가 없거나 provider=none 이면 None (BM25 단독)."""
    if provider == "openai":
        import os

        if not os.getenv("OPENAI_API_KEY"):
            return None
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model="text-embedding-3-small")
    return None


@dataclass
class StandardIndex:
    clauses: list[Clause]
    bm25: BM25Okapi
    embedder: Embedder | None = None
    _collection: object | None = field(default=None, repr=False)

    @classmethod
    def build(cls, clauses: list[Clause] | None = None, embedder: Embedder | None = None) -> StandardIndex:
        if clauses is None:
            clauses = [c for cs in load_standard_clauses().values() for c in cs]
        docs = [tokenize(f"{c.title} {c.text}") for c in clauses]
        idx = cls(clauses=clauses, bm25=BM25Okapi(docs), embedder=embedder)
        if embedder is not None:
            idx._build_vectors()
        return idx

    def _build_vectors(self) -> None:
        import chromadb

        assert self.embedder is not None
        client = chromadb.EphemeralClient()
        col = client.get_or_create_collection("standards", metadata={"hnsw:space": "cosine"})
        texts = [f"{c.title}\n{c.text[:1500]}" for c in self.clauses]
        col.add(
            ids=[str(i) for i in range(len(texts))],
            embeddings=self.embedder.embed_documents(texts),
            documents=texts,
        )
        self._collection = col

    @property
    def mode(self) -> str:
        return "hybrid" if self._collection is not None else "bm25"

    def _bm25_ranks(self, query: str, n: int) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
        return [(i, float(scores[i])) for i in order]

    def _vector_ranks(self, query: str, n: int) -> list[tuple[int, float]]:
        assert self.embedder is not None and self._collection is not None
        res = self._collection.query(  # type: ignore[attr-defined]
            query_embeddings=[self.embedder.embed_query(query)], n_results=n
        )
        ids, dists = res["ids"][0], res["distances"][0]
        return [(int(i), 1.0 - float(d)) for i, d in zip(ids, dists, strict=True)]

    def search(self, query: str, k: int = 3, doc_filter: str | None = None) -> list[RetrievedRef]:
        pool = max(k * 10, 30)
        bm = self._bm25_ranks(query, pool)
        if self._collection is None:
            fused = {i: s for i, s in bm}
            ranked = bm
        else:
            vec = self._vector_ranks(query, pool)
            fused = {}
            for lst in (bm, vec):  # RRF, k=60
                for rank, (i, _) in enumerate(lst):
                    fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
            ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)
        out: list[RetrievedRef] = []
        for i, score in ranked:
            c = self.clauses[i]
            if doc_filter and c.doc_id != doc_filter:
                continue
            out.append(
                RetrievedRef(
                    source_doc=c.doc_id,
                    clause_id=c.clause_id,
                    title=c.title,
                    text=c.text,
                    score=score,
                )
            )
            if len(out) == k:
                break
        return out


def query_text(clause: Clause, max_chars: int = 600) -> str:
    """검색 질의: 제목을 두 번 넣어 가중치를 주고 본문 앞부분을 붙인다."""
    return f"{clause.title} {clause.title} {clause.text[:max_chars]}"
