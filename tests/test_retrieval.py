from contract_review.eval_retrieval import evaluate, load_queries
from contract_review.nodes.retrieve_standard import retrieve_standard
from contract_review.retrieval import StandardIndex, tokenize
from contract_review.schemas import Clause, RetrievedRef


def test_tokenize_neutralizes_parties_and_adds_bigrams() -> None:
    toks = tokenize("갑은 수급사업자에게 지체상금을 청구한다")
    assert "지체상금을" in toks and "지체" in toks and "상금" in toks
    assert "갑은" in toks  # 어절 단위는 보존
    assert "수급사업자에게" in toks


def test_bm25_finds_standard_clause_for_rewritten_text() -> None:
    index = StandardIndex.build()
    assert index.mode == "bm25"
    q = Clause(
        doc_id="x",
        clause_id="제9조",
        title="지체상금",
        text=(
            "제9조(지체상금) 을이 정당한 사유없이 계약의 이행을 지체한 경우 "
            "갑은 지체일수에 요율을 곱한 지체상금을 청구할 수 있다."
        ),
    )
    refs = retrieve_standard(q, index, k=3)
    assert all(isinstance(r, RetrievedRef) for r in refs)
    assert ("ftc_standard_subcontract", "제56조") in [(r.source_doc, r.clause_id) for r in refs]


def test_doc_filter_restricts_results() -> None:
    index = StandardIndex.build()
    q = Clause(doc_id="x", clause_id="제1조", title="손해배상", text="제1조(손해배상) 손해를 배상한다.")
    refs = retrieve_standard(q, index, k=3, doc_filter="subcontract_act")
    assert refs and {r.source_doc for r in refs} == {"subcontract_act"}


def test_retrieval_hit_at_3_on_synthetic_set_is_reasonable() -> None:
    """회귀 방지용 하한. 실제 측정값은 PROGRESS.md 에 기록한다."""
    index = StandardIndex.build()
    res = evaluate(index, load_queries(), ks=(3,))
    assert res["n_labeled"] >= 20
    assert res["hit@3_labeled"] >= 0.8
