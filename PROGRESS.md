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

## 2026-11-08 · 실제 LLM 평가 준비 (Anthropic, 보스 맥에서 실행)
**상황**
- Anthropic 키는 클라우드 세션의 보안 입력 폼으로 저장할 수 없음 (api.anthropic.com 은 시스템 예약 호스트, 키 없이 호출하면 401 확인) → 보스 맥에서 실행하기로 결정

**한 일**
- 가짜 키로 Anthropic 경로 드라이런 → **`claude-sonnet-5-5` 가 temperature 지정을 거부하는 버그 발견** (그대로 돌렸으면 150회 호출 전부 실패). temperature 제거, timeout 600초. 회귀 테스트 `test_anthropic_client_does_not_set_temperature`
- 조항별 LLM 호출 병렬화 (`LLM_CONCURRENCY`, 기본 4; fake 는 1). 결과 순서 유지, 카운터·캐시 쓰기 스레드 안전 처리
- `scripts/run_real_eval.sh`: 연결 확인 1회 → baseline/v1/v2 → 비교표 → 샘플 리포트 1건 (fake 로 끝까지 실행 확인)
- 비교표가 날짜별 중복 행을 내던 문제 수정: (LLM, config) 별 최신 결과만

**숫자**
- `make test`: 69 passed

**다음 할 일**
- 보스 맥에서 `scripts/run_real_eval.sh` 실행 → 결과 push → README·02_requirements 상태 갱신 → 05_traceability, 06_retro

## 2026-11-08 · M5 실제 LLM 평가 결과 (claude-sonnet-5-5, 보스 맥에서 실행)
**숫자**
| config | Recall | Precision | Citation | Risk match | 입력 토큰/계약서 | 출력 토큰/계약서 |
|---|---|---|---|---|---|---|
| baseline | 0.92 (22/24) | 0.81 (22/27) | 0.00 | 0.82 | 42,887 | 8,311 |
| v1 | 0.96 (23/24) | 0.85 (23/27) | 1.00 | 0.57 | 251,952 | 14,341 |
| v2 | 1.00 (24/24) | 0.89 (24/27) | 1.00 | 0.62 | 252,158 | 12,826 |
- LLM 호출 실패 0, JSON 파싱 실패 0, 잘림 0, 근거 검증 폐기 0 (세 config 모두)

**분석**
- v1 → v2 개선은 전부 규칙 레이어: `dc_pay_15_to_60`(contract_03 제28조)을 v1은 payment_deadline 으로 오분류(누락 1 + 오탐 1), v2는 규칙이 design_change 로 잡음
- 근거 검증은 이번 데이터에서 효과 0 (Sonnet 인용이 전부 실존). "환각 차단" 효과는 측정되지 않았다고 기록
- v1·v2 남은 오탐 제11조/design_change ×3 = **평가셋 생성기 버그**: 재번호 시 본문 조문 참조를 안 고침 → 제11조가 "제11조에 따른 서면"으로 자기 참조. 계약서 내 조문 참조 114개 중 최대 89개가 어긋남(법률 조문 참조 포함 상한값). LLM 은 실제 결함을 지적한 것
- baseline citation 0.00: 원인 미확인. 결과 JSON 에 finding 원문이 없었음 → `findings_detail` 저장 추가 (재실행 필요, 캐시로 비용 0)
- 처리 시간: LLM_CACHE=1 로 돌려 v1(32/150)·v2(141/150) 캐시 적중 → 시간 비교 무효. baseline 53초만 유효
- risk_match 는 baseline 이 최고 (0.82)

**결정이 필요한 것 (보스)**
- 생성기 버그 수정판(평가셋 v2)을 만들지. CLAUDE.md 규칙 9에 따라 현재판 결과는 그대로 두고, 수정판을 **별도 버전**으로 나란히 기록하는 방식 제안

**다음 할 일**
- 보스 맥에서 `git pull && LLM_PROVIDER=anthropic bash scripts/run_real_eval.sh` 재실행 (캐시 적중으로 비용 ≈ 0) → findings_detail 확보 → baseline citation 원인 확인
- 캐시 끄고 시간 재측정 (`LLM_CACHE=0`, v1·v2 비용 다시 발생)
- 05_traceability.md, 06_retro.md

## 2026-11-08 · 평가셋 set-v2 (생성기 조문 참조 버그 수정판)
**보스 결정:** set-v1 은 그대로 두고, 버그만 고친 평가셋을 별도 버전으로 만들어 나란히 기록

**한 일**
- `scripts/make_synthetic.py --dataset v2` → `data/synthetic_v2/`, `eval/cases_v2/`
  - 같은 시드·같은 변형 추첨·같은 삭제 추첨. 다른 점 두 가지만:
    1) 본문 속 계약서 내부 조문 참조를 새 번호로 치환 (법령 참조 「…법」 제n조 는 그대로)
    2) 남은 조항이 참조하는 조항은 삭제 취소 (계약서 02·03 → 조항 52개)
  - 조사 어색함(갑가, 을는)은 일부러 그대로 둠 (한 번에 한 가지 변경)
- set-v1 재생성이 기존 파일과 바이트 단위로 동일함 확인 (v1 결과 재현성 유지)
- `eval.py --dataset v1|v2`, 결과에 `dataset: set-v1|set-v2`, 비교표에 평가셋 열. `run_real_eval.sh` 에 `DATASET` 환경변수
- 테스트 73개: set-v2 내부 참조 어긋남 0, set-v1 은 버그 유지, 두 평가셋 변형 동일

**숫자**
- 내부 조문 참조 (변형으로 문장이 바뀐 조항 제외): set-v1 58개 중 54개 어긋남 + 삭제 조항 참조 4개 → set-v2 59개 중 0개
- **정정:** 앞 기록의 "114개 중 최대 89개"는 법령 조문 참조까지 센 과대 추정이었다. 위 숫자가 정확한 값
- 검색 hit@3: set-v1 1.00 (150 질의), set-v2 1.00 (154 질의)
- FakeLLM 은 set-v2 에서 precision 0.74 로 하락: 글자 diff 라 재번호된 참조("제11조"→"제10조")를 차이로 봄. 실제 LLM 이 이걸 정상으로 이해하는지가 set-v2 의 확인 포인트
- 실제 LLM 예상 비용: 구성 v1·v2 각각 새 호출 약 67/154 (나머지는 캐시) + baseline 3회

**다음 할 일**
- 보스 맥: `git pull && DATASET=v2 LLM_PROVIDER=anthropic bash scripts/run_real_eval.sh` → push
- 같은 실행에서 findings_detail 확보를 위해 set-v1 도 재실행 (캐시로 비용 ≈ 0): `LLM_PROVIDER=anthropic bash scripts/run_real_eval.sh`

## 2026-11-08 · M5 set-v2 결과 + baseline 인용 분석
**숫자 (claude-sonnet-5-5)**
| 평가셋 | config | Recall | Precision | Citation | Risk match |
|---|---|---|---|---|---|
| set-v2 | baseline | 0.92 | 0.81 | 0.00 | 0.73 |
| set-v2 | v1 | 0.92 | 0.92 | 1.00 | 0.59 |
| set-v2 | v2 | **1.00** | **1.00** | 1.00 | 0.62 |
| set-v1 | baseline / v1 / v2 | 0.92 / 0.96 / 1.00 | 0.81 / 0.85 / 0.89 | 0.00 / 1.00 / 1.00 | 0.82 / 0.57 / 0.62 |
- 실패 0, 파싱 실패 0, 잘림 0, 근거 검증 폐기 0 (전 구성)

**분석**
- 생성기 버그 가설 확인: set-v1 의 v1·v2 오탐(제11조 자기 참조) 3건이 set-v2 에서 0건
- set-v2 v1 → v2: `dc_pay_15_to_60` 을 v1 이 계약서 02·03 에서 payment_deadline 으로 분류(누락 2 + 오탐 2). set-v1 계약서 02 에서는 같은 변형을 design_change 로 맞혔음 → LLM 분류가 문맥에 따라 흔들림. 규칙 레이어가 일관되게 해결
- baseline citation 0.00 원인: 표준 원문을 못 받아 **계약서 자기 조항 번호를 "표준하도급계약서 제n조"로 적거나 번호 없이 서술**
- baseline 의 하도급법 인용(설명 포함 21건) 중 5건이 원문과 불일치 (`data/raw` 대조, 위 명령으로 확인):
  1. 제13조 제6항 "발주자로부터 대금 수령 후 15일 이내 지급" → 원문은 제13조③ (⑥은 어음 할인료)
  2·3. 제13조 제6항 "증액대금 수령 후 15일 이내 지급" ×2 → 원문 15일 기준은 제16조④ (⑥은 어음 할인료)
  4. 제12조의3 "부당한 감액 금지" → 원문 제12조의3 은 "기술자료 제공 요구 금지 등" (감액금지는 제11조)
  5. 제16조 제1항 "증액받은 날부터 30일 이내 조정" → 원문은 제16조③
  - 애매해서 오류로 세지 않음: 제4조 "결정·감액 금지" (원문 제목은 "부당한 하도급대금의 결정 금지")

**하네스 수정**
- 같은 날 재실행이 결과 파일을 덮어쓰던 문제: set-v1 재실행이 첫 실행 처리 시간(baseline 53초 등)을 캐시 값으로 덮어씀. 지표 값은 동일, 첫 실행 원본은 커밋 `79af582`. → 파일이 있으면 시각 접미사, `run_at`·`timing_valid` 기록, 비교표에서 캐시 오염 시간에 `*`
- 테스트 74개

**알게 된 작은 문제 (미수정)**
- 하도급법 PDF 페이지 머리글 "하도급거래 공정화에 관한 법률" 줄이 조항 본문 중간에 섞여 있음 (parse 의 머리글 제거가 법제처 줄만 처리). 인용 검증에는 영향 없음

**다음 할 일**
- (선택) 캐시 끄고 v1·v2 처리 시간 측정: `LLM_CACHE=0 DATASET=v2 LLM_PROVIDER=anthropic bash scripts/run_real_eval.sh` (v1·v2 호출 비용 다시 발생)
- 05_traceability.md (P6), 06_retro.md (P7), 자소서·면접 정리

## 2026-11-08 · M7 마무리
**한 일**
- `docs/05_traceability.md` (P6): FR 17개·NFR 11개 → 설계 → 구현 파일 → 테스트 → 결과. 미충족 3건(FR-05 하이브리드, NFR-09 시간, NFR-10 비용)과 해결 방법
- `docs/06_retro.md` (P7): KPT. 핵심 교훈 "측정할 준비가 끝나기 전에는 만들지 않는다"
- `docs/07_final_report.md`: 지표 비교표(set-v2/set-v1), 가장 효과 컸던 개선(규칙 레이어), 한계 3, 자소서 3줄, 면접 질문 5
- README 문서 안내 섹션, CLAUDE.md 폴더 구조(set-v2, 05~07) 갱신, 02 요구사항의 오래된 숫자 정정

**숫자**
- `make test`: 74 passed · `make lint`: 통과

**남은 선택 과제**
- 캐시 끄고 처리 시간 측정 (NFR-09), 토큰 단가로 비용 계산 (NFR-10), 실제 공개 계약서로 일반화 평가, 어려운 변형(문장 재작성) 추가

## 2026-11-08 · 공개 사례 평가셋 (set-public) 구축 — 실제 LLM 실행 전
**보스 결정:** 공정위 의결서 3건 제공, "알아서 처리" → B 승인으로 진행. CLAUDE.md 규칙 2에 (b) 공정위 공개 의결서 실제 문구 허용 추가, 02 요구사항 FR-18 추가

**한 일**
- 의결서 원문: 유강종합건설 의결(약) 2025-080, 지원건설 의결 2025-143, 대방건설 의결 2026-085 → `data/raw/public_cases/`
- 실제 문구 5개 (`data/public_cases/cases.yaml`): 텍스트층 2건은 테스트로 원문 존재 확인, 이미지 3건은 화면 보고 전사(`transcribed_from_image`) + 본문 대응 구절 존재 확인
- 시험 문서 5개: 표준 60조 그대로 + 실제 문구를 제61조로. 특수조건이 "제9조"로 시작하는 1건은 번호만 제61조로 변경
- 채점: 탐지율(신규), acceptable_categories 로 카테고리 판정, 정답 표준 조항 없는 라벨은 citation·hit@3 제외. **합성셋 점수 불변 확인**(fake set-v1 v2: recall 0.92, precision 1.00)
- 테스트 78개

**실행 전 관찰 (결과 보기 전 기록)**
- 규칙 레이어 적중 0/5 (숫자형 아님) → v2 ≈ v1 예상
- 검색이 "특약사항" 제목 때문에 국토부 제42조(특약사항)를 1등으로 붙이는 경우 있음 (case 1·2), case 1 은 표준 대금 지급 조항(제40조)이 top-3 에 없음. **튜닝하지 않고 그대로 실행**
- FakeLLM: 탐지 1/5 (글자 diff 라 의미 없음)

**다음 할 일**
- 보스 맥: `git pull && DATASET=public LLM_PROVIDER=anthropic bash scripts/run_real_eval.sh` → push

## 2026-11-08 · set-public 실제 LLM 결과 (claude-sonnet-5-5)
**숫자**
| config | 탐지 | 카테고리 일치 | 오탐 | 위험도 high | 입력 토큰/문서 |
|---|---|---|---|---|---|
| baseline | 5/5 | 5/5 | 0 | 5/5 | 51,750 |
| v1 | 5/5 | 5/5 | 0 | 2/5 | 313,498 |
| v2 | 5/5 | 5/5 | 0 | 2/5 | 313,498 |
- 실패·파싱 실패·잘림·근거 폐기 모두 0. v2 는 캐시 305/305 (v1 과 프롬프트 동일 — 규칙 적중 0, 실행 전 예상대로)

**분석 (원문 대조로 확인)**
- 탐지는 세 구성 동일 → 실제 노골적 특약에서는 파이프라인의 탐지 우위 없음
- baseline: "하도급법 제15조(감액금지)" 인용 → 원문 제15조는 "관세 등 환급액의 지급" (감액금지는 제11조)
- v1·v2 case 1: 근거로 표준 "제11조(추가·변경공사에 대한 서면 발급 등)" → 실행 전 기록한 검색 약점이 실제로 발생. 인용문은 실존해 근거 검증 통과 → 관련성 미검증 한계 확인
- 설명문 속 "하자보수보증금률 상한 통상 3%"(v1·v2), "통상 2%"(baseline): data/raw 에 없는 숫자, 확인 불가
- 위험도 high 판정은 baseline 5/5 > v1·v2 2/5

**다음 할 일 (선택)**
- 검색 개선(제목 가중치 축소, 본문 키워드) → set-public 이 아닌 **새 문구**로 검증
- 설명문 속 조문 번호·숫자 검증 단계

## 2026-11-08 · FR-19 조문 인용 검증
**한 일**
- `citation_check.py`: 근거·설명문 속 "하도급법/표준하도급계약서/표준도급계약서 제N조 제M항(설명)"을 원문과 대조
  - 조·항 존재, 괄호 속 숫자가 그 조·항에 있는가, 괄호 설명이 그 조와 맞는가(IDF 가중 제목 비교: 다른 조 제목과 더 맞으면 번호 오류), 출처 없는 숫자(경고), 범위 밖 법령(민법·건산법·시행령 등)은 판정 안 함
  - 기준값은 실제 출력에서 찾은 오류 8종·정상 인용 10종으로 정함 (테스트에 고정)
- 파이프라인: v2 에서 LLM finding 에 `citation_issues` 주석, 리포트에 ⚠️ 표시 (판정 불변). 규칙 판정은 검사 제외
- 평가: 세 구성 모두 같은 검사기로 `citation_errors` 채점, 비교표 열 추가. `scripts/audit_citations.py` → `docs/citation_audit.md`
- 테스트 102개

**숫자 (저장된 실제 LLM 결과 재채점, API 비용 0)**
- 인용 오류: set-v1 baseline 15 / v1 0 / v2 0 · set-v2 baseline 24 / 0 / 0 · set-public baseline 1 / 0 / 0
- baseline 오류 40건 = 하도급법 조문 오류 7건(원문 대조로 전부 확인, 없는 "제40조" 포함) + 합성 계약서 재번호 번호 혼동 33건

**과정에서 잡은 것**
- 같은 테스트 2회 실패(제12조의3): 흔한 단어("부당한", "금지")가 점수를 동점으로 만듦 → IDF 가중치로 해결. 3회째 전에 스크립트로 전 사례 점수 확인 후 실행
- 항이 하나뿐인 조를 "제1항"으로 인용하면 "없는 항"으로 잡던 거짓 경보 수정
- 통합 확인 중 거짓 경보: Finding.contract_text 가 400자 발췌라 "90일"이 출처 없는 숫자로 잡힘, 규칙 판정에도 경고 → 조항 전문 사용 + 규칙 판정 제외 (회귀 테스트 추가)

**한계**
- 검사기 기준을 같은 결과에서 정함 (독립 검증 아님). 관련성(번호만 맞고 무관한 인용) 미검증. 계산된 숫자(80일, 4배)가 경고에 걸림
- 결과 파일의 설명문은 앞 300자만 저장돼 재채점은 과소 집계 (새 실행부터는 평가 단계에서 전문으로 채점)

## 2026-11-10 · 공개 준비 [1] 현대건설 문서 제거
- `data/raw/reference/hdec_subcontract_act_guideline_2024.pdf` 삭제 (기업 내부 교육 자료 성격이라 공개 레포에서 제외), `data/raw/README.md` 언급 삭제
- 참조 확인: `grep` 결과 코드·테스트·스크립트·설정 어디에서도 참조 없음. 기준값·평가에 쓰인 적 없음
- **주의: 파일은 과거 커밋 `0ca1ed4` 에 남아 있다.** 히스토리에서 지울지는 보스 결정 대기 (force push 필요)

## 2026-11-10 · 공개 준비 [2] AI 협업 고지
- README 상단에 "Claude Code와 협업해 개발" 고지 추가
- 작성자 역할 근거: PROGRESS·docs 의 "보스 결정/보스 제공" 기록 (원문 제공, 의결서 제공·승인, set-v1 유지·set-v2 결정, SPEC 승인, 실제 LLM 평가 실행)
  + 기록에는 없지만 **보스가 2026-11-10 사실로 확인한 항목**: 초기 기획(목표·절대 규칙·마일스톤) 작성, 개발 프로세스(P0~P7) 정형화 요청, 검증 범위(결함 분석·실제 사례 평가·조문 번호 검증) 요청
- 보스 승인 초안에서 한 곳만 정확성 수정: "생성기 버그 발견 후" → "버그가 확인된 뒤" (버그 확인은 분석 과정에서 이뤄짐)

## 2026-11-10 · 공개 준비 [3] README 첫 화면 요약
- 맨 위 18줄(빈 줄 제외 14줄): 한 줄 문제 정의, 결과표(baseline/v1/v2 × Recall·Precision·근거 조항 정확도·조문 인용 오류·입력 토큰), 핵심 메시지(근거 정확성 40→0, set-public 에서 baseline 도 5/5), 한계 한 줄, 실행 명령 3줄
- 숫자 출처: `eval/results/2026-11-08_*_anthropic-claude-sonnet-5-5_set-v2.json` (Recall·Precision·정확도·토큰), 조문 인용 오류는 `scripts/audit_citations.py` 로 세 평가셋 결과를 재채점한 합계 (set-v1 15 + set-v2 24 + set-public 1)
- 기존 내용은 삭제 없이 "# 상세" 아래로 이동. 스크린샷 자리: `docs/images/streamlit_report.png` (README 에 주석 처리된 이미지 줄)

## 2026-11-10 · 공개 준비 [4] 회사 과제와의 연결 문단
- README "왜 이 문제를 골랐나": 2026-11-02 공개 발표된 '1인 1 AI 에이전트' 체계, 보도된 과제 '대외 공문 및 계약 검토'를 공개 자료만으로 재현
- 보도 기사 링크 2곳은 `TODO(링크)` — 보스가 제공 예정
- 기대효과는 측정값만: 조항 자동 대조(표준 168개 조항 인덱스, set-v2 hit@3 1.00), 조문 인용 오류 0건(baseline 40건), 숫자 규칙으로 v1 누락 2건 탐지. 시간 절감 수치는 쓰지 않음
- 사내 정보·특강 수치(에이전트 수, 검토 시간 등)는 README 에 넣지 않음

## 2026-11-10 · 공개 준비 [5] 샘플 리포트 교체 — 보류
- set-v2 v2 리포트를 캐시로 재생성하려 했으나 LLM 응답 캐시(`.cache/llm/`, gitignore)는 보스 맥에만 있고 이 세션에는 없음 → API 호출 없이는 불가해 **멈춤**
- 프롬프트 생성 코드는 11/08 평가 이후 바뀌지 않아 보스 맥에서 실행하면 전부 캐시 적중(비용 0) 예상. 명령은 보스에게 전달

## 2026-11-10 · 공개 준비 [6] 오래된 문구 수정
**고친 것 (실제 값 기준)**
| 위치 | 이전 | 수정 | 실제 값 근거 |
|---|---|---|---|
| README "핵심 설계 결정" | `make test` 47개 | 102개 | `pytest --collect-only` 102 |
| 02_requirements NFR-03, 05_traceability (2곳) | 74 passed | 102 passed | 같음 |
| 06_retro 머리말 | 테스트 74개 | 74개(회고 작성 시점) + 현재 102개 병기 | 회고 커밋 836d8cf 당시 74 |
| 03_design 테스트 계획, 05_traceability NFR-01 | 기준값 15개 | 18개 항목(값 16 + TODO 2, 규칙 사용 14) | `load_thresholds()` 18, `rule_thresholds()` 14 |
| 02_requirements FR-06 | 기준값 15개 중 규칙 사용 14개 | 항목 18개(값 16, TODO 2) / 규칙 사용 14개 | 같음 |
| README 레포 구조 | M4 시점 구조 | citation_check.py, textnorm.py, eval_retrieval.py, synthetic_v2, public_cases, cases_v2, cases_public, 새 스크립트 반영 | `git ls-files` |

**점검했지만 그대로 둔 것**
- 토큰 수: README·docs 의 모든 "NN,NNN" 토큰 수가 `eval/results/` 저장값과 일치 (스크립트 대조)
- PLAN M1 "33 passed", PROGRESS 날짜별 숫자: 그 시점 기록이라 유지
- 06_retro "커밋 15개": 회고 커밋 직전 기준으로 맞음 (회고 커밋 포함 16)
- SPEC 7절 "변형 7~10개, 라벨 20개 이상": 목표 사양이고 실제(8개·24개)와 모순 아님

## 2026-11-10 · 공개 준비 [7] 설치 안정화 + CI
- `pyproject.toml`: 버전 범위 지정 (하한 = 테스트한 버전, 상한 = 다음 메이저 전, ruff 마이너 고정). chromadb·langchain-openai → 선택 설치 `[embedding]`
- 선택 설치가 없으면: 임베딩은 BM25 단독으로 자동 전환, `LLM_PROVIDER=openai` 는 설치 방법을 알려주는 오류. 회귀 테스트 추가 → **테스트 103개**
- 새 환경 측정 (레포 새 복제 + pip 캐시 끔, Python 3.13): `make setup` 88초 + `make test` 39초 = **127초**, 103 passed, 선택 패키지 미설치 확인
- `.github/workflows/test.yml`: push·PR 에서 Python 3.11·3.13 으로 `make setup` → `make test` → `make lint`. README 배지 추가
- Docker: 첫 빌드 시도에서 Docker Hub 429(익명 pull 횟수 제한)로 베이스 이미지 다운로드 실패 → 1분 간격 재시도 (결과는 아래 기록)

## 2026-11-10 · 공개 준비 [8] LICENSE
- 루트 `LICENSE` (MIT, 저작권자: 심혁 — 초기 기획 문서에 보스가 밝힌 이름)
- `data/raw/README.md`: MIT 는 코드·작성 문서에만 적용, 공개 원문(법령·고시·표준계약서·의결서)은 각 기관 자료로 대상 아님. README 9절 라이선스 추가

## 2026-11-10 · [7] 확인 결과 (CI·Docker)
- GitHub Actions 첫 실행: Python 3.11·3.13 모두 성공 (setup → test 103 → lint). https://github.com/XXXXXim/construction-contract-review-agent/actions/runs/42810913834
- Docker: Docker Hub 429 로 2회 실패 후 3회째 빌드 성공 (120초). 세션 프록시 CA 2줄만 더한 검증용 Dockerfile 사용 (원본 Dockerfile 은 그대로).
  컨테이너: Python 3.11.18, 선택 패키지 0개, set-v2 contract_01 v2 실행 성공(fake, 조항 50), Streamlit 헬스체크 ok

**다음 할 일 (보스)**
- [5] 맥에서 캐시로 set-v2 샘플 리포트 재생성 → push
- README 스크린샷 `docs/images/streamlit_report.png`, 보도 기사 링크 2개
- 과거 커밋 `0ca1ed4` 의 현대건설 PDF 를 히스토리에서도 지울지 결정 (force push 필요)
- (선택) `LLM_CACHE=0` 으로 set-v2 처리 시간 측정 → push 하면 README 의 "처리 시간 비교 불가"를 실측값으로 교체

- 정정: [6] 에서 문서 테스트 수를 102 로 맞췄으나 [7] 에서 회귀 테스트 1개를 추가해 103 이 됨 → README·02·05·06 을 103 으로 다시 맞춤

## 2026-11-10 · [5] 샘플 리포트 완료 + 처리 시간 실측 (보스 맥에서 실행)
**[5] 샘플 리포트** (커밋 13c21ef, 보스 실행): set-v2 contract_01 v2, 처리 0.18초 = 전부 캐시 적중(비용 0). 지적 8건(규칙 4 + LLM 4), 인용 경고 0

**처리 시간** (커밋 2debdb8, 보스 실행, `LLM_CACHE=0`, 캐시 적중 0, `timing_valid: true`, 조항 호출 4개 동시)
| config | 초/계약서 |
|---|---|
| baseline | 44.85 |
| v1 | 44.19 |
| v2 | 40.37 |
→ README "처리 시간 비교 불가" 문단, 02 NFR-09, 05 추적표를 실측값으로 교체

**재실행 정확도 편차 (덮어쓰지 않음, 첫 화면 표는 11/08 유지)**
| config | 11/08 R / P | 11/10 R / P | 조문 인용 오류 11/08 → 11/10 |
|---|---|---|---|
| baseline | 0.92 / 0.81 | 0.96 / 0.85 | 24 → 23 |
| v1 | 0.92 / 0.92 | 1.00 / 0.92 | 0 → 0 |
| v2 | 1.00 / 1.00 | 1.00 / 0.92 | 0 → 0 |
- v1: 11/08 에 놓친 dc_pay_15_to_60 2건을 이번엔 design_change 로 맞힘 (LLM 분류가 실행마다 흔들린다는 기존 관찰과 같음)
- v2 오탐 2건(위험도 low): 표준 그대로인 제33조(부당한 하도급대금의 결정금지)를 "하도급법 제4조 ②6·7호가 빠졌다"고 지적
  → 원문 대조: **HWP 변환(hwp5txt)이 표 안의 제33조 ② 제6호를 `<표>` 로만 남겨 내용이 빠진 것.** 표준계약서 결함이 아니라 우리 데이터 변환 손실. 본문 안 표는 2개(제33조, 제59조)
  → 평가셋·원문을 바꾸지 않기 위해 수정 보류, README 한계와 data/raw/README 에 기록
- 주의: `scripts/audit_citations.py` 는 최신 결과를 쓰므로 지금 다시 돌리면 set-v2 가 11/10 결과로 바뀐다 (README 의 40건은 11/08 결과 기준). 재생성하지 않음

## 2026-11-10 · README 에 1차·2차 실행 나란히 (보스 결정)
- 첫 화면 표: Recall·Precision·근거 조항 정확도를 "1차 · 2차"로 병기. 조문 인용 오류(40/0/0)와 입력 토큰은 1차 기준 (입력 토큰은 두 실행 동일)
- 상세 결과표에 set-v2 2차 행 3개 추가 (`eval/results/2026-11-10_*_set-v2.json` 값 그대로)
- **1차에서만 맞는 주장을 정정:** "v1 → v2 개선은 전부 규칙 레이어" → 2차에서는 v1 도 맞혀 차이 0. 규칙의 가치는 "평균 상승"보다 "실행마다 같은 답"으로 서술 (README, 07 최종 보고 2절·자소서 3줄, 06 회고)
- 한계: "1회 실행" → "set-v2 2회 실행, Recall·Precision 최대 0.08 차이 (v1 Recall 0.917 → 1.000)"

## 2026-11-14 · Orca 병렬 작업 인수인계 준비 (새 기능 없음)
**[1] 현재 상태 얼리기**
- 작업 트리 깨끗함, `origin/main` 과 동일(3496a64) 확인
- 태그 `v1.0-application` (주석 태그, 3496a64) 을 로컬에 만들었으나 **push 실패**: 세션 프록시가 태그 push(git HTTP 403)와 GitHub API 쓰기를 모두 거부. 우회하지 않음 → 보스 맥에서 실행할 명령을 `docs/ORCA_HANDOFF.md` 0-2 에 적음
- `docs/FROZEN_NUMBERS.md`: 자소서 숫자 6개와 출처 파일·필드. **6개 모두 결과 파일과 일치** (불일치 0)
  - 인용 오류 40 = 11/08 결과만으로 검사기를 다시 돌려 15(set-v1) + 24(set-v2) + 1(set-public) 재현, v1·v2 0
  - 근거 조항 정확도 0.0 → 1.0 (set-v1·v2, 1차·2차 모두), 라벨 24 = 8×3, 규칙 기준값 14(전체 18), set-v1 v2 오탐 3건 = 제11조/design_change ×3 (set-v2 0건), 토큰 257,866 ÷ 43,560 = 5.92
  - 해석 주의 4가지(40은 세 평가셋 합·2차 기준 39, baseline 0% 이유, v1 오탐은 4건 중 3건, 1차·2차 Precision 차이)를 같은 파일에 기록

**[2] 병렬 작업 공통 규칙** — `CLAUDE.md` 새 섹션 + 같은 내용의 `AGENTS.md`(다른 CLI 에이전트용, 절대 규칙 요약 포함). 두 파일의 규칙 섹션이 같음을 diff 로 확인
- 보스 지시 9개 외에 공유 파일 충돌을 막는 운영 규칙 추가: 진행 기록은 `docs/progress/<브랜치명>.md`(PROGRESS.md 는 보스가 합칠 때 정리), 요구사항은 작업별 ID 범위로 제안만, 담당 없는 공유 파일 목록, 첫 push 뒤 rebase 대신 merge

**[3]·[4] `docs/ORCA_HANDOFF.md`** — 맨 위 보스 맥 할 일(클론·setup·test, 태그 push, gh 로그인, Orca 설치, 1차 워크트리 4개, 워크트리별 첫 프롬프트, 2차 시작), 작업 8개의 목표/담당 파일/완료 기준/하지 말 것/의존 관계, 마지막에 담당 파일 겹침 표
- 담당 파일은 `git ls-files` 기준 실제 경로. 동시 진행 작업끼리 겹침 없음
- 보스 확인이 필요한 추가 제안 4개: ws-c 에 `schemas.py`·`nodes/report.py`(선택 필드 추가만), `data/amount_basis.yaml`, ws-d 의 `scripts/run_public_contracts.py`, ws-f 의 `data/demo/`
- 발견한 제약: HWP 표 손실은 `data/raw/` 변환본을 고쳐야 해결되므로 ws-b 는 감지·표시까지만, 재변환은 보스 결정. 워크트리마다 `make setup` 필요(editable 설치가 설치 폴더의 src 를 가리킴), 워크트리에 `.env` 복사 금지
- Orca 공식 문서(orca.dev)는 세션 네트워크에서 막혀 메뉴 이름을 확인하지 못함 → 워크트리 생성은 `git worktree` 명령으로 적음. 설치 링크·brew 명령은 GitHub `stablyai/orca` README 기준

**다음 할 일 (보스)**
- 맥에서 `docs/ORCA_HANDOFF.md` 0-1 ~ 0-6 순서대로. 특히 0-2 태그 push
- 추가 제안 4개 승인 여부

## 2026-11-14 · 인수인계 보완 ([4] 나머지 + [5])
- `docs/ORCA_HANDOFF.md` 0-6: 첫 프롬프트를 보스 지정 문장으로 교체 ("…계획을 5줄로 보고한 뒤 내 OK를 받고 시작해"), Codex 는 AGENTS.md
- 0-7: PR 합치는 순서(1차 ws-d → ws-a → ws-g, 2차 C2 → C1 → ws-b → C3 → C4 → ws-f, ws-h 독립)와 합칠 때마다 돌릴 명령(`make test`·`make lint`·보호 파일 수정 확인 `git diff --diff-filter=MD` 출력 없음)
- 0-8: 2차 시작 조건 체크리스트 11개 (태그, 1차 합침, 테스트, 리뷰, set-v3 라벨·검수·hit@3, 기준선 측정 결정, 보스 결정 5개, PROGRESS 정리)
- 0-10: 걸리는 시간 추정 (1차 반나절~하루, 2차 2~3일, 합계 약 3~4일, 보스 시간 약 7~10시간) — 이 레포 실제 소요 기준 추정
- 순서 정정: C2 는 `graph.py` 를 고치지 않아 C1 과 동시 진행, C1 → C3 → C4 는 앞 PR 합친 뒤 (이전 문안의 "앞 PR 을 연 뒤"는 graph.py 충돌 위험)
- 태그 push 재시도 1회 → 같은 HTTP 403. 여전히 보스 맥에서 실행 필요 (0-2)
