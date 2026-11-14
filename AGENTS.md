# AGENTS.md: 건설 하도급 계약 검토 에이전트

> Claude Code 이외의 CLI 에이전트(Codex 등)용 규칙이다. Claude Code 는 `CLAUDE.md` 를 읽는다.
> 이 레포의 전체 규칙 원본은 `CLAUDE.md` 다. 아래 "병렬 작업 공통 규칙"은 `CLAUDE.md` 의 같은 섹션과 **내용이 같다.**

## 시작 순서
1. `docs/ORCA_HANDOFF.md` 에서 내 작업(ws-*)의 목표·담당 파일·완료 기준·하지 말 것을 읽는다.
2. `CLAUDE.md` 의 "절대 규칙" 1~9 와 이 파일의 병렬 규칙을 읽는다.
3. `PROGRESS.md` 의 마지막 기록과 `docs/FROZEN_NUMBERS.md` 를 읽는다.
4. `make setup && make test` 로 출발점이 초록인지 확인한 뒤 시작한다. 테스트는 API 키 없이 통과해야 한다 (`LLM_PROVIDER=fake`).

## 절대 규칙 요약 (원본: CLAUDE.md "절대 규칙")
- 법령 수치·조문은 기억으로 쓰지 않는다. `data/raw/` 원문에서 출처와 함께 가져오고, 없으면 `TODO(source-needed)`.
- 데이터를 지어내지 않는다. 합성 데이터는 `synthetic` 표시, 실제 문구는 출처(의결번호·쪽 등) 표시.
- SK에코플랜트 내부·비공개 정보를 쓰지 않는다. API 키는 환경변수로만, `.env` 커밋·키 출력 금지.
- 모든 리포트에 "법률 자문이 아닌 검토 보조 도구" 고지 (`contract_review.schemas.DISCLAIMER`).
- 허용 의존성 밖의 패키지는 추가 전에 이유를 말하고 승인받는다.
- 같은 테스트가 3번 연속 실패하면 멈추고 보고. 테스트 삭제·skip 으로 통과시키기 금지.
- 네트워크로 못 받는 것은 우회하지 말고 보고. 평가셋을 숫자에 맞춰 고치지 않는다.

## 명령어
`make setup` · `make test` · `make lint` (커밋 전 둘 다 통과) · 실제 LLM 을 쓰는 `make eval*` 는 보스 승인 없이 실행 금지.

## 병렬 작업 공통 규칙 (Orca 워크트리, 2026-11-14 보스 지시)
> `AGENTS.md` 의 같은 이름 섹션과 내용이 같아야 한다. 한쪽을 고치면 다른 쪽도 고친다.
> 작업별 목표·담당 파일·완료 기준은 `docs/ORCA_HANDOFF.md`. 자소서 인용 숫자는 `docs/FROZEN_NUMBERS.md`.

1. **작업마다 브랜치 하나.** 이름은 `docs/ORCA_HANDOFF.md` 표를 따른다. `main` 에 직접 push 금지. 끝나면 PR 만 열고, 합치는 것은 보스가 한다.
2. **담당 파일 밖은 수정 금지.** 꼭 필요하면 PR 설명에 이유를 적고 멈춘다.
3. `eval/results/` 의 기존 파일, `eval/cases*/` 의 기존 라벨, `data/raw/` 는 **수정·삭제 금지.** 새 평가는 새 파일로만.
4. `docs/FROZEN_NUMBERS.md` 의 숫자를 README 에서 바꾸지 않는다. 새 결과는 README 의 별도 섹션 **"v1.1 이후 결과"** 에만 추가한다.
5. **실제 LLM API 를 부르는 평가는 보스 승인 없이 실행 금지.** 테스트는 FakeLLM 으로. 승인이 필요하면 예상 호출 수와 토큰을 PR 에 적고 멈춘다.
6. 성능 개선을 주장하려면 **ws-d 가 만든 평가셋**으로 측정한다. 개발 중에 본 데이터로 잰 숫자는 '개선'이라고 쓰지 않는다.
7. 기존 규칙은 그대로: 법령 수치를 기억으로 쓰지 않기, 평가셋을 숫자에 맞춰 고치지 않기, 같은 테스트 3회 연속 실패 시 멈춤, 의존성 추가 전 승인.
8. **PR 설명 형식:** `## 바꾼 것` / `## 검증 방법과 결과` / `## 바꾸지 않은 것` / `## 남은 문제`.
9. 회사 관련 서술은 **공개 보도로 확인되는 것만.** 내부 정보나 특강 내용은 쓰지 않는다.

**공유 파일 충돌을 막기 위한 운영 규칙** (위 규칙을 지키기 위한 세부 사항)
- 진행 기록은 `PROGRESS.md` 가 아니라 **`docs/progress/<브랜치명>.md`** 에 쓴다 (작업별 담당 파일). `PROGRESS.md` 는 보스가 PR 을 합칠 때 정리한다.
- 새 요구사항은 `docs/02_requirements.md` 를 직접 고치지 않고 진행 기록 파일의 "요구사항 제안" 절과 PR 설명에 적는다. ID 는 `docs/ORCA_HANDOFF.md` 에서 작업마다 미리 나눈 범위를 쓴다 (겹침 방지). 테스트 docstring 에는 그 ID 를 적는다.
- `Makefile`, `pyproject.toml`, `.github/`, `CLAUDE.md`, `AGENTS.md`, `PROGRESS.md`, `docs/02~06`, `data/thresholds.yaml`, `src/contract_review/schemas.py` 처럼 **담당이 없는 공유 파일**은 고치지 않는다. 필요하면 PR 에 바꿀 내용을 적고 멈춘다 (단, 담당 표에 예외로 적힌 경우는 그 범위 안에서만).
- 기존 테스트 파일은 그 파일을 담당한 작업만 고친다. 다른 작업은 새 테스트 파일을 만든다. 기존 테스트가 깨지면 고치지 말고 원인을 보고한다.
- 작업 시작 전 `git fetch origin && git rebase origin/main` 으로 최신 main 위에서 시작한다. 첫 push 뒤에는 rebase 대신 `git merge origin/main` 을 쓴다 (force push 금지).

