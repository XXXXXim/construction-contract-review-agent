# PROGRESS

> 새 세션은 이 파일부터 읽고, 맨 아래 항목의 "다음 할 일"부터 이어서 작업한다.

## 2026-11-04 · M0 하네스 구성
**한 일**
- 하네스 파일 생성: `CLAUDE.md`, `docs/SPEC.md`, `docs/PLAN.md`, `PROGRESS.md`, `Makefile`, `.env.example`, `.gitignore`, `pyproject.toml`
- 패키지 골격 `src/contract_review/` + pydantic 스키마 초안 (`schemas.py`), 환경변수 설정 (`config.py`)
- 스모크 테스트 (`tests/test_smoke.py`): 스키마 검증, 설정 기본값(`fake`)

**결정한 것**
- 패키지는 `src/` 레이아웃, 설치는 `pip install -e ".[dev]"` (uv 없는 맥 환경도 고려)
- 기본 `LLM_PROVIDER=fake`, `EMBEDDING_PROVIDER=none` → 키 없이 `make test` 통과
- 평가 매칭 키: `(contract_id, clause_id, category)`, `risk_level=none`은 "지적 안 함"
- 규칙 판정이 같은 조항·카테고리의 LLM 판정보다 우선

**숫자**
- `make test`: 4 passed · `make lint`: 통과

**막힌 것 / 보고 사항**
- 세션에 GitHub 레포 미연결 → 로컬 git으로 커밋, 레포 연결 후 push 예정
- `data/raw/` 비어 있음 → M1 시작 전에 원문 3종 필요
- 환경변수에 API 키 없음 → M4 실제 LLM 1건 리포트 전까지 필요

**다음 할 일**
- 보스 SPEC 승인 → M1 (원문 확인 후 parse/split_clauses)

## 2026-11-04 · M1 파싱 + 조항 분할
**한 일**
- `data/raw/` 원문 3종 커밋 (보스 제공): 하도급법 PDF(법률 제21857호), 표준하도급계약서 HWP(2024-12-24) + `hwp5txt` 변환 txt, 국토부 표준도급계약서 고시 PDF(제2026-34호)
- `nodes/parse.py`: pypdf 추출, 띄어쓰기 소실 PDF 자동 layout 모드 재추출(실측 공백비율 0.16 vs 0.42, 임계 0.25), 머리글·쪽번호 제거
- `nodes/split_clauses.py`: "제n조(제목)" 분할, 별첨(조 번호 리셋)·부칙·장래시행 조문(`[시행일: …]`) section 분리, `body_clauses()`로 본문 선택
- `standards.py`: 기준 문서 로더 + 인용문 검증(`quote_in_clause`, 공백 무시 비교)
- `data/thresholds.yaml` + `thresholds.py`: 규칙 기준값 16개, 전부 원문 인용 보유 → `tests/test_thresholds.py`가 인용 존재를 검증
- `docs/SPEC.md` 5절 카테고리 표를 출처 달아 확정, `docs/raw_clauses.md` 조항표 생성

**숫자**
- 본문 조항 수: 하도급법 65 (+장래시행 7, 부칙 1) · 표준하도급계약서 60 (+별첨 4개 27조) · 표준도급계약서 43 (+고시 3)
- `make test`: 33 passed · `make lint`: 통과

**결정한 것**
- HWP는 프로젝트 의존성 없이 1회 변환한 txt를 커밋 (pyhwp는 스크래치 venv에서만 사용, pyproject 미추가)
- 숫자 기준값은 코드 상수 금지 → `data/thresholds.yaml` 단일 출처, 테스트로 인용 강제
- 지체상금 요율·하자담보 기간 상한은 원문에 숫자가 없어 `TODO(source-needed)` (value: null) → 규칙 판정에서 제외, LLM 판정만

**막힌 것 / 보고 사항**
- TODO(source-needed) 2건: 국가계약법 시행규칙 지체상금률, 건설산업기본법 시행령 하자담보책임기간 별표. 보스가 원문을 주면 규칙으로 승격 가능
- API 키 아직 없음 (M4 실제 LLM 1건 전까지 필요)

**다음 할 일**
- M2: `scripts/make_synthetic.py` (표준하도급계약서 본문 기반, 시드 고정, 계약서 3개 × 변형 7~10개, 정상 조항 포함) + `eval/cases/*.yaml`

## 2026-11-04 · M2 합성 평가셋
**한 일**
- `scripts/make_synthetic.py`: 변형 카탈로그 25종(7개 카테고리), 계약서 3개 × 변형 8개 = **라벨 24개**
- 검색이 조 번호만 보고 맞히지 못하게: 정상 조항 10개 삭제 후 재번호, "원사업자→갑 / 수급사업자→을" 치환
- 라벨에 `standard_clause_id`(정답 표준 조항) 포함 → citation accuracy, hit@3 계산용
- `tests/test_synthetic.py`: 시드 재현성(해시), 변형 패턴이 원문에 실존·적용 후 변화, 커밋된 라벨↔계약서 정합, 정상 조항 > 변형 조항

**숫자**
- 계약서당 조항 50개 (변형 8, 정상 42) · 라벨 카테고리 분포: payment 6, unfair 4, design 3, delay 3, termination 3, damages 3, defect 2
- `make test`: 36 passed · `make lint`: 통과

**결정한 것**
- 변형은 전부 결정적 문자열 치환(LLM 미사용) → 재현성 보장, 라벨 정확
- 조항당 변형 최대 1개 (평가 매칭 키가 조항+카테고리)

**다음 할 일**
- M3: 표준 조항 인덱스(BM25 + 선택적 임베딩) + `retrieve_standard` 노드 + hit@3 측정

## 2026-11-04 · M3 검색 + 검색 평가
**한 일**
- `retrieval.py`: BM25(어절 + 한글 2-gram, 당사자 명칭 중립화), 선택적 OpenAI 임베딩 + chromadb + RRF 하이브리드, 키 없으면 BM25 단독
- `nodes/retrieve_standard.py`, `eval_retrieval.py` (hit@1/3/5, 라벨 24개 + 전체 150조항, `--hard`는 제목 제거 질의)
- 합성셋 라벨 파일에 `clause_map`(전체 조항 → 표준 조항) 추가해 150개 질의로 측정

**숫자 (BM25 단독, 기준 문서 3종 168조항 인덱스)**
| 설정 | hit@1 | hit@3 | 질의당 시간 |
|---|---|---|---|
| 전체 150조항, 제목 포함 | 0.98 | **1.00** | 8 ms |
| 전체 150조항, 제목 제거(hard) | 0.96 | **1.00** | 5 ms |
| 라벨 24조항, 제목 포함 | 1.00 | 1.00 | – |
- 하이브리드(임베딩): **미측정** — OPENAI_API_KEY 없음

**솔직한 해석**
- hit@3=1.0은 합성 계약서가 표준 원문을 거의 그대로 복사해서 나온 값이다. 실제 계약서는 문장을 바꿔 쓰므로 이보다 낮을 것. 이 한계는 README에 그대로 적는다.
- 그래서 M5 비교에서 검색은 차별 요인이 되기 어렵고, 규칙 레이어와 근거 검증이 핵심 변수가 될 것으로 본다.

**다음 할 일**
- M4: `rule_check`, `llm_judge`(구조화 출력 + evidence_quote 검증), `report`, LangGraph 조립, `FakeLLM` E2E

## 2026-11-04 · M4 규칙 + LLM 판정 + 근거 검증, M5 평가 하네스(fake), M6 UI
**한 일**
- `nodes/rule_check.py`: thresholds.yaml 의 인용문에서 숫자 자리를 `(\d+)` 로 바꾼 패턴으로 계약서 숫자를 읽어 `worse_if` 방향 비교. 같은 문형이 여러 번 나오는 조항(손해의 3배/5배)은 표준에서의 등장 순서로 짝을 맞춤. 법령 출처면 high, 표준계약서 출처면 medium
- `llm.py`: `JudgeLLM` 프로토콜, `FakeLLM`(표준 top-1 과 문장 단위 diff, 결정적), openai/anthropic 은 langchain, 키는 환경변수만
- `nodes/llm_judge.py`: 프롬프트(카테고리 가이드, 규칙 결과, 계약 조항, 표준 top-3 태그) → JSON finding → **근거 검증**: standard_ref 가 준 후보 중 하나이고 evidence_quote 가 그 조항 본문에 공백 무시로 존재해야 통과, 아니면 폐기(dropped 집계)
- `nodes/report.py`, `graph.py`(LangGraph, baseline/v1/v2 경로 분기), `eval.py`(recall/precision/citation/hit@3/risk_match/시간/토큰, 비교표)
- `app/streamlit_app.py`, `Dockerfile`, `.dockerignore`
- 테스트 47개 통과: 날조 인용 폐기, 규칙 판정, fake E2E, baseline 그래프

**숫자 (fake 판정기, 실제 LLM 아님 — 하네스 동작 확인용)**
| config | recall | precision | citation | hit@3 | risk_match | 초/계약서 |
|---|---|---|---|---|---|---|
| baseline | 0.00 | – | – | – | – | 0.01 |
| v1 | 0.92 | 1.00 | 1.00 | 1.00 | 0.59 | 0.41 |
| v2 | 0.92 | 1.00 | 1.00 | 1.00 | 0.45 | 0.42 |
- fake 가 놓친 2건은 "문장 추가형" 변형(산안비 전액 부담 추가, 배상 상한 5% 추가) — 문장 삭제·치환만 보는 diff 의 한계. baseline 0 은 fake 가 전체 문서 프롬프트를 처리하지 못해서이며 의미 없는 값
- v2 risk_match 가 v1 보다 낮은 이유: 규칙 레이어가 법령 출처 위반을 high 로 올리는데 라벨 일부(예: 조정 기한 30→90일)는 medium 으로 적혀 있음. 라벨은 고치지 않고 그대로 둠 (규칙 9)
- 규칙 레이어 단독 적중: 계약서당 평균 4건 (숫자형 변형 12개 중 12개)

**막힌 것 / 보고 사항**
- **실제 LLM 측정 불가: OPENAI_API_KEY / ANTHROPIC_API_KEY 없음.** 키가 오면 `make eval-baseline && make eval CONFIG=v1 && make eval` 3번 + `--compare` 로 진짜 비교표가 나온다
- `docker build` 미검증 (세션에 docker 데몬 없음)
- 비용(USD)은 단가를 기억으로 쓰지 않기 위해 `PRICE_IN_PER_1M`/`PRICE_OUT_PER_1M` 환경변수가 있을 때만 계산

**다음 할 일**
- M7 README 케이스 스터디 → 키 확보 후 실제 LLM 평가 → README 숫자 교체 → 최종 보고

## 2026-11-04 · 결함 분석 후 수정 (fix)
**찾은 결함과 수정**
| # | 결함 | 수정 | 테스트 |
|---|---|---|---|
| 1 | 조항 머리가 `제1조(목적)` 형식만 인식 → `제 1 조 (목적)`, `제1조【목적】`, `제1조 목적` 이면 조항 0개 | 공백·【】·[]·전각 괄호 허용, 괄호 없는 제목줄은 한글 제목만 있고 조사·접속어로 시작하지 않을 때만 인정 | `test_split_accepts_header_variants` 외 |
| 2 | 근거 검증이 문장부호 차이(원문 ㆍ U+318D vs LLM · U+00B7)로 **진짜 인용을 버림** → v2 recall 과소평가 | `textnorm.canon`: 문장부호 통일 + NFKC. **NFKC 가 ㆍ를 ᆞ(U+119E)로 바꾸는 문제를 테스트가 잡아** 정규화 전후 모두 매핑. "…" 생략 인용은 조각별 검증 | `test_quote_match_ignores_punctuation_variants` |
| 5 | baseline 출력이 max_tokens(4096)에 잘리면 JSON 파싱 실패 → recall 0 | max_tokens 16000(LLM_MAX_TOKENS), 잘린 배열에서 완성된 객체만 복구, 잘림 횟수 집계 | `test_parse_recovers_truncated_array` |
| 6 | API 오류 1번에 평가 전체 중단 | max_retries=5(지수 백오프), 실패 호출은 그 조항만 제외하고 `llm_errors` 집계, 선택적 디스크 캐시(LLM_CACHE=1) | `test_llm_error_is_isolated_per_clause`, `test_cached_llm_reuses_response` |
| 7 | 응답이 `{"findings":[…]}`/코드펜스/설명문 섞이면 0건 | 파서가 코드펜스·객체 감싸기·앞뒤 설명문 처리, 못 읽으면 `unparsed_responses` 집계 | `test_parse_variants` |
| 8 | 같은 조항·카테고리 중복 finding 이 precision 부풀림 | 파이프라인에서 (조항, 카테고리) dedupe(규칙 > 높은 위험도), 평가도 고유 키로 계산 | `test_dedupe_prefers_rule_then_higher_risk`, `test_precision_counts_unique_clause_category` |
| + | **평가 하네스(`eval.py`)에 테스트가 없어** 수정 중 KeyError 로 깨진 걸 pytest 가 못 잡음 | `tests/test_eval.py` 추가 (v2·baseline 끝까지 실행) | – |
| 3 | docker build 미검증 | 세션에서 dockerd 기동해 빌드. 처음엔 pip 가 **세션 프록시 CA** 를 못 믿어 실패(Dockerfile 문제 아님) → 프록시 CA만 추가한 검증용 Dockerfile 로 빌드 성공, 컨테이너 안 v2 실행·UI 헬스체크 ok | – |

**숫자**
- `make test`: **68 passed** (47 → 68) · `make lint`: 통과
- fake 비교표는 변화 없음 (baseline 0.00 / v1 0.92 / v2 0.92 recall). 이번 결함들은 실제 LLM 출력·실제 계약서에서만 드러나는 종류라 fake 로는 수치가 안 움직이는 게 정상

**남은 것**
- 실제 LLM 측정 (API 키 필요) — 4·10번(실제 hit@3, 실제 오탐)은 키 + 실제 계약서 샘플이 있어야 검증 가능
- 미착수: 정상 조항 LLM 호출 생략(비용 절감). 합성셋에선 "원문 복사 조항 건너뛰기"가 수치를 부풀릴 수 있어 보류

**다음 할 일**
- API 키 확보 → `LLM_CACHE=1 make eval-baseline && make eval CONFIG=v1 && make eval` → `--compare` → README 숫자 교체

## 2026-11-08 · P0~P3 문서 사후 작성
**한 일**
- 개발 프로세스(P0~P7)를 정하고, 건너뛴 앞 단계를 거꾸로 채움: `docs/01_brief.md`, `02_requirements.md`, `03_design.md`, `04_readiness.md`
- 요구사항에 ID 부여: FR 17개(Won't 2개 포함), NFR 11개, 각각 상태와 검증 테스트 연결
- ADR 11개 (오케스트레이션, 분할, 검색, 벡터 저장소, 숫자 판정, 환각 대응, provider, 평가 데이터, HWP, UI, 스키마): 후보 비교, 선택 이유, 트레이드오프
- 준비물 12개를 이 세션에서 명령으로 직접 확인 (API 키 ❌, API 호스트 도달 ✅, 정부 사이트 ❌, docker 데몬 재시작으로 꺼짐)
- CLAUDE.md 에 문서 순서와 규칙 추가

**숫자**
- Must 요구사항 중 미완료: FR-07, FR-11, FR-13 (전부 API 키 하나가 원인)

**다음 할 일**
- R-01 API 키 확보 → 실제 LLM baseline/v1/v2 평가 → 02 상태 갱신 → 05_traceability.md(P6), 06_retro.md(P7)
