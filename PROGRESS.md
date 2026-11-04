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
