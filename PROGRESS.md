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
