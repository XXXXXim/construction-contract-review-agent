# PLAN: 마일스톤 (마감 11/7(토) 23:00)

> 시간이 모자라면 **M6 UI를 줄이고 M5 평가를 지킨다.**

## M0: 하네스 파일, 레포 구조
- [x] `CLAUDE.md`, `docs/SPEC.md`, `docs/PLAN.md`, `PROGRESS.md`
- [x] `Makefile` (setup/test/eval/eval-baseline/run/lint), `.env.example`, `.gitignore`
- [x] `pyproject.toml` (허용 의존성만), 패키지 골격, pydantic 스키마 초안
- [x] `make test` 통과 (스모크 테스트)
- [x] SPEC 보고 → 보스 확인 (레포 생성·원문 제공으로 진행 승인)

## M1: PDF 파싱, 조항 분할
- [x] `data/raw/`에 원문 3종 확인 (HWP는 txt로 변환)
- [x] `parse` 노드 (pypdf), `split_clauses` 노드 ("제n조(제목)" 패턴)
- [x] 표준계약서 3종의 조항 수와 제목 표 출력 (`scripts/inspect_raw.py` → `docs/raw_clauses.md`)
- [x] SPEC 5절 카테고리 표를 원문 출처로 채움 (`data/thresholds.yaml` + 인용 검증 테스트)
- [x] 단위 테스트 통과 (33 passed)

## M2: 합성 평가셋
- [x] `scripts/make_synthetic.py` (seed=20261104): 표준하도급계약서 기반 계약서 3개 × 변형 8개
- [x] 정상 조항 포함 (계약서당 50조 중 42조 정상)
- [x] `eval/cases/*.yaml` 라벨 24개
- [x] 해시 비교 테스트로 재현성 확인 (`tests/test_synthetic.py`)

## M3: 검색 + 검색 평가
- [x] 표준 조항 인덱스 (BM25 어절+2-gram, 임베딩은 EMBEDDING_PROVIDER=openai 때 RRF 하이브리드)
- [x] `retrieve_standard` 노드, 임베딩 없을 때 BM25 폴백
- [x] hit@3 측정 → PROGRESS 기록 (BM25 단독; 하이브리드는 키 확보 후 측정)

## M4: 규칙 레이어 + LLM 판정 + 근거 검증
- [x] `rule_check` (원문 추출 기준값 14개, 등장 순서 맞춤 숫자 비교)
- [x] `llm_judge` 구조화 출력 + `evidence_quote` 검증 (지목 조항 본문 부분문자열, 실패 시 폐기)
- [x] `report` (MD + JSON, 면책 고지)
- [x] LangGraph 조립 (baseline/v1/v2 경로), `FakeLLM` E2E 테스트 통과
- [ ] 실제 LLM으로 리포트 1건 생성 ← **API 키 필요**

## M5: baseline / v1 / v2 비교 평가
- [x] `make eval-baseline`, `make eval CONFIG=v1`, `make eval` (fake 판정기로 동작 확인)
- [x] 비교표 `eval/results/{날짜}_compare.md` 저장 (fake)
- [ ] 실제 LLM으로 baseline/v1/v2 측정 ← **API 키 필요**
- [ ] 무엇을 바꿨더니 어떤 지표가 얼마나 변했는지 PROGRESS에 기록

## M6: Streamlit UI + Dockerfile
- [x] PDF 업로드 → 리포트 표시/다운로드 (`app/streamlit_app.py`)
- [x] `make run` 기동 확인 (헬스체크 ok)
- [ ] `docker build` ← 이 세션에 docker 데몬이 없어 **미검증**. 보스 맥에서 `docker build -t contract-review .` 확인 필요

## M7: README 케이스 스터디
- [x] 문제 정의, 아키텍처(Mermaid), 비교표(fake), 한계, 다음 단계 (실제 LLM 숫자는 키 확보 후 교체)
- [ ] 최종 보고 (지표표, 최대 개선, 한계 3, 자소서 3줄, 면접 질문 5)
