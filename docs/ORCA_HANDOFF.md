# Orca 병렬 작업 인수인계

> 기준: 태그 `v1.0-application` (커밋 `3496a64`, 자소서 인용 버전) + 이 문서를 추가한 main.
> 공통 규칙: `CLAUDE.md` / `AGENTS.md` 의 "병렬 작업 공통 규칙". 고정 숫자: `docs/FROZEN_NUMBERS.md`.
> 작성: 2026-11-14. 아래 담당 파일은 이 시점의 `git ls-files` 를 보고 채웠다.

---

## 0. 보스 맥에서 할 일 (순서대로)

### 0-1. 클론하고 출발점 확인
```bash
mkdir -p ~/code && cd ~/code
git clone https://github.com/XXXXXim/construction-contract-review-agent.git
cd construction-contract-review-agent
make setup && make test        # 103 passed 가 나와야 한다 (API 키 불필요)
make lint
```
Python 3.11 이상이 필요하다. 기본 `python3` 가 3.10 이하라면 `make setup PY=python3.13` 처럼 지정한다.

### 0-2. 태그 push (클라우드 세션에서는 막혀서 못 함)
클라우드 세션 프록시가 태그 push 를 거부했다(HTTP 403). 맥에서 한 번만 실행한다.
```bash
git tag -a v1.0-application 3496a64 -m "SK에코플랜트 지원서(자기소개서)에 인용된 버전. 숫자 출처: docs/FROZEN_NUMBERS.md"
git push origin v1.0-application
git ls-remote --tags origin    # refs/tags/v1.0-application 이 보이면 끝
```

### 0-3. PR 을 만들 수 있게 GitHub CLI 로그인 (처음 한 번)
```bash
brew install gh
gh auth login
```

### 0-4. Orca 설치
- 공식 사이트: <https://orca.dev/download> (Stably AI 의 오픈소스 데스크톱 앱, 소스 <https://github.com/stablyai/orca>)
- Homebrew. `orca` 라는 이름의 다른 cask(Plotly)가 있으니 **전체 이름**을 쓴다.
```bash
brew install --cask stablyai/orca/orca
```
> 주의: Orca 화면의 메뉴 이름은 이 세션에서 공식 문서(orca.dev)에 접속하지 못해 **확인하지 못했다.** 아래 0-5 는 Orca 화면이 다르더라도 그대로 통하도록 `git worktree` 명령으로 적었다. Orca 에서 워크트리를 만들 때는 **같은 브랜치 이름과 같은 기준(origin/main)**만 맞추면 된다.

### 0-5. 1차 작업 4개의 워크트리 만들기
Orca 에서 레포 폴더(`~/code/construction-contract-review-agent`)를 연 뒤, 아래 4개를 만든다. Orca 화면으로 만들어도 되고 터미널로 만들어도 결과는 같다.
```bash
cd ~/code/construction-contract-review-agent
git fetch origin
git worktree add -b ws-a-fit       ../ccra-wt/ws-a-fit       origin/main
git worktree add -b ws-d-eval      ../ccra-wt/ws-d-eval      origin/main
git worktree add -b ws-g-interview ../ccra-wt/ws-g-interview origin/main
git worktree add --detach          ../ccra-wt/ws-e-review    origin/main   # 리뷰어: 브랜치 없음(읽기 전용)
git worktree list
```
그다음 **워크트리마다** 가상환경을 따로 만든다.
```bash
for w in ws-a-fit ws-d-eval ws-g-interview ws-e-review; do (cd ../ccra-wt/$w && make setup && make test); done
```
- 왜 따로 만드나: `make setup` 은 `pip install -e .` 라서 가상환경이 **설치한 폴더의 `src/`** 를 가리킨다. 원래 클론의 `.venv` 를 같이 쓰면 워크트리에서 고친 코드가 아니라 main 의 코드가 실행된다.
- **`.env` 는 워크트리에 복사하지 않는다.** 키가 없으면 실수로 실제 LLM 을 부를 수 없다 (공통 규칙 5).

### 0-6. 각 워크트리에 붙여넣을 첫 프롬프트
Claude Code 든 Codex 든 같은 문장을 쓴다. Codex 는 `CLAUDE.md` 대신 `AGENTS.md` 를 읽는다.

**ws-a-fit**
```
ORCA_HANDOFF.md의 ws-a-fit 작업을 해. 먼저 CLAUDE.md(또는 AGENTS.md)의 "병렬 작업 공통 규칙"과 docs/ORCA_HANDOFF.md의 ws-a-fit 절, docs/FROZEN_NUMBERS.md를 읽고, 담당 파일·완료 기준·하지 말 것을 5줄로 요약해서 보여준 뒤 시작해. 브랜치는 ws-a-fit, 끝나면 PR만 열고 멈춰.
```
**ws-d-eval**
```
ORCA_HANDOFF.md의 ws-d-eval 작업을 해. 먼저 CLAUDE.md(또는 AGENTS.md)의 "병렬 작업 공통 규칙"과 docs/ORCA_HANDOFF.md의 ws-d-eval 절을 읽고, 담당 파일·완료 기준·하지 말 것을 5줄로 요약해서 보여준 뒤 시작해. 실제 LLM 호출이 필요한 단계는 실행하지 말고 예상 호출 수와 토큰을 PR에 적고 멈춰. 브랜치는 ws-d-eval.
```
**ws-g-interview**
```
ORCA_HANDOFF.md의 ws-g-interview 작업을 해. 먼저 CLAUDE.md(또는 AGENTS.md)의 "병렬 작업 공통 규칙"과 docs/ORCA_HANDOFF.md의 ws-g-interview 절을 읽고, 담당 파일·완료 기준·하지 말 것을 5줄로 요약해서 보여준 뒤 시작해. 코드는 읽기만 하고 docs/interview/ 와 docs/progress/ws-g-interview.md 만 써. 브랜치는 ws-g-interview.
```
**ws-e-review** (다른 작업의 PR 이 열린 뒤에)
```
ORCA_HANDOFF.md의 ws-e-review 역할을 해. 먼저 CLAUDE.md(또는 AGENTS.md)의 "병렬 작업 공통 규칙"과 docs/ORCA_HANDOFF.md의 ws-e-review 절을 읽어. 열린 PR 목록을 gh pr list로 확인하고, PR마다 체크리스트대로 검사해서 PR 코멘트와 docs/reviews/<PR번호>.md를 남겨. 코드는 고치지 말고 커밋도 하지 마.
```

### 0-7. 1차 PR 을 합친 뒤 (2차 시작)
```bash
cd ~/code/construction-contract-review-agent && git switch main && git pull
git worktree add -b ws-b-fix              ../ccra-wt/ws-b-fix              origin/main
git worktree add -b ws-c-advance-c1       ../ccra-wt/ws-c-advance-c1       origin/main   # C2~C4 는 C1 PR 을 연 뒤 하나씩
(cd ../ccra-wt/ws-b-fix && make setup && make test)
(cd ../ccra-wt/ws-c-advance-c1 && make setup && make test)
```
ws-f-demo 는 C2(`ws-c-advance-c2`) PR 을 합친 뒤에 만든다. ws-h-databricks 는 선택이며 언제든 독립적으로 시작할 수 있다.
다 끝난 워크트리는 `git worktree remove ../ccra-wt/<이름>` 으로 정리한다.

---

## 1. 작업 한눈에 보기

| 차수 | 작업 | 브랜치 | 성격 | 요구사항 ID 범위 |
|---|---|---|---|---|
| 1차 | ws-a-fit | `ws-a-fit` | 문서만 | – |
| 1차 | ws-d-eval | `ws-d-eval` | 데이터·평가 스크립트 (시스템 코드 불변) | FR-20 ~ FR-24, NFR-12 ~ NFR-13 |
| 1차 | ws-g-interview | `ws-g-interview` | 문서만, 코드 수정 금지 | – |
| 1차 | ws-e-review | (없음, `origin/main` detached) | 읽기 전용 리뷰어 | – |
| 2차 | ws-b-fix | `ws-b-fix` | 버그 수정 | FR-25 ~ FR-29 |
| 2차 | ws-c-advance | `ws-c-advance-c1` ~ `-c4` (기능마다 PR 하나) | 고도화 | FR-30 ~ FR-39, NFR-14 ~ NFR-15 |
| 2차 | ws-f-demo | `ws-f-demo` | 데모 (C2 합친 뒤) | FR-40 ~ FR-44, NFR-16 ~ NFR-17 |
| 선택 | ws-h-databricks | `ws-h-databricks` | 노트북 | FR-45 ~ FR-49 |

**모든 작업 공통 담당:** 자기 진행 기록 `docs/progress/<브랜치명>.md` (ws-e 는 제외). 요구사항 제안은 이 파일의 "요구사항 제안" 절에 쓰고, `docs/02_requirements.md`·`docs/05_traceability.md` 반영은 보스가 합칠 때 한다.

---

## 2. 1차 작업

### ws-a-fit · 적합성 (문서만)
**목표**
- README 의 관점을 원청(원사업자) 기준으로 다시 쓴다: "원청이 하도급 계약을 맺기 전에 하도급법 위반 소지가 있는 조항을 찾아 제재 리스크를 막는 컴플라이언스 검토 도구".
- **탐지 로직은 같다**는 점을 명시한다 (같은 조항 분할·표준 대조·규칙·LLM 판정. 바뀌는 것은 결과를 읽는 관점).
- 하도급 업체 관점은 '확장 가능성' 한 줄로 내린다.
- README 에 빈 섹션 **"v1.1 이후 결과"** 를 만들어 둔다 (이후 새 결과가 들어갈 자리. 지금은 "아직 없음").

**담당 파일**
- `README.md`
- `docs/01_brief.md`
- `docs/07_final_report.md`
- `docs/progress/ws-a-fit.md` (새 파일)

**완료 기준**
- README 첫 화면 한 줄 설명과 "1 문제" 절이 원청 관점이고, "탐지 로직은 동일" 문장이 있다.
- `docs/FROZEN_NUMBERS.md` 의 6개 숫자가 README·07 에서 **글자 그대로** 남아 있다 (PR 에 `git diff v1.0-application -- README.md docs/07_final_report.md` 중 숫자 줄 비교 결과 첨부).
- 01_brief 의 고객·Pain point 가 원청 컴플라이언스 담당 기준으로 바뀌고, 성공 지표는 기존 측정값만 쓴다.
- `make test` · `make lint` 통과 (문서만 바꿨어도 확인).

**하지 말 것**
- 숫자·평가 결과 수정, 새 성능 주장. 원청 관점에서 "제재 금액"·"과징금 규모" 같은 수치를 쓸 때는 `data/raw/` 원문 근거가 없으면 쓰지 않는다 (`TODO(source-needed)`).
- 회사 관련 문장은 공개 보도로 확인되는 것만. 기존 `TODO(링크)` 2곳을 지어낸 링크로 채우지 않는다.
- `docs/02_requirements.md`, `docs/03_design.md` 등 담당 밖 문서 수정. 관점이 어긋나는 문장을 발견하면 PR "남은 문제"에 위치만 적는다.

**의존 관계**
- 선행 없음. ws-d·ws-g 와 동시 진행.
- ws-g 는 이 작업의 원청 관점 문장을 면접 답변에 쓸 수 있으므로, ws-g 가 먼저 끝나면 ws-g 답변 중 관점 관련 1~2개는 합친 뒤 보스가 맞춘다.
- 2차 이후 README "v1.1 이후 결과" 에 숫자를 넣는 일은 ws-a 담당이 끝난 뒤이므로, **보스가 승인한 결과가 생겼을 때 작은 문서 PR(`ws-a-fit-results`)로 따로** 한다.

---

### ws-d-eval · 평가 강화 (시스템 코드 불변)
**목표**
1. **문장 재작성 평가셋 set-v3**: set-v2 의 변형 조항(24개)을 표준 원문과 다른 문장으로 바꿔 쓴 계약서 3부.
   - 라벨(`eval/cases_v3/`)은 **측정 전에 확정·커밋**한다.
   - 재작성 문장은 `data/synthetic_v3/paraphrases.yaml` 에 조항마다 `원래 변형 문장 / 바꾼 문장 / 보존한 핵심 요소(숫자·기한·주체·의무 방향) / 의미가 같다고 본 근거` 로 남긴다. 숫자·기한이 그대로인지는 테스트로 자동 검사한다.
   - 재작성은 **API 를 부르지 않고** 에이전트가 직접 작성한 문장을 yaml 에 넣고, `scripts/make_paraphrase.py` 가 그것을 set-v2 계약서에 결정적으로 적용한다 (시드·입력 고정, 다시 돌리면 바이트 동일).
   - 보스 검수용으로 무작위 5개(시드 고정)를 뽑아 `data/synthetic_v3/REVIEW_SAMPLE.md` 에 원래 문장·바꾼 문장·근거를 나란히 적는다.
2. **실제 공개 계약서**: 공공기관 입찰 공고 첨부 등 공개된 실제 하도급·도급 계약서 몇 건을 `data/public_contracts/` 에 넣고, `data/public_contracts/README.md` 에 파일마다 **출처 URL·다운로드 날짜·기관·공고명**을 적는다. 라벨이 없으므로 정답 채점이 아니라 '사람 검토용 결과'로만 쓴다.
3. **반복 실행 편차**: `scripts/repeat_eval.py` — 같은 설정을 N회(기본 3) 실행해 지표별 평균과 범위(최소~최대)를 표로 저장한다. 결과는 새 파일(`eval/results/{날짜}_repeat_{config}_{dataset}.md/json`)로만.
4. **측정은 하지 않는다.** 실행 명령과 예상 호출 수·토큰을 PR 에 적고 보스 승인을 받는다.

**담당 파일**
- `data/synthetic_v3/` (새 폴더: 계약서 3부, `README.md`(synthetic 명시), `paraphrases.yaml`, `REVIEW_SAMPLE.md`)
- `eval/cases_v3/` (새 폴더: 라벨 3개)
- `data/public_contracts/` (새 폴더: 원문 파일 + `README.md`)
- `scripts/make_paraphrase.py` (새 파일)
- `scripts/repeat_eval.py` (새 파일)
- `src/contract_review/eval.py` — **`DATASETS` 에 `"v3"` 추가와 이에 필요한 CLI 옵션만**
- 새 테스트: `tests/test_dataset_v3.py`, `tests/test_repeat_eval.py`, `tests/test_public_contracts.py`
- `docs/progress/ws-d-eval.md`
- (추가 제안, 보스 확인) 공개 계약서를 라벨 없이 돌려 사람 검토용 리포트를 만드는 `scripts/run_public_contracts.py` (새 파일). `eval.py` 를 채점 없는 모드로 넓히는 대신 별도 스크립트로 둔다.

**완료 기준**
- `make test` 통과, 새 테스트에 FR-20~ ID. 최소한 다음을 검사:
  - set-v3 라벨 24개가 계약서 조항과 맞는다 (`test_committed_cases_match_contracts` 와 같은 방식)
  - 재작성 조항마다 원래 변형의 숫자·기한이 그대로 있다
  - 변형하지 않은 조항은 set-v2 와 같다, 내부 조문 참조가 모두 존재하는 조항을 가리킨다 (set-v1 버그 재발 방지)
  - `make_paraphrase.py` 재실행이 바이트 동일
  - `repeat_eval.py` 가 FakeLLM 으로 3회 돌아 평균·범위를 계산한다 (FakeLLM 은 결정적이므로 범위 0)
- set-v3 에서 BM25 검색 hit@3 를 **API 없이** 잰 값을 진행 기록에 적는다 (검색만이라 비용 0). `eval_retrieval.py` 는 담당 밖이라 CLI 에 옵션을 더하지 않고, `DATASETS["v3"]` 추가 뒤 함수로 부른다:
  `.venv/bin/python -c "from contract_review.eval_retrieval import evaluate, load_queries; from contract_review.retrieval import StandardIndex; import json; print(json.dumps(evaluate(StandardIndex.build(embedder=None), load_queries('v3')), ensure_ascii=False))"` set-v2 의 1.00 보다 낮아야 "어려운 평가셋"이라는 근거가 된다. 낮지 않으면 그대로 보고.
- PR 에 측정 승인 요청: 명령, 예상 LLM 호출 수, 예상 입력·출력 토큰. 참고값(set-v2, 계약서 3부, 1회, 11/10 실측): baseline 호출 3·입력 130,680·출력 20,400 / v1 호출 154·입력 772,980·출력 45,672 / v2 호출 154·입력 773,598·출력 41,310. 세 구성 1회 ≈ 호출 311·입력 168만·출력 11만 토큰, **3회 반복 ≈ 호출 933·입력 503만·출력 32만 토큰.** 반복 측정은 `LLM_CACHE=0` 이어야 의미가 있다(캐시가 켜지면 같은 응답이 재사용됨). 금액은 단가를 기억으로 쓰지 않는 규칙상 적지 않는다.
- `data/public_contracts/` 의 모든 파일에 출처 URL·날짜가 있다.

**하지 말 것**
- `graph.py`, `nodes/`, `retrieval.py`, `llm.py` 등 시스템 코드 수정.
- `eval/cases/`, `eval/cases_v2/`, `eval/cases_public/`, `data/synthetic/`, `data/synthetic_v2/`, `data/public_cases/`, `eval/results/` 기존 파일 수정. `scripts/make_synthetic.py` 수정 (set-v1·v2 재현성이 깨짐).
- 실제 LLM 호출 (재작성 생성 포함, 평가 실행 포함). 결과를 보고 라벨이나 재작성 문장 바꾸기.
- 공개 계약서에 개인정보(개인 이름·연락처·서명·주민번호 등)가 있으면 넣지 말고 보고. 로그인·유료 자료, 이용 조건이 금지하는 자료는 넣지 않는다. 내려받기가 네트워크로 막히면 우회하지 않고 보고.
- 의존성 추가 (HWP 변환 도구 포함). HWP 만 있는 공개 계약서는 출처만 README 에 적고 "HWP 라 미포함"으로 둔다.

**의존 관계**
- 선행 없음. ws-a·ws-g 와 동시 진행.
- **ws-b, ws-c 의 "개선" 주장은 이 작업이 만든 set-v3 로만** 측정한다 (공통 규칙 6). 그래서 2차 시작 전에 합쳐져야 한다.
- 2차 작업자는 set-v3 의 계약서·재작성 문장을 개발 중에 열어 보고 튜닝하면 안 된다 (측정에만 사용).

---

### ws-g-interview · 면접 대비 (문서만, 코드 수정 금지)
**목표** — 코드를 직접 읽고 `docs/interview/` 에 작성
- `ARCHITECTURE_1PAGE.md`: 보스가 2분 안에 말로 설명할 수 있는 구조 설명. 노드별(parse → split_clauses → retrieve_standard → rule_check → llm_judge → report) 입력·출력, 구성(baseline/v1/v2)의 차이, 설계 이유.
- `DESIGN_QA.md`: "왜 이렇게 만들었나" 질문 30개. 질문마다 짧은 답 / 근거 `파일:줄` / 다른 선택지와 버린 이유 / 이 설계의 약점.
  반드시 포함: 왜 LangGraph 인가, 왜 BM25 인가, 왜 규칙을 LLM 보다 우선하나, 근거 검증이 0건을 버렸는데 왜 남겨뒀나, 토큰 5.9배는 실무에서 괜찮나, 합성 데이터를 믿을 수 있나, 원청에게 이 도구가 왜 필요한가, "에이전트인가 워크플로우인가".
- `SELF_TEST.md`: 보스가 코드를 이해했는지 확인하는 문제 20개. 답은 맨 아래 `<details>` 로 접어 둔다.

**담당 파일**
- `docs/interview/` (새 폴더: 위 3개 파일)
- `docs/progress/ws-g-interview.md`

**완료 기준**
- 30개·20개 개수 충족. 모든 `파일:줄` 이 이 브랜치의 기준 커밋에서 실제로 그 내용을 가리킨다 (PR 에 기준 커밋 해시 명시).
- 숫자는 `docs/FROZEN_NUMBERS.md` 와 `eval/results/` 저장값만 쓴다. 1차·2차 실행 차이(Precision 1.00 vs 0.92 등)가 있는 숫자는 둘 다 쓰거나 실행을 밝힌다.
- 보스의 역할은 `PROGRESS.md` 와 `docs/` 에 **"보스 결정"** 으로 기록된 것만 근거로 쓴다 (예: 공정위 의결서 사용 승인, set-v2 별도 버전, 1차·2차 병기). 각 서술 옆에 기록 위치를 적는다.
- `make test` · `make lint` 통과.

**하지 말 것**
- 코드·테스트·다른 문서 수정. 기록에 없는 일을 보스가 했다고 쓰기.
- 법령 수치·조문을 기억으로 쓰기 (원문 또는 `data/thresholds.yaml` 인용).
- 회사 관련 추측, 내부 정보·특강 내용.

**의존 관계**
- 선행 없음. ws-a 의 원청 관점 문장과 겹치는 답(“원청에게 왜 필요한가”)은 ws-a 가 합쳐진 뒤 보스가 맞춘다. 2차 작업이 합쳐지면 줄 번호가 바뀌므로, 그때 `파일:줄` 갱신은 별도 작은 PR 로 한다.

---

### ws-e-review · 리뷰어 (읽기 전용, 자기 브랜치 없음)
**목표** — 다른 작업의 PR 이 열리면 검사만 한다.

**체크리스트 (PR 마다)**
1. 담당 파일 밖을 건드렸는가 — `gh pr diff <N> --name-only` 를 이 문서 §5 겹침 표와 대조
2. `docs/FROZEN_NUMBERS.md` 가 바뀌었는가, README·07 의 고정 숫자 줄이 바뀌었는가
3. `eval/results/` 기존 파일, `eval/cases*/` 기존 라벨, `data/raw/` 를 수정·삭제했는가
4. 테스트가 통과하는가 — PR 의 GitHub Actions(Python 3.11·3.13 `make test`·`make lint`) 결과 확인. 직접 돌릴 때는 아래 명령으로 PR 을 detached 로 받아 돌리고 다시 main 으로 돌아온다
   ```bash
   git fetch origin pull/<N>/head && git checkout --detach FETCH_HEAD && make test && make lint; git checkout --detach origin/main
   ```
   (가상환경은 editable 설치라 체크아웃한 코드가 그대로 쓰인다. 단 `pyproject.toml` 이 바뀐 PR 은 `make setup` 이 필요하므로 그 사실만 적는다.)
5. 개선 주장이 ws-d 평가셋(set-v3) 기준인가, 개발 중 본 데이터로 잰 숫자를 '개선'이라 했는가
6. 근거 없는 법령 수치(기한·비율·조문 번호)가 들어갔는가 — 새 숫자마다 `data/raw/` 원문 또는 `data/thresholds.yaml` 출처가 있는지
7. 실제 LLM 호출이 승인 없이 실행됐는가 (새 `eval/results/` 파일, `.cache/` 언급), 새 의존성이 승인 없이 추가됐는가
8. PR 설명이 4단 형식(바꾼 것 / 검증 방법과 결과 / 바꾸지 않은 것 / 남은 문제)인가

**담당 파일**
- `docs/reviews/<PR번호>.md` — **이 폴더만 쓰기 허용. 커밋하지 않는다** (자기 브랜치가 없으므로 워크트리 안의 로컬 파일로 남는다. 영구 기록은 PR 코멘트).

**완료 기준**
- PR 마다 `gh pr comment <N>` 코멘트 1개(체크리스트 8개 항목 ✅/❌ + 문제마다 고치는 방법 제안)와 `docs/reviews/<N>.md` 요약(보스가 30초 안에 읽을 분량: 합쳐도 되는가 / 막는 문제 / 사소한 문제).

**하지 말 것**
- 코드·문서 수정, 커밋, push, PR 승인·합치기·닫기. 다른 작업의 브랜치에 직접 고쳐 넣기.
- 실제 LLM 을 부르는 명령 실행.

**의존 관계**
- 1차·2차의 모든 PR 이 대상. PR 이 없으면 할 일이 없다.

---

## 3. 2차 작업 (1차 PR 을 보스가 합친 뒤)

### ws-b-fix · 오류 수정
**목표** — 이미 기록된 한계 중 코드로 고칠 수 있는 것
1. **검색이 제목 "특약사항"에 끌려 대금 지급 조항을 놓치는 문제** (README "3 평가" set-public case 1, `PROGRESS.md` 2026-11-08 set-public 기록: 국토부 제42조(특약사항)가 1등, 표준 제40조가 top-3 밖). 예: 조항 제목과 본문의 가중치 분리.
2. **HWP 표 변환 손실** (`data/raw/README.md` "알려진 변환 손실": hwp5txt 가 제33조 ② 제6호, 제59조의 표 내용을 빠뜨림). → **보스 결정 필요** (아래 "하지 말 것" 참고). 코드로 할 수 있는 범위는 "표가 빠졌음을 감지해 그 조항을 리포트에서 '원문 불완전'으로 표시"까지로 본다.
3. **재실행 편차의 원인 조사** (set-v2 2회 실행, Recall·Precision 최대 0.08 차이). 원인 가설과 근거를 정리하고, 담당 파일 안에서 고칠 수 있는 것만 고친다.

**담당 파일**
- `src/contract_review/retrieval.py`
- `src/contract_review/nodes/retrieve_standard.py`
- `src/contract_review/nodes/parse.py`
- `src/contract_review/textnorm.py`
- `tests/test_retrieval.py` (기존), `tests/test_retrieval_*.py` (새 파일)
- `tests/test_robustness.py` (기존)
- `docs/progress/ws-b-fix.md`

**완료 기준**
- 고친 문제마다 **회귀 테스트** (고치기 전 실패, 고친 뒤 통과를 PR 에 기록), FR-25~ ID.
- 효과는 **ws-d 의 set-v3** 로 잰다. 검색 개선은 `eval_retrieval.py` 의 hit@3(API 없음)로 잴 수 있으니 set-v3 와 set-v2 의 전후 값을 PR 에 적는다. LLM 이 필요한 측정은 승인 요청만.
- set-v1·set-v2 hit@3 가 1.00 에서 떨어지지 않는다 (떨어지면 그대로 보고).
- `make test` · `make lint` 통과.

**하지 말 것**
- `data/raw/` 의 변환본(`ftc_standard_subcontract_construction_*.txt`) 수정·덮어쓰기. HWP 를 다시 변환해야 고칠 수 있다면 **멈추고 보고**: 새 변환 파일 위치, 필요한 도구(허용 의존성 밖이면 승인 필요), 표준 인덱스가 바뀌어 기존 결과와 비교가 깨지는 점을 PR 에 적는다.
- 편차 원인이 `llm.py`·`nodes/llm_judge.py`(담당 밖)에 있으면 고치지 말고 근거와 수정안을 PR 에 적는다.
- set-v3 계약서·재작성 문장을 보고 튜닝하기 (측정에만 사용). 개발은 set-v1·v2·public 과 직접 만든 테스트 문장으로.
- 기존 구성(baseline/v1/v2) 결과 파일 수정.

**의존 관계**
- 선행: **ws-d 합침** (set-v3 필요). ws-c 와 동시 진행 가능 (담당 파일 겹치지 않음).
- ws-c C1(관련성 검증)과 목표가 일부 겹친다(잘못된 근거 조항). ws-b 는 **검색 단계**, ws-c 는 **판정 뒤 검증 노드**로 나눈다.

---

### ws-c-advance · 고도화 (기능마다 작은 PR 로 따로)
기능마다 브랜치와 PR 을 따로 만든다: `ws-c-advance-c1`, `-c2`, `-c3`, `-c4`. 앞 PR 을 연 뒤 다음 기능을 시작한다(같은 파일 `graph.py` 를 고치므로 순서대로, 앞 PR 이 합쳐진 뒤 `git merge origin/main`).

**공통 원칙: 기존 구성(baseline/v1/v2)의 동작은 바꾸지 않는다.** 새 노드는 `PipelineConfig` 의 새 플래그(기본 꺼짐) 또는 새 구성 이름으로만 켠다. 그래야 `FROZEN_NUMBERS` 와 기존 결과가 계속 같은 의미를 가진다.

- **C1 관련성 검증 (FR-30)**: 인용이 실존하는지만이 아니라 그 지적을 실제로 뒷받침하는지 반론하는 검증 노드(Red Team 방식). 판정(위험도·카테고리)은 바꾸지 않고 '재검토 필요' 표시만 단다. 추가 LLM 호출 수를 PR 에 적는다.
- **C2 사람 검토 기록 (FR-31)**: 각 지적에 검토자가 수락/거절/메모를 남기는 저장 구조(`feedback.py`, 저장 위치는 gitignore 된 `outputs/feedback/`)와, 기록을 모아 오탐 패턴(카테고리·조항·규칙/LLM 별 거절률)을 집계하는 `scripts/feedback_report.py`. 화면 연결은 ws-f.
- **C3 리스크 금액 표시 (FR-32)**: 금액 계산은 원문에 근거가 있는 것만(예: 계약금액과 원문 비율이 둘 다 있는 경우). 근거가 없으면 `TODO(source-needed)`. 현재 `data/thresholds.yaml` 의 TODO 2건(지체상금 요율, 하자담보 기간 상한)은 채우지 않는다.
- **C4 운영 로그 (FR-33, NFR-14)**: 실행마다 처리 시간·토큰·LLM 호출 수·지적 수·버린 지적 수를 JSONL(`outputs/telemetry/`, gitignore)로 남기고 요약 리포트를 만드는 `scripts/ops_report.py`.

**담당 파일**
- `src/contract_review/graph.py`
- `src/contract_review/nodes/` 아래 **새** 노드 파일: `nodes/relevance_check.py`(C1), `nodes/risk_amount.py`(C3)
- `src/contract_review/feedback.py`(C2), `src/contract_review/telemetry.py`(C4) (새 파일)
- `scripts/feedback_report.py`(C2), `scripts/ops_report.py`(C4) (새 파일)
- 새 테스트: `tests/test_relevance_check.py`, `tests/test_feedback.py`, `tests/test_risk_amount.py`, `tests/test_telemetry.py`
- `docs/progress/ws-c-advance.md` (C1~C4 공용, 기능별 절)
- **(추가 제안, 보스 확인 필요)** C1·C3 의 결과를 리포트에 담으려면 `src/contract_review/schemas.py`(`Finding` 에 **기본값 있는 선택 필드만 추가**, 기존 JSON 호환)와 `src/contract_review/nodes/report.py`(표시 한 줄)가 필요하다. 승인 전에는 필요한 변경을 PR 에 적고 멈춘다. 승인되면 2차에서 이 두 파일은 ws-c 만 고친다.
- **(추가 제안)** C3 의 금액 근거는 `data/thresholds.yaml` 을 고치지 않고 새 파일 `data/amount_basis.yaml`(항목마다 원문 인용·출처)로 둔다.

**완료 기준**
- 기능마다: 새 테스트(FakeLLM) 통과, `make test` · `make lint` 통과, 기존 구성의 FakeLLM 결과가 바뀌지 않음을 테스트로 확인 (예: v2 의 finding 목록이 전과 같다).
- C1: 실제 인용이지만 엉뚱한 근거(set-public case 1 같은 유형)를 '재검토 필요'로 표시하는 FakeLLM 테스트.
- C2: 저장 → 다시 읽기 → 집계가 왕복되는 테스트, 집계 리포트 예시(가짜 기록으로).
- C3: 근거 없는 항목은 금액 대신 `TODO(source-needed)` 가 나오는 테스트.
- C4: 한 번 실행에 JSONL 1줄, 필드 누락 없음 테스트. 키·계약서 본문은 로그에 남기지 않는다.
- 효과를 주장하려면 set-v3 로 (LLM 이 필요하면 승인 요청만).

**하지 말 것**
- 기존 노드 파일(`nodes/llm_judge.py`, `nodes/rule_check.py` 등)과 `llm.py`, `retrieval.py` 수정. 판정 결과(위험도·카테고리) 변경.
- 법령 수치를 기억으로 쓰기, 금액 계산식에 근거 없는 요율 넣기.
- 로그·검토 기록을 레포에 커밋하기 (`outputs/` 는 gitignore).
- 승인 없이 실제 LLM 호출.

**의존 관계**
- 선행: 1차 합침 (특히 ws-d: 측정 기준). ws-b 와 동시 진행 가능.
- C2 → **ws-f** 의 선행 조건.
- C4 의 로그 형식은 ws-h(Databricks 집계)가 읽을 수 있으므로, 형식을 PR 에 표로 적는다.

---

### ws-f-demo · 데모 (ws-c 의 C2 가 합쳐진 뒤)
**목표**
- API 키 없이 도는 **데모 모드**: 저장된 결과로 리포트를 보여주고 실제 LLM 호출은 꺼둔다. 화면에 **'데모 모드, 합성 계약서'** 표시와 기존 고지(DISCLAIMER).
- C2 검토 기록을 Streamlit 화면에 연결 (지적마다 수락/거절 버튼, 메모).
- 무료 배포처(Streamlit Community Cloud, Hugging Face Spaces 등)의 배포 설정과 절차를 문서로. **실제 배포는 보스가 자기 계정으로** 한다. 비밀정보는 절대 넣지 않는다.
- README 첫 화면용 스크린샷 자리 안내와 30초 시연 GIF 촬영 대본.

**담당 파일**
- `app/streamlit_app.py`
- `src/contract_review/demo.py` (새 파일)
- `.streamlit/` (새 폴더, 예: `config.toml`. **secrets.toml 은 만들지 않는다**)
- `docs/demo/` (새 폴더: 배포 절차, GIF 대본, README 에 넣을 스크린샷 문단 제안)
- 새 테스트 `tests/test_demo.py`
- `docs/progress/ws-f-demo.md`
- 데모가 읽는 저장 결과는 기존 `eval/results/sample_report/`(읽기만). 새 저장 결과가 필요하면 새 폴더 `data/demo/` 에만 둔다 (추가 제안).

**완료 기준**
- `LLM_PROVIDER` 설정과 무관하게 데모 모드에서는 LLM 클라이언트가 만들어지지 않음을 테스트로 확인.
- 데모 화면에 '데모 모드, 합성 계약서'와 법률 자문 아님 고지가 보인다 (스크린샷을 PR 에 첨부).
- 수락/거절이 C2 저장 구조로 기록되고 다시 열면 보인다.
- `docs/demo/DEPLOY.md`: 배포처별 절차, 필요한 설정 파일, 비밀정보가 필요 없다는 확인. **루트에 놓아야 하는 파일**(예: `requirements.txt`, Hugging Face Spaces 의 README 머리말)은 담당 밖이므로 내용만 문서에 적고 보스 결정으로 남긴다. HF Spaces 머리말은 현재 `README.md` 와 충돌하므로 별도 배포용 위치를 제안한다.
- `make test` · `make lint` 통과.

**하지 말 것**
- README 직접 수정 (ws-a 담당이었고 지금은 공유 파일) — 스크린샷 문단은 `docs/demo/` 에 제안으로.
- API 키·토큰을 파일·설정·스크린샷에 넣기. 실제 배포 실행.
- 데모 화면에 성능 숫자를 새로 쓰기 (쓴다면 `FROZEN_NUMBERS` 그대로).

**의존 관계**
- 선행: **C2(`ws-c-advance-c2`) 합침.** C1·C3 가 합쳐져 있으면 '재검토 필요'·금액도 화면에 표시할 수 있으나 필수 아님.

---

## 4. 선택 작업

### ws-h-databricks · Databricks Free Edition 노트북
**목표** — 평가 데이터 적재와 결과 집계를 Databricks 노트북으로 옮긴 버전. 실행은 보스 계정에서 보스가 하고, 결과 캡처를 넣을 자리를 만든다.

**담당 파일**
- `databricks/` (새 폴더: 노트북 소스, 적재·집계 코드, `README.md`)
- `docs/databricks/` (새 폴더: 실행 절차, 캡처 자리 `images/`)
- `docs/progress/ws-h-databricks.md`

**완료 기준**
- 노트북이 레포의 `eval/results/*.json`, `eval/cases*/*.yaml` 을 **읽기만** 해서 적재하고, 집계 결과가 `FROZEN_NUMBERS` 의 값과 같게 나오는지 확인하는 셀이 있다 (예: set-v2 citation_accuracy, 토큰 비율).
- 실행 절차 문서에 보스가 할 일(계정, 업로드, 실행 순서)과 캡처를 넣을 위치가 있다.
- 레포 쪽 `make test` · `make lint` 통과 (노트북 파일이 lint 대상이면 형식 맞춤).

**하지 말 것**
- 토큰·워크스페이스 URL 등 계정 정보 커밋. 이 세션이나 워크트리에서 Databricks 실행.
- 레포의 Python 패키지 의존성 추가 (노트북 안에서만 필요한 것은 노트북에 적고 PR 에 알림).
- 결과를 노트북에서 다시 계산해 기존 숫자를 바꾸기.

**의존 관계**
- 선행 없음 (언제든). ws-c C4 가 합쳐져 있으면 운영 로그 집계도 추가할 수 있다.

---

## 5. 담당 파일 겹침 확인

같은 시기에 동시에 도는 작업끼리 담당 파일이 겹치면 안 된다. 1차(ws-a·d·g·e)와 2차(ws-b·c, 이후 ws-f), 선택(ws-h) 기준.

| 파일·폴더 | a-fit | d-eval | g-interview | e-review | b-fix | c-advance | f-demo | h-databricks |
|---|---|---|---|---|---|---|---|---|
| `README.md` | ✍️ | | | | | | 제안만 | |
| `docs/01_brief.md`, `docs/07_final_report.md` | ✍️ | | | | | | | |
| `docs/interview/` | | | ✍️ | | | | | |
| `docs/reviews/` (커밋 안 함) | | | | ✍️ | | | | |
| `docs/progress/<브랜치>.md` | 자기 것 | 자기 것 | 자기 것 | | 자기 것 | 자기 것 | 자기 것 | 자기 것 |
| `data/synthetic_v3/`, `eval/cases_v3/`, `data/public_contracts/` | | ✍️ | | | 측정만 | 측정만 | | |
| `scripts/make_paraphrase.py`, `scripts/repeat_eval.py` (+제안 `run_public_contracts.py`) | | ✍️ | | | | | | |
| `src/contract_review/eval.py` | | ✍️ (데이터셋 옵션만) | | | | | | |
| `tests/test_dataset_v3.py`, `test_repeat_eval.py`, `test_public_contracts.py` | | ✍️ | | | | | | |
| `src/contract_review/retrieval.py`, `nodes/retrieve_standard.py`, `nodes/parse.py`, `textnorm.py` | | | | | ✍️ | | | |
| `tests/test_retrieval.py`, `tests/test_retrieval_*.py`, `tests/test_robustness.py` | | | | | ✍️ | | | |
| `src/contract_review/graph.py` | | | | | | ✍️ | | |
| `nodes/relevance_check.py`, `nodes/risk_amount.py`, `feedback.py`, `telemetry.py` | | | | | | ✍️ | | |
| `scripts/feedback_report.py`, `scripts/ops_report.py`, 새 테스트 4개 | | | | | | ✍️ | | |
| `schemas.py`, `nodes/report.py` (추가 제안, 승인 시) | | | | | | ✍️ | | |
| `data/amount_basis.yaml` (추가 제안) | | | | | | ✍️ | | |
| `app/streamlit_app.py`, `src/contract_review/demo.py`, `.streamlit/`, `docs/demo/`, `tests/test_demo.py`, `data/demo/` | | | | | | | ✍️ | |
| `databricks/`, `docs/databricks/` | | | | | | | | ✍️ |
| **담당 없음 (공유, 수정 금지)**: `PROGRESS.md`, `CLAUDE.md`, `AGENTS.md`, `Makefile`, `pyproject.toml`, `.github/`, `Dockerfile`, `docs/02~06`, `docs/SPEC.md`, `docs/PLAN.md`, `docs/FROZEN_NUMBERS.md`, `docs/citation_audit.md`, `data/thresholds.yaml`, `config.py`, `llm.py`, `standards.py`, `thresholds.py`, `citation_check.py`, `eval_retrieval.py`, `nodes/split_clauses.py`, `nodes/rule_check.py`, `nodes/llm_judge.py`, 기존 `scripts/*`, 기존 테스트(위에 적힌 것 제외) | – | – | – | – | – | – | – | – |
| **수정·삭제 금지 (데이터)**: `data/raw/`, `data/synthetic/`, `data/synthetic_v2/`, `data/public_cases/`, `eval/cases/`, `eval/cases_v2/`, `eval/cases_public/`, `eval/results/` 기존 파일 | – | – | – | – | – | – | – | – |

**결론: 같은 시기에 도는 작업끼리 ✍️ 가 겹치는 행은 없다.** 확인한 경계 사례:
- `README.md`: ws-a(1차)만 쓴다. ws-f(2차)는 `docs/demo/` 에 제안만 하고, 2차 이후 "v1.1 이후 결과" 추가는 보스 승인 뒤 별도 문서 PR.
- `eval.py` 는 ws-d 만. ws-b·ws-c 는 2차에서 `eval.py` 를 고치지 않고 실행만 한다. C4 운영 로그는 `graph.py` 에서 남기므로 `eval.py` 수정이 필요 없다.
- `graph.py` 는 ws-c 만. ws-b 의 검색 수정은 `retrieve_standard.py` 안에서 끝나야 하고, `graph.py` 연결 변경이 필요하면 멈추고 보고.
- ws-c 의 C1~C4 는 모두 `graph.py` 를 고치므로 **동시에 돌리지 않고 순서대로** 한다.
- ws-c 가 `graph.py` 를 바꾸면 담당 없는 기존 테스트 `tests/test_judge_and_graph.py` 가 깨질 수 있다. 깨지면 고치지 말고 보고 (공통 규칙).
- `schemas.py`·`nodes/report.py` 는 지금 담당 없음. ws-c 에 주는 것은 **보스 승인 시에만**, 그 경우 2차 동안 ws-b·ws-f 는 이 두 파일을 고치지 않는다.
- `nodes/parse.py`(ws-b)와 `app/streamlit_app.py`(ws-f): 업로드 화면이 parse 를 호출하지만 ws-f 는 parse 를 고치지 않는다.
