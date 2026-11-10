# baseline / v1 / v2 비교 (2026-11-10)

| 평가셋 | config | LLM | recall | detection_rate | precision | citation_accuracy | retrieval_hit3 | risk_match | avg_sec_per_contract | avg_input_tokens | avg_llm_calls | dropped_findings | citation_errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| set-public | baseline | anthropic:claude-sonnet-5-5 | 1.00 | 1.00 | 1.00 | – | – | 1.00 | 14.69 | 51750 | 1.00 | 0 | – |
| set-public | v1 | anthropic:claude-sonnet-5-5 | 1.00 | 1.00 | 1.00 | – | – | 0.40 | 17.06* | 313498 | 61.00 | 0 | – |
| set-public | v2 | anthropic:claude-sonnet-5-5 | 1.00 | 1.00 | 1.00 | – | – | 0.40 | 0.41* | 313498 | 61.00 | 0 | – |
| set-v1 | baseline | anthropic:claude-sonnet-5-5 | 0.92 | – | 0.81 | 0.00 | – | 0.82 | 0.01* | 42887 | 1.00 | 0 | – |
| set-v1 | v1 | anthropic:claude-sonnet-5-5 | 0.96 | – | 0.85 | 1.00 | 1.00 | 0.57 | 0.32* | 251952 | 50.00 | 0 | – |
| set-v1 | v2 | anthropic:claude-sonnet-5-5 | 1.00 | – | 0.89 | 1.00 | 1.00 | 0.62 | 0.33* | 252158 | 50.00 | 0 | – |
| set-v2 | baseline | anthropic:claude-sonnet-5-5 | 0.96 | 0.96 | 0.85 | 0.00 | – | 0.74 | 44.85 | 43560 | 1.00 | 0 | 23 |
| set-v2 | v1 | anthropic:claude-sonnet-5-5 | 1.00 | 1.00 | 0.92 | 1.00 | 1.00 | 0.58 | 44.19 | 257660 | 51.33 | 0 | 0 |
| set-v2 | v2 | anthropic:claude-sonnet-5-5 | 1.00 | 1.00 | 0.92 | 1.00 | 1.00 | 0.58 | 40.37 | 257866 | 51.33 | 0 | 0 |

\* 캐시 적중이 있어 처리 시간이 실제 호출 시간이 아님 (비교 무효)
