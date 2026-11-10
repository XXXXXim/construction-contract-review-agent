# P6. 요구사항 추적표

> 2026-11-08 기준. 요구사항(`02_requirements.md`) → 설계(`03_design.md`) → 구현 → 테스트 → 결과를 한 줄로 잇는다.
> 테스트는 `make test` (102 passed, API 키 불필요). "실측"은 실제 LLM(claude-sonnet-5-5) 평가 결과다.

## 기능 요구사항
| ID | 요구사항 | 설계 | 구현 | 검증 | 결과 |
|---|---|---|---|---|---|
| FR-01 | PDF/TXT 읽기 | ADR-02, §3 parse | `nodes/parse.py` | `test_real_sources_split`, `test_parse_rejects_unknown_suffix`, `test_molit_layout_extraction_keeps_spaces` | ✅ 원문 3종 파싱 (국토부 PDF 는 띄어쓰기 소실 자동 감지 후 layout 재추출) |
| FR-02 | 조항 분할·ID·제목 | ADR-02, §3 split_clauses | `nodes/split_clauses.py` | `test_real_sources_split`, `test_split_accepts_header_variants`, `test_split_does_not_treat_references_as_headers`, `test_split_spaced_sub_article` | ✅ 표준하도급 60 / 표준도급 43 / 하도급법 65 조항 |
| FR-03 | 별첨·부칙·장래 시행 분리 | ADR-02 | `nodes/split_clauses.py` | `test_addendum_and_annex_sections`, `test_law_future_versions_are_separated`, `test_molit_contract_body_is_annex_after_addendum` | ✅ |
| FR-04 | 대응 표준 조항 top-k 검색 | ADR-03, §3 StandardIndex | `retrieval.py`, `nodes/retrieve_standard.py` | `test_retrieval_hit_at_3_on_synthetic_set_is_reasonable`, `test_bm25_finds_standard_clause_for_rewritten_text` | ✅ hit@3 1.00 (set-v1 150 질의, set-v2 154 질의) |
| FR-05 | 하이브리드 검색 + BM25 폴백 | ADR-03, ADR-04 | `retrieval.py` (`make_embedder`, RRF) | `test_doc_filter_restricts_results` (BM25 경로) | 🟡 BM25 만 검증. 임베딩 키(OpenAI) 없어 하이브리드 미실행 |
| FR-06 | 숫자 항목 규칙 판정 | ADR-05 | `nodes/rule_check.py`, `thresholds.py`, `data/thresholds.yaml` | `test_rule_detects_longer_payment_deadline`, `test_rule_silent_on_unchanged_clause_and_lower_multiplier_flagged`, `test_threshold_quote_exists_in_source` | ✅ 실측: set-v2 에서 v1 이 놓친 2건을 규칙이 잡음 |
| FR-07 | LLM 구조화 판정 | ADR-07, §5 LLM 출력 계약 | `nodes/llm_judge.py`, `llm.py` | `test_fake_llm_reads_prompt_format_and_finds_diff`, `test_parse_variants`, `test_parse_recovers_truncated_array` | ✅ 실측: 파싱 실패 0, 잘림 0 (전 구성) |
| FR-08 | 근거 인용 검증 | ADR-06 | `nodes/llm_judge.py`, `textnorm.py` | `test_fabricated_evidence_is_dropped_but_real_quote_kept`, `test_judge_keeps_real_quote_with_different_middle_dot`, `test_quote_match_ignores_punctuation_variants` | ✅ 동작. 실측 폐기 0건 (Sonnet 인용이 전부 실존) → **효과 미관측** |
| FR-09 | 규칙 우선 중복 제거 | ADR-05 | `nodes/llm_judge.py` `dedupe_findings`, `graph.py` | `test_dedupe_prefers_rule_then_higher_risk`, `test_precision_counts_unique_clause_category` | ✅ |
| FR-10 | MD + JSON 리포트 | §3 report | `nodes/report.py` | `test_report_sorted_by_risk_and_has_disclaimer`, `test_e2e_v2_with_fake_llm_on_synthetic_contract` | ✅ 실측 샘플: `eval/results/sample_report/` |
| FR-11 | provider 설정 전환 | ADR-07 | `config.py`, `llm.py` | `test_settings_default_fake`, `test_anthropic_client_does_not_set_temperature` | ✅ fake·anthropic 실행. openai 미실행 |
| FR-12 | 시드 고정 합성 평가셋 | ADR-08 | `scripts/make_synthetic.py` | `test_generation_is_deterministic`, `test_committed_cases_match_contracts`, `test_dataset_v2_has_consistent_cross_references_and_v1_keeps_the_bug`, `test_dataset_v2_keeps_same_mutations_as_v1` | ✅ set-v1(원본, 바이트 동일 재생성), set-v2(조문 참조 수정판), 각 라벨 24개 |
| FR-18 | 공정위 실제 문구 탐지 | §6 | `scripts/make_public_cases.py`, `data/public_cases/cases.yaml`, `eval.py` (acceptable_categories, 탐지율) | `test_public_case_quotes_exist_in_decision_pdfs`, `test_public_contracts_append_clause_to_unmodified_standard`, `test_matches_uses_acceptable_categories` | ✅ 탐지 5/5 (세 구성 동일), 오탐 0 |
| FR-19 | 조문 인용 검증 | – | `citation_check.py`, `graph.py`(v2 주석), `nodes/report.py`(⚠️ 표시), `eval.py`(citation_errors), `scripts/audit_citations.py` | `tests/test_citation_check.py` (실제 오류·정상 인용, 통합, 거짓 경보 회귀) | ✅ baseline 40 / v1 0 / v2 0 (세 평가셋 합) |
| FR-13 | baseline/v1/v2 비교 | §2 설정별 경로, §6 | `graph.py`, `eval.py`, `scripts/run_real_eval.sh` | `test_run_eval_v2_and_baseline_produce_metrics`, `test_run_eval_on_dataset_v2`, `test_save_result_does_not_overwrite_same_day_run` | ✅ `eval/results/2026-11-08_compare_anthropic.md` |
| FR-14 | Streamlit UI | ADR-10 | `app/streamlit_app.py` | 수동: 기동·헬스체크 (11/04, 11/08 컨테이너 안) | ✅ 자동 테스트 없음 |
| FR-15 | Docker | – | `Dockerfile` | 수동: 빌드·컨테이너 안 v2 실행·UI 헬스체크 (11/04) | ✅ 세션 프록시 CA 를 추가한 검증용 Dockerfile 기준. 프록시 없는 환경에서 원본 Dockerfile 빌드는 미확인 |
| FR-16 | 조항 수정안 생성 | – | – | – | Won't |
| FR-17 | HWP 업로드, OCR | ADR-09 | – | – | Won't |

## 비기능 요구사항
| ID | 요구사항 | 구현·근거 | 검증 | 결과 |
|---|---|---|---|---|
| NFR-01 | 법령 수치를 기억으로 쓰지 않음 | `data/thresholds.yaml` 18개 항목(값 있음 16, TODO 2) 전부 원문 인용 보유, 규칙 사용 14 | `test_threshold_quote_exists_in_source` | ✅ TODO(source-needed) 2건(지체상금 요율, 하자담보 기간 상한) |
| NFR-02 | 법률 자문 아님 고지 | `schemas.DISCLAIMER` → 리포트·UI | `test_report_sorted_by_risk_and_has_disclaimer` | ✅ |
| NFR-03 | 키 없이 테스트 통과 | `FakeLLM`, `LLM_PROVIDER=fake` 기본 | `make test` | ✅ 102 passed |
| NFR-04 | 재현성 | 시드 고정, 결과 파일 덮어쓰기 방지 | `test_generation_is_deterministic`, set-v1 바이트 동일 재생성 | ✅ |
| NFR-05 | 키 보안 | 환경변수만, `.env` gitignore | 코드 검토 | ✅ 실측은 보스 맥에서 `read -s` 로 입력 |
| NFR-06 | 공개 자료·synthetic 표기 | `data/raw/README.md`, `data/synthetic*/README.md` | 파일명·README | ✅ |
| NFR-07 | 평가 정직성 | set-v1 라벨·계약서 미수정, 수정판은 별도 set-v2 | `test_dataset_v2_..._v1_keeps_the_bug` | ✅ 나쁜 숫자(risk_match, 근거 검증 효과 0)도 기록 |
| NFR-08 | 장애 내성 | 재시도 5회, 조항별 실패 격리, 캐시 | `test_llm_error_is_isolated_per_clause`, `test_cached_llm_reuses_response` | ✅ 실측 호출 실패 0 |
| NFR-09 | 처리 시간 기록 | `eval.py` `timing_valid` | `test_save_result_does_not_overwrite_same_day_run` | 🟡 baseline 48~53초/계약서만 유효. v1·v2 는 캐시 적중으로 미측정 |
| NFR-10 | 비용 기록 | 토큰 기록, 단가는 환경변수로만 | – | 🟡 토큰만 (입력 baseline 43.6k / v2 257.9k 계약서당) |
| NFR-11 | 의존성 통제 | `pyproject.toml` 허용 목록만 | – | ✅ |

## 미충족 요구사항과 이유
| ID | 상태 | 이유 | 해결 방법 |
|---|---|---|---|
| FR-05 | 🟡 | 임베딩용 OpenAI 키 없음 | OpenAI 키 확보 후 `EMBEDDING_PROVIDER=openai` 로 hit@3 비교. 단, 합성셋 BM25 hit@3 가 이미 1.00 이라 이 평가셋으로는 차이를 볼 수 없다 |
| NFR-09 | 🟡 | 평가를 캐시 켠 채 실행 | `LLM_CACHE=0 DATASET=v2 LLM_PROVIDER=anthropic bash scripts/run_real_eval.sh` (v1·v2 호출 비용 재발생) |
| NFR-10 | 🟡 | 단가를 기억으로 쓰지 않는 규칙 | 공식 가격 페이지 확인 후 `PRICE_IN_PER_1M`, `PRICE_OUT_PER_1M` 설정 |
