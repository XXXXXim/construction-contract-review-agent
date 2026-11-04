"""Streamlit UI (M6): 계약서 PDF/TXT 업로드 → 검토 리포트. 꾸미기는 비범위."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from contract_review.config import load_settings
from contract_review.graph import CONFIGS, Pipeline
from contract_review.nodes.report import render_markdown
from contract_review.schemas import DISCLAIMER

st.set_page_config(page_title="하도급 계약 검토 보조", layout="wide")
st.title("건설 하도급 계약 검토 보조 도구")
st.caption(DISCLAIMER)

settings = load_settings()
with st.sidebar:
    st.markdown("### 설정")
    config = st.selectbox("파이프라인", list(CONFIGS), index=list(CONFIGS).index("v2"))
    st.markdown(f"- LLM: `{settings.llm_provider}`\n- 임베딩: `{settings.embedding_provider}`")
    if settings.llm_provider == "fake":
        st.info("LLM_PROVIDER=fake: API 키 없이 결정적 판정기로 동작합니다 (.env 에서 바꿀 수 있음).")
    st.markdown("샘플: `data/synthetic/synthetic_contract_01.txt` (합성 데이터)")


@st.cache_resource(show_spinner="표준 조항 인덱스 생성 중…")
def get_pipeline(name: str) -> Pipeline:
    return Pipeline(name)


uploaded = st.file_uploader("하도급 계약서 (PDF 또는 TXT, 텍스트 레이어 필요)", type=["pdf", "txt"])
if uploaded is not None and st.button("검토 시작", type="primary"):
    suffix = Path(uploaded.name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = Path(tmp.name)
    try:
        with st.spinner("조항 분할 → 표준 조항 검색 → 규칙 검사 → LLM 판정 중…"):
            out = get_pipeline(config).run(tmp_path, contract_id=Path(uploaded.name).stem)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)
    report = out["report"]
    fs = report.sorted_findings()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("조항", report.stats.clause_count)
    c2.metric("지적", len(fs))
    c3.metric("높음", sum(f.risk_level.value == "high" for f in fs))
    c4.metric("처리 시간(초)", f"{report.stats.elapsed_sec:.1f}")
    md = render_markdown(report)
    st.markdown(md)
    st.download_button("리포트 Markdown 다운로드", md, file_name=f"{report.contract_id}.report.md")
    st.download_button(
        "리포트 JSON 다운로드",
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        file_name=f"{report.contract_id}.report.json",
    )
