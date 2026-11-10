# 평가 결과: v2 · 평가셋 set-v2 (2026-11-10)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 3개 · 라벨 24개 · finding 26개

| 지표 | 값 |
|---|---|
| Recall | 1.00 |
| 탐지율 (카테고리 무관) | 1.00 |
| Precision | 0.92 |
| Citation accuracy | 1.00 |
| Retrieval hit@3 | 1.00 |
| Risk match (보조) | 0.58 |
| 계약서당 처리 시간(초) | 40.37 |
| 계약서당 토큰 (입력/출력) | 257,866 / 13,770 |
| 계약서당 LLM 호출 | 51.33 |
| 근거 검증으로 제외된 finding | 0 |
| 조문 인용 오류 / 대조한 인용 (FR-19) | 0 / 26 |
| 출처 없는 숫자 (경고) | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 0 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| synthetic_contract_01 | 8 | 8 | 8 | - | - |
| synthetic_contract_02 | 8 | 9 | 8 | - | 제28조/unfair_special_terms |
| synthetic_contract_03 | 8 | 9 | 8 | - | 제27조/unfair_special_terms |
