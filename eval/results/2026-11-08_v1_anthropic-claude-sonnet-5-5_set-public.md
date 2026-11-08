# 평가 결과: v1 · 평가셋 set-public (2026-11-08)

- LLM: `anthropic:claude-sonnet-5-5` · 검색: `bm25` · 계약서 5개 · 라벨 5개 · finding 5개

| 지표 | 값 |
|---|---|
| Recall | 1.00 |
| 탐지율 (카테고리 무관) | 1.00 |
| Precision | 1.00 |
| Citation accuracy | – |
| Retrieval hit@3 | – |
| Risk match (보조) | 0.40 |
| 계약서당 처리 시간(초) | 17.06 (캐시 적중 포함, 비교 무효) |
| 계약서당 토큰 (입력/출력) | 313,498 / 7,672 |
| 계약서당 LLM 호출 | 61.00 |
| 근거 검증으로 제외된 finding | 0 |
| LLM 호출 실패 / JSON 파싱 실패 | 0 / 0 |
| max_tokens 로 잘린 응답 / 캐시 적중 | 0 / 240 |
| 계약서당 비용(USD) | – |

## 계약서별

| 계약서 | 라벨 | finding | TP | 놓친 것 | 오탐 |
|---|---|---|---|---|---|
| public_case_01 | 1 | 1 | 1 | - | - |
| public_case_02 | 1 | 1 | 1 | - | - |
| public_case_03 | 1 | 1 | 1 | - | - |
| public_case_04 | 1 | 1 | 1 | - | - |
| public_case_05 | 1 | 1 | 1 | - | - |
