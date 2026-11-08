# 평가 결과: v1 · 평가셋 set-v2 (2026-11-08)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 3개 · 라벨 24개 · finding 24개

| 지표 | 값 |
|---|---|
| Recall | 0.92 |
| Precision | 0.92 |
| Citation accuracy | 1.00 |
| Retrieval hit@3 | 1.00 |
| Risk match (보조) | 0.59 |
| 계약서당 처리 시간(초) | 20.96 |
| 계약서당 토큰 (입력/출력) | 257,660 / 14,423 |
| 계약서당 LLM 호출 | 51.33 |
| 근거 검증으로 제외된 finding | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 111 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| synthetic_contract_01 | 8 | 8 | 8 | - | - |
| synthetic_contract_02 | 8 | 8 | 7 | 제30조/design_change (dc_pay_15_to_60) | 제30조/payment_deadline |
| synthetic_contract_03 | 8 | 8 | 7 | 제29조/design_change (dc_pay_15_to_60) | 제29조/payment_deadline |
