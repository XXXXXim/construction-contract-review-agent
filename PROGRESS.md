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
