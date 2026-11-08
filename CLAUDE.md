# CLAUDE.md: 건설 하도급 계약 검토 에이전트

> 새 세션은 **`PROGRESS.md`를 먼저 읽고** 마지막 "다음 할 일"부터 이어서 작업한다.
> 개발 단계 문서: `docs/01_brief.md`(문제) → `02_requirements.md`(FR/NFR) → `03_design.md`(스택·아키텍처) →
> `04_readiness.md`(준비물·리스크) → `PLAN.md`(일정). 상세 스키마는 `docs/SPEC.md`.
> 요구사항이 바뀌면 `02_requirements.md`를 먼저 고친다. 새 테스트에는 관련 요구사항 ID(FR-xx)를 docstring에 적는다.

## 프로젝트 한 줄 요약
하도급 계약서(PDF)를 표준하도급계약서·표준도급계약서·하도급법과 **조항별로 비교**하고, 불리하거나 표준에서 벗어난 조항을 **근거 인용과 함께** 찾아내는 LangGraph 파이프라인. 공개 자료만 쓰는 개인 포트폴리오 프로젝트이며, 성능은 `make eval`의 **측정값**으로 증명한다.

## 절대 규칙 (가드레일)
1. **법령 수치와 조문을 기억으로 쓰지 않는다.** 기한, 비율, 조문 번호 같은 기준값은 `data/raw/` 원문에서 추출하고 출처(파일명, 조항)를 코드와 리포트에 남긴다. 원문에서 찾지 못하면 `TODO(source-needed)`로 표시하고 보스에게 보고한다.
2. **데이터를 지어내지 않는다.** 평가용 계약서는 (a) 표준계약서를 변형한 합성 데이터(파일명과 README에 `synthetic` 명시) 또는
   (b) **공정위 공개 의결서에 인용된 실제 계약 문구**(의결번호·쪽·표/문단 출처를 남기고 원문 그대로, 이미지에서 옮긴 것은 `transcribed_from_image` 표시)만 쓴다.
   (b)는 2026-11-08 보스 승인. 문구를 다듬거나 지어내지 않는다.
3. SK에코플랜트의 내부 정보나 비공개 자료를 가정하거나 쓰지 않는다.
4. API 키는 환경변수로만 읽는다. `.env`는 커밋하지 않고(`.gitignore`), 키를 출력하지 않는다.
5. 모든 리포트에 "법률 자문이 아닌 검토 보조 도구"라는 고지를 넣는다 (`contract_review.schemas.DISCLAIMER`).
6. 허용 의존성: `langgraph`, `langchain-core`, `langchain-openai`, `langchain-anthropic`, `chromadb`, `rank-bm25`, `pypdf`, `pydantic`, `streamlit`, `pytest`, `ruff`, `pyyaml`, `python-dotenv`. 그 밖의 패키지는 **추가 전에 이유를 말하고 승인받는다.**
7. 같은 테스트가 **3번 연속 실패하면 멈추고** 원인 가설과 시도한 방법을 보고한다. 테스트 삭제나 `skip`으로 통과시키는 것은 금지.
8. 네트워크 때문에 무언가를 못 받으면 우회하지 말고 필요한 것을 보고한다.
9. 평가 숫자를 좋게 보이려고 평가셋(`eval/cases`)을 고치지 않는다. 나빠진 숫자도 그대로 기록한다.

## 폴더 구조
```
.
├── CLAUDE.md               # 이 파일 (하네스 규칙)
├── PROGRESS.md             # 진행 로그. 새 세션은 여기부터 읽는다
├── docs/01_brief.md        # P0 문제 정의 (고객, 성공 지표, 가정)
├── docs/02_requirements.md # P1 요구사항 (FR/NFR, 수용 기준, 상태)
├── docs/03_design.md       # P2 설계 (ADR, 아키텍처, 컴포넌트)
├── docs/04_readiness.md    # P3 준비물·리스크
├── docs/05_traceability.md # P6 요구사항 추적표
├── docs/06_retro.md        # P7 회고 (KPT)
├── docs/07_final_report.md # 최종 보고 (지표, 자소서 3줄, 면접 질문)
├── docs/SPEC.md            # 입력·출력 스키마, 카테고리, 판정 기준, 비범위
├── docs/PLAN.md            # 마일스톤 체크리스트
├── src/contract_review/
│   ├── schemas.py          # pydantic 스키마 (노드 입출력, Finding, Report)
│   ├── config.py           # 환경변수 기반 설정 (LLM/임베딩 provider)
│   ├── llm.py              # provider 팩토리 + FakeLLM (M4)
│   ├── graph.py            # LangGraph StateGraph 조립 (M4)
│   └── nodes/              # parse, split_clauses, retrieve_standard, rule_check, llm_judge, report
├── app/streamlit_app.py    # UI (M6)
├── scripts/make_synthetic.py  # 합성 평가셋 생성 (M2, 시드 고정)
├── data/raw/               # 보스가 넣는 공개 원문 PDF (수정 금지)
├── data/synthetic/         # 합성 계약서 set-v1 (*synthetic*, 결과 재현용으로 수정 금지)
├── data/synthetic_v2/      # 합성 계약서 set-v2 (조문 참조 재번호 수정판)
├── eval/cases/*.yaml       # 정답 라벨 set-v1
├── eval/cases_v2/*.yaml    # 정답 라벨 set-v2
├── eval/results/           # {날짜}_{config}.md 평가 결과
└── tests/
```

## 명령어
| 명령 | 설명 |
|---|---|
| `make setup` | `.venv` 생성 후 의존성 설치 (`pip install -e ".[dev]"`) |
| `make test` | pytest 실행. **API 키 없이 통과해야 한다** (FakeLLM 사용) |
| `make lint` | ruff check + ruff format --check |
| `make eval` | v2 config로 평가, `eval/results/`에 저장 (M5) |
| `make eval-baseline` | baseline config로 평가 (M5) |
| `make run` | Streamlit UI 실행 (M6) |

## 코딩 규칙
- Python 3.11+, 모든 함수에 **타입힌트**.
- 노드 입출력과 외부 경계(LLM 응답, 리포트, 평가 케이스)는 **pydantic 모델**로 정의한다.
- 한국어 주석과 docstring 사용 OK.
- 법령/표준 기준값은 코드에 상수로 박지 말고, 원문 추출 결과(출처 포함)를 읽어 쓴다.
- LLM provider는 `LLM_PROVIDER` 설정으로 바꾼다 (`fake` | `openai` | `anthropic`). 테스트는 항상 `fake`.
- 테스트에서 네트워크를 쓰지 않는다.

## 커밋 규칙
- 마일스톤마다: 테스트 통과 → `PROGRESS.md` 업데이트 → 작은 단위로 커밋.
- 메시지 형식: `feat(M3): ...`, `fix(M4): ...`, `docs(M0): ...`, `test(M1): ...`
