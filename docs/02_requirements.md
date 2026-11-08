# P1. 요구사항

> **사후 작성 (2026-11-08).** 원래 요구사항은 첫 프롬프트, `docs/SPEC.md`, `CLAUDE.md`에 흩어져 있었다.
> 그것을 ID를 붙여 한곳에 모았다. "상태"와 "검증" 칸은 지금 코드와 테스트 기준이다.
> 우선순위: **Must** 꼭 필요 / **Should** 있어야 함 / **Could** 있으면 좋음 / **Won't** 이번엔 안 함

## 유저 스토리
- **US-1** 계약 검토 담당자로서, 하도급 계약서 PDF를 올리면 **표준에서 벗어난 조항 목록을 위험도순으로** 받고 싶다. 그래야 50개 조항을 다 읽지 않고 문제 조항부터 볼 수 있다.
- **US-2** 계약 검토 담당자로서, 각 지적마다 **어느 표준 조항·법 조문 기준인지 원문 인용**을 보고 싶다. 그래야 AI 말을 그대로 믿지 않고 확인할 수 있다.
- **US-3** 계약 검토 담당자로서, "지급기일 60일 → 90일"처럼 **숫자가 바뀐 조항은 확실하게** 잡히길 원한다.
- **US-4** 개발자(보스)로서, 파이프라인을 바꿨을 때 **성능이 얼마나 변했는지 숫자로** 보고 싶다. 그래야 자소서와 면접에서 개선 근거를 댈 수 있다.
- **US-5** 개발자(보스)로서, **API 키 없이도** 테스트와 데모가 돌아가길 원한다.

## 기능 요구사항 (FR)
| ID | 요구사항 | 우선순위 | 수용 기준 | 상태 | 검증 (테스트) |
|---|---|---|---|---|---|
| FR-01 | 텍스트가 있는 PDF와 TXT 계약서를 읽는다 | Must | 기준 문서 3종을 파싱하고, 스캔 PDF는 명확한 오류를 낸다 | ✅ | `test_real_sources_split`, `test_parse_rejects_unknown_suffix`, `test_molit_layout_extraction_keeps_spaces` |
| FR-02 | "제n조(제목)" 단위로 조항을 나누고 ID·제목을 붙인다 | Must | 표준하도급 60조, 표준도급 43조, 하도급법 65조. `제 1 조`, `【】`, 괄호 없는 제목줄도 인식 | ✅ | `test_real_sources_split`, `test_split_accepts_header_variants`, `test_split_does_not_treat_references_as_headers` |
| FR-03 | 별첨·부칙·장래 시행 조문을 본문과 분리한다 | Should | 법령의 `[시행일: …]` 중복 조문, 고시의 별표가 따로 분류된다 | ✅ | `test_addendum_and_annex_sections`, `test_law_future_versions_are_separated`, `test_molit_contract_body_is_annex_after_addendum` |
| FR-04 | 계약서 조항마다 대응 표준 조항 top-k 를 찾는다 | Must | 합성셋 변형 조항 hit@3 ≥ 0.8 | ✅ (1.00) | `test_retrieval_hit_at_3_on_synthetic_set_is_reasonable` |
| FR-05 | 임베딩을 쓸 수 있으면 BM25와 합치고(하이브리드), 없으면 BM25만으로 동작한다 | Should | `EMBEDDING_PROVIDER=none` 에서 정상 동작 | 🟡 BM25만 검증. 하이브리드는 키가 없어 미실행 | `test_bm25_finds_standard_clause_for_rewritten_text` |
| FR-06 | 숫자 항목(기한·비율·배수)을 LLM 없이 규칙으로 판정한다 | Must | 기준값은 원문 인용과 함께 두고, 인용이 원문에 있는지 테스트로 확인 | ✅ (기준값 15개 중 규칙 사용 14개) | `test_rule_detects_longer_payment_deadline`, `test_threshold_quote_exists_in_source` |
| FR-07 | LLM 이 조항별로 카테고리·위험도·근거를 구조화 출력(JSON)으로 판정한다 | Must | 7개 카테고리 + other, high/medium/low | 🟡 FakeLLM 으로만 검증. **실제 LLM 미실행** | `test_fake_llm_reads_prompt_format_and_finds_diff`, `test_parse_variants` |
| FR-08 | LLM 근거 인용이 지목한 표준 조항 본문에 실제로 있는지 검증하고, 없으면 버린다 | Must | 지어낸 인용은 폐기, 문장부호만 다른 진짜 인용은 통과 | ✅ | `test_fabricated_evidence_is_dropped_but_real_quote_kept`, `test_judge_keeps_real_quote_with_different_middle_dot` |
| FR-09 | 같은 조항·카테고리를 규칙과 LLM 이 둘 다 지적하면 규칙 결과를 쓴다 | Should | 중복 제거 후 (조항, 카테고리)당 1건 | ✅ | `test_dedupe_prefers_rule_then_higher_risk` |
| FR-10 | 한국어 마크다운 + JSON 리포트를 위험도순으로 만든다 | Must | 근거 인용, 면책 고지, 처리 통계 포함 | ✅ | `test_report_sorted_by_risk_and_has_disclaimer`, `test_e2e_v2_with_fake_llm_on_synthetic_contract` |
| FR-11 | LLM provider 를 설정으로 바꾼다 (`fake`/`openai`/`anthropic`) | Must | 코드 수정 없이 환경변수로 전환 | 🟡 fake 만 실행 확인 | `test_settings_default_fake` |
| FR-12 | 시드 고정 합성 평가셋을 만든다 | Must | 계약서 3개, 라벨 20개 이상, 정상 조항 포함, 재실행 시 동일 | ✅ (라벨 24개) | `test_generation_is_deterministic`, `test_committed_cases_match_contracts` |
| FR-13 | baseline / v1 / v2 를 같은 평가셋에서 비교한다 | Must | Recall, Precision, Citation, hit@3, 시간, 토큰을 표로 저장 | 🟡 하네스 동작 ✅, **실제 LLM 숫자 ❌** | `test_run_eval_v2_and_baseline_produce_metrics` |
| FR-14 | PDF 업로드 → 리포트 웹 화면 | Should | `make run` 으로 실행, 리포트 다운로드 | ✅ (헬스체크 확인, 자동 테스트 없음) | 수동 확인 |
| FR-15 | Docker 이미지로 실행한다 | Could | `docker build` 성공, 컨테이너 안에서 파이프라인 실행 | ✅ (세션 프록시 CA 추가한 검증용 Dockerfile 기준) | 수동 확인 |
| FR-16 | 조항 수정안 자동 생성 | Won't | – | – | – |
| FR-17 | HWP 직접 업로드, OCR | Won't | – | – | – |

## 비기능 요구사항 (NFR)
| ID | 분류 | 요구사항 | 측정 기준 | 상태 |
|---|---|---|---|---|
| NFR-01 | 신뢰성 | **법령 수치와 조문을 기억으로 쓰지 않는다.** 모든 기준값은 원문 인용과 출처를 가진다 | `test_threshold_quote_exists_in_source` 통과. 원문에 없으면 `TODO(source-needed)` | ✅ (TODO 2건: 지체상금 요율, 하자담보 기간 상한) |
| NFR-02 | 법적 고지 | 모든 리포트에 "법률 자문이 아닌 검토 보조 도구" 고지를 넣는다 | 리포트 MD·JSON·UI 에 포함 | ✅ |
| NFR-03 | 테스트 용이성 | API 키 없이 `make test` 가 통과한다 | 키 없는 환경에서 68 passed | ✅ |
| NFR-04 | 재현성 | 평가 데이터와 결과가 재실행 시 같다 | 시드 고정, 해시 비교 테스트 | ✅ |
| NFR-05 | 보안 | API 키는 환경변수로만 읽고, 커밋·출력하지 않는다 | `.env` gitignore, 키 값을 다루는 코드 없음 | ✅ |
| NFR-06 | 데이터 윤리 | 공개 자료만 쓰고, 평가 데이터는 `synthetic` 표기 | 파일명, README | ✅ |
| NFR-07 | 평가 정직성 | 숫자를 좋게 보이려고 평가셋을 고치지 않는다. 나빠진 숫자도 기록한다 | 라벨 파일 변경 이력 | ✅ (v2 risk_match 0.45 < v1 0.59 그대로 기록) |
| NFR-08 | 장애 내성 | LLM 호출 하나가 실패해도 평가 전체가 멈추지 않는다 | 재시도 5회, 실패는 그 조항만 제외하고 집계 | ✅ `test_llm_error_is_isolated_per_clause` |
| NFR-09 | 성능 | 계약서당 처리 시간을 기록한다 | 평가 결과표 | 🟡 FakeLLM 0.5초. 실제 LLM 은 조항 50회 순차 호출이라 수 분 예상, 미측정 |
| NFR-10 | 비용 | 계약서당 토큰과 비용을 기록한다. 단가는 기억으로 쓰지 않는다 | `PRICE_IN_PER_1M` 등 환경변수가 있을 때만 비용 계산 | 🟡 실제 LLM 미측정 |
| NFR-11 | 의존성 | 허용 목록 밖 패키지는 승인 후 추가 | `pyproject.toml` | ✅ (pyhwp 는 1회 변환에만 쓰고 의존성에 넣지 않음) |

## 제약 조건
- **의존성:** `langgraph`, `langchain-core`, `langchain-openai`, `langchain-anthropic`, `chromadb`, `rank-bm25`, `pypdf`, `pydantic`, `streamlit`, `pytest`, `ruff`, `pyyaml`, `python-dotenv` (첫 프롬프트에서 고정)
- **데이터:** 공개 원문 3종(하도급법, 공정위 건설업종 표준하도급계약서, 국토부 민간건설공사 표준도급계약서). 실제 계약서 없음
- **환경:** 클라우드 세션은 정부 사이트 접속이 막혀 있다 → 원문은 보스가 직접 제공
- **시간:** 11/7 MVP, 11/15 서류 마감

## 요약: 아직 Must 인데 미완료인 것
| ID | 무엇이 막혔나 | 필요한 것 |
|---|---|---|
| FR-07, FR-11, FR-13 | 실제 LLM 으로 판정·비교한 숫자가 없다 | **API 키 1개** (`04_readiness.md` R-01) |
