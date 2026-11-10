# 평가 결과: baseline · 평가셋 set-v2 (2026-11-10)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 3개 · 라벨 24개 · finding 27개

| 지표 | 값 |
|---|---|
| Recall | 0.96 |
| 탐지율 (카테고리 무관) | 0.96 |
| Precision | 0.85 |
| Citation accuracy | 0.00 |
| Retrieval hit@3 | – |
| Risk match (보조) | 0.74 |
| 계약서당 처리 시간(초) | 44.85 |
| 계약서당 토큰 (입력/출력) | 43,560 / 6,800 |
| 계약서당 LLM 호출 | 1.00 |
| 근거 검증으로 제외된 finding | 0 |
| 조문 인용 오류 / 대조한 인용 (FR-19) | 23 / 46 |
| 출처 없는 숫자 (경고) | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 0 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| synthetic_contract_01 | 8 | 9 | 7 | 제50조/termination (term_40_to_70) | 제18조/damages_cap, 제20조/delay_penalty |
| synthetic_contract_02 | 8 | 9 | 8 | - | 제16조/damages_cap |
| synthetic_contract_03 | 8 | 9 | 8 | - | 제19조/delay_penalty |
