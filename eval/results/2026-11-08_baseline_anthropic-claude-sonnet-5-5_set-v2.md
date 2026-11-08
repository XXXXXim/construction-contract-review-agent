# 평가 결과: baseline · 평가셋 set-v2 (2026-11-08)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 3개 · 라벨 24개 · finding 27개

| 지표 | 값 |
|---|---|
| Recall | 0.92 |
| Precision | 0.81 |
| Citation accuracy | 0.00 |
| Retrieval hit@3 | – |
| Risk match (보조) | 0.73 |
| 계약서당 처리 시간(초) | 47.79 |
| 계약서당 토큰 (입력/출력) | 43,560 / 7,368 |
| 계약서당 LLM 호출 | 1.00 |
| 근거 검증으로 제외된 finding | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 0 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| synthetic_contract_01 | 8 | 8 | 7 | 제50조/termination (term_40_to_70) | 제18조/unfair_special_terms |
| synthetic_contract_02 | 8 | 9 | 8 | - | 제16조/damages_cap |
| synthetic_contract_03 | 8 | 10 | 7 | 제29조/design_change (dc_pay_15_to_60) | 제29조/payment_deadline, 제16조/damages_cap, 제51조/defect_liability |
