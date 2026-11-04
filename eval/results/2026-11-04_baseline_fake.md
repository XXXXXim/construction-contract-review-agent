# 평가 결과: baseline (2026-11-04)

- LLM: `fake` · 검색: `bm25` · 계약서 3개 · 라벨 24개 · finding 0개

| 지표 | 값 |
|---|---|
| Recall | 0.00 |
| Precision | – |
| Citation accuracy | – |
| Retrieval hit@3 | – |
| Risk match (보조) | – |
| 계약서당 처리 시간(초) | 0.01 |
| 계약서당 토큰 (입력/출력) | 0 / 0 |
| 계약서당 LLM 호출 | 1.00 |
| 근거 검증으로 제외된 finding | 0 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| synthetic_contract_01 | 8 | 0 | 0 | 제31조/design_change (dc_adjust_30_to_90), 제34조/payment_deadline (pay_cash_ratio_removed), 제41조/unfair_special_terms (unfair_civil_complaint_cost), 제45조/payment_deadline (guarantee_30_to_90), 제46조/damages_cap (damages_treble_to_single), 제48조/delay_penalty (delay_exemptions_removed), 제49조/defect_liability (defect_refund_10_to_90), 제50조/termination (term_40_to_70) | - |
| synthetic_contract_02 | 8 | 0 | 0 | 제18조/unfair_special_terms (unfair_safety_cost), 제29조/design_change (dc_pay_15_to_60), 제32조/payment_deadline (pay_owner_15_to_45), 제39조/unfair_special_terms (unfair_civil_complaint_cost), 제43조/payment_deadline (guarantee_30_to_90), 제44조/damages_cap (damages_cap_5pct), 제46조/delay_penalty (delay_unilateral_offset), 제48조/termination (term_damages_one_sided) | - |
| synthetic_contract_03 | 8 | 0 | 0 | 제28조/design_change (dc_pay_15_to_60), 제33조/payment_deadline (pay_60_to_90), 제39조/unfair_special_terms (unfair_civil_complaint_cost), 제44조/payment_deadline (guarantee_30_to_90), 제45조/damages_cap (damages_sub_strict), 제47조/delay_penalty (delay_unilateral_offset), 제48조/defect_liability (defect_exemptions_removed), 제49조/termination (term_one_sided) | - |
