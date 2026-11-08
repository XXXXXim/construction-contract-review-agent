# baseline / v1 / v2 비교 (2026-11-08)

| config | LLM | recall | precision | citation_accuracy | retrieval_hit3 | risk_match | avg_sec_per_contract | avg_input_tokens | avg_llm_calls | dropped_findings |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | anthropic:claude-sonnet-5-5 | 0.92 | 0.81 | 0.00 | – | 0.82 | 53.02 | 42887 | 1.00 | 0 |
| v1 | anthropic:claude-sonnet-5-5 | 0.96 | 0.85 | 1.00 | 1.00 | 0.57 | 35.40 | 251952 | 50.00 | 0 |
| v2 | anthropic:claude-sonnet-5-5 | 1.00 | 0.89 | 1.00 | 1.00 | 0.62 | 4.77 | 252158 | 50.00 | 0 |
