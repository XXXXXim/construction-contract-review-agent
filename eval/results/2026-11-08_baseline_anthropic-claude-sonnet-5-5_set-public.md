# 평가 결과: baseline · 평가셋 set-public (2026-11-08)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 5개 · 라벨 5개 · finding 6개

| 지표 | 값 |
|---|---|
| Recall | 1.00 |
| 탐지율 (카테고리 무관) | 1.00 |
| Precision | 1.00 |
| Citation accuracy | – |
| Retrieval hit@3 | – |
| Risk match (보조) | 1.00 |
| 계약서당 처리 시간(초) | 14.69 |
| 계약서당 토큰 (입력/출력) | 51,750 / 1,798 |
| 계약서당 LLM 호출 | 1.00 |
| 근거 검증으로 제외된 finding | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 0 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| public_case_01 | 1 | 1 | 1 | - | - |
| public_case_02 | 1 | 1 | 1 | - | - |
| public_case_03 | 1 | 2 | 1 | - | - |
| public_case_04 | 1 | 1 | 1 | - | - |
| public_case_05 | 1 | 1 | 1 | - | - |
