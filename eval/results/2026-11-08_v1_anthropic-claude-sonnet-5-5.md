# 평가 결과: v1 (2026-11-08)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 3개 · 라벨 24개 · finding 27개

| 지표 | 값 |
|---|---|
| Recall | 0.96 |
| Precision | 0.85 |
| Citation accuracy | 1.00 |
| Retrieval hit@3 | 1.00 |
| Risk match (보조) | 0.57 |
| 계약서당 처리 시간(초) | 35.40 |
| 계약서당 토큰 (입력/출력) | 251,952 / 14,341 |
| 계약서당 LLM 호출 | 50.00 |
| 근거 검증으로 제외된 finding | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 32 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| synthetic_contract_01 | 8 | 9 | 8 | - | 제11조/design_change |
| synthetic_contract_02 | 8 | 9 | 8 | - | 제11조/design_change |
| synthetic_contract_03 | 8 | 9 | 7 | 제28조/design_change (dc_pay_15_to_60) | 제11조/design_change, 제28조/payment_deadline |
