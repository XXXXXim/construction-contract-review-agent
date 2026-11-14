# 고정 숫자 (FROZEN NUMBERS)

> SK에코플랜트 지원서(자기소개서)에 인용한 숫자와 그 출처다. 기준 버전은 태그 **`v1.0-application`** (커밋 `3496a64`).
> **이 파일과 README 의 해당 숫자는 바꾸지 않는다.** 새 결과는 README 의 "v1.1 이후 결과" 섹션에만 추가한다.
> 2026-11-14, 저장된 결과 파일에서 다시 계산해 모두 일치함을 확인했다 (불일치 0건).
> 실제 LLM 결과는 전부 `claude-sonnet-5-5`, 2026-11-08 실행(1차)이다. 11/10 2차 실행값은 "참고"에만 적는다.

| # | 자소서 표현 | 값 | 출처 파일 | 필드·계산 |
|---|---|---|---|---|
| 1 | 조문 인용 오류 baseline 40건 → v1·v2 0건 | baseline **40** (set-v1 15 + set-v2 24 + set-public 1), v1 **0**, v2 **0** | `docs/citation_audit.md` 표의 **오류** 열. 이 표는 `scripts/audit_citations.py` 가 아래 11/08 결과 9개로 만든 것 | 11/08 결과 JSON 에는 `citation_errors` 필드가 없다(FR-19 이전 실행). 검사기를 11/08 파일만 대상으로 다시 돌려 15·24·1 / 0·0·0 재현 |
| 2 | 근거 조항 정확도 0% → 100% | baseline **0.0**, v1 **1.0**, v2 **1.0** | `eval/results/2026-11-08_{baseline,v1,v2}_anthropic-claude-sonnet-5-5_set-v2.json` | `citation_accuracy` (정답 표준 조항 번호가 `standard_ref` 에 있는 TP 비율). set-v1 결과(`2026-11-08_*_anthropic-claude-sonnet-5-5.json`)도 0.0 / 1.0 / 1.0 |
| 3 | 정답 라벨 24개 (계약서 3부) | 라벨 **24** = 8 + 8 + 8, 계약서 **3** | `eval/cases_v2/synthetic_contract_0{1,2,3}.yaml` (`cases` 목록), set-v1 `eval/cases/` 도 같은 구성 | 결과 JSON 의 `labels: 24`, `contracts: 3` 과 일치 |
| 4 | 규칙 기준값 14개 | 규칙이 쓰는 기준값 **14** (전체 항목 18 = 값 있음 16 + `TODO(source-needed)` 2) | `data/thresholds.yaml` | `contract_review.thresholds.rule_thresholds()` 길이 14, `load_thresholds()` 길이 18 |
| 5 | 오탐 3건의 원인이 평가셋 생성기 버그 | set-v1 v2 오탐 **3건** = `제11조/design_change` × 계약서 3부. set-v2(참조 수정판)에서 같은 오탐 **0건** | `eval/results/2026-11-08_v2_anthropic-claude-sonnet-5-5.json` → `per_contract.*.false_positives`. 비교: `..._set-v2.json` 의 `false_positives` 비어 있음 | 원인 분석: `PROGRESS.md` 2026-11-08 (재번호 시 본문 조문 참조 미수정, 내부 참조 58개 중 54개 어긋남). 회귀 테스트 `test_dataset_v2_has_consistent_cross_references_and_v1_keeps_the_bug` |
| 6 | 입력 토큰 약 5.9배 | v2 **257,866** ÷ baseline **43,560** = **5.92** (v1 257,660 ÷ 43,560 = 5.92) | `eval/results/2026-11-08_{baseline,v2}_anthropic-claude-sonnet-5-5_set-v2.json` | `avg_input_tokens` (계약서당). set-v1 은 252,158 ÷ 42,887 = 5.88 |

## 해석할 때 주의 (면접 대비)
- **#1 의 40건은 세 평가셋 합계다.** set-v1 과 set-v2 는 같은 변형을 담은 계약서(조문 참조만 수정)라 서로 독립된 표본이 아니다.
  2차 실행(11/10) 기준으로 다시 세면 set-v2 baseline 은 23건이다 (`2026-11-10_baseline_..._set-v2.json` 의 `citation_errors`). `scripts/audit_citations.py` 는 최신 결과를 쓰므로 지금 재생성하면 합계가 39 가 된다. 그래서 `docs/citation_audit.md` 는 재생성하지 않는다.
- **#2 의 baseline 0% 는** baseline 이 근거로 계약서 쪽 조문 번호나 기억한 번호를 적었기 때문이다 (예: 정답 표준 제40조 대신 "표준하도급계약서 제34조"). 검색이 없는 구성이라 정답 번호를 볼 수 없다는 구조 차이도 함께 설명해야 한다.
- **#5 의 3건은 v2 기준이다.** 같은 결과에서 v1 은 오탐 4건이고, 그중 3건이 같은 `제11조` 자기 참조다.
- 자소서 초안에 Recall·Precision 을 쓴다면 1차 값(Recall 0.92 → 1.00, Precision 0.81 → 1.00)이다. 2차 실행에서 v2 Precision 은 0.92 였다 (README 첫 화면 표에 1차·2차 병기).

## 다시 확인하는 방법
```bash
.venv/bin/python -c "import json; r=json.load(open('eval/results/2026-11-08_v2_anthropic-claude-sonnet-5-5_set-v2.json')); print(r['citation_accuracy'], r['labels'], r['contracts'], r['avg_input_tokens'])"
.venv/bin/python -c "from contract_review.thresholds import rule_thresholds, load_thresholds; print(len(rule_thresholds()), len(load_thresholds()))"
```
