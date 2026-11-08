# 건설 하도급 계약 검토 보조 에이전트

> 하도급 계약서(PDF)를 **공정위 표준하도급계약서 · 국토부 표준도급계약서 · 하도급법**과 조항별로 대조해서,
> 수급사업자에게 **불리하거나 표준에서 벗어난 조항**을 **원문 근거 인용과 함께** 찾아내는 LangGraph 파이프라인.
> 공개 자료만으로 만든 개인 포트폴리오 프로젝트이며, 성능은 `make eval`의 측정값으로 증명한다.
>
> ⚠️ 법률 자문이 아닌 **검토 보조 도구**입니다. 모든 리포트에 같은 고지가 들어갑니다.

## 1. 문제

- 원청의 계약 검토 담당자는 하도급 계약서를 받으면 표준계약서·하도급법과 **조항마다 사람이 대조**해야 한다. 60개 조항 × 기준 문서 3종.
- 그중 상당수는 "60일이 90일로 바뀌었다"처럼 **숫자만 보면 되는 항목**인데도 LLM에 통째로 맡기면 근거 없이 그럴듯한 지적(환각)이 섞인다.
- 이 프로젝트는 (1) 조항 단위로 쪼개고, (2) 숫자형 항목은 **결정적 규칙**으로, 나머지는 LLM으로 판정하되, (3) LLM의 근거 인용이 **기준 문서에 실제로 있는 문장인지 코드로 검증**해서 환각 지적을 버린다.

## 2. 아키텍처

```mermaid
flowchart LR
    PDF[계약서 PDF/TXT] --> P[parse<br/>pypdf, layout 자동 전환]
    P --> S[split_clauses<br/>제n조 패턴, 별첨·부칙 분리]
    S --> R[retrieve_standard<br/>BM25 어절+2gram<br/>+ 선택적 임베딩 RRF]
    R --> RC[rule_check<br/>thresholds.yaml 14개 숫자 기준<br/>원문 인용 보유]
    RC --> J[llm_judge<br/>구조화 JSON<br/>evidence_quote 검증]
    J --> REP[report<br/>MD + JSON, 위험도순]
    STD[(data/raw<br/>표준하도급계약서 60조<br/>표준도급계약서 43조<br/>하도급법 65조)] --> R
    STD --> RC
    STD -. 인용 검증 .-> J
```

| 설정 | 조항 분할 | 검색 | 규칙 레이어 | 근거 검증 | 설명 |
|---|---|---|---|---|---|
| `baseline` | ✗ | ✗ | ✗ | ✗ | 계약서 전체를 LLM 한 번에 넣고 "불리한 조항 찾아줘" |
| `v1` | ✓ | BM25 | ✗ | ✗ | 조항별 LLM 판정 |
| `v2` | ✓ | BM25(+임베딩) | ✓ | ✓ | 규칙 우선 + LLM 인용 검증 |

핵심 설계 결정:
- **법령 수치는 기억으로 쓰지 않는다.** 규칙 기준값 14개는 전부 `data/thresholds.yaml`에 원문 인용과 함께 있고, `tests/test_thresholds.py`가 인용이 해당 조항 본문에 실제로 있는지 검증한다. 원문에 숫자가 없는 지체상금 요율·하자담보 기간 상한은 `TODO(source-needed)`로 두고 규칙에서 제외했다.
- **LLM 인용 검증**: `evidence_quote`는 LLM이 지목한 표준 조항 본문의 부분문자열(공백 무시)이어야 한다. 아니면 그 finding은 버리고 개수를 리포트에 적는다.
- **규칙 판정 우선**: 같은 조항·카테고리를 규칙과 LLM이 둘 다 지적하면 규칙 결과를 쓴다.
- `FakeLLM`(표준 top-1과 문장 diff) 덕분에 **API 키 없이 `make test` 47개가 통과**한다.

## 3. 평가

### 3.1 평가셋 (합성, `data/synthetic/`)
- 표준하도급계약서 본문을 바탕으로 `scripts/make_synthetic.py`가 **시드 고정**으로 생성 (실제 계약서 아님).
- 계약서 3개 × 변형 8개 = **라벨 24개**, 7개 카테고리. 변형 카탈로그 25종(기한 연장, 비율 변경, 면제 사유 삭제, 일방 권리화, 비용 전가 조항 추가 등).
- 검색이 조 번호만 보고 맞히지 못하게 정상 조항 10개를 삭제·재번호하고 당사자 명칭을 갑/을로 바꿨다. 정상 조항 42개/계약서가 오탐(false positive) 측정용.

### 3.2 지표
| 지표 | 정의 |
|---|---|
| Recall | 주입한 변형 중 잡아낸 비율 (`contract_id, clause_id, category` 일치) |
| Precision | 지적한 finding 중 라벨과 일치한 비율 |
| Citation accuracy | TP 중 `standard_ref`가 정답 표준 조항을 가리킨 비율 |
| Retrieval hit@3 | 변형 조항의 정답 표준 조항이 검색 top-3에 든 비율 |
| 처리 시간·토큰 | 계약서당 평균 |

### 3.3 결과

**검색 (BM25 단독, 150개 조항 질의)**: hit@1 0.98 / hit@3 **1.00**, 제목을 지운 hard 설정에서도 hit@3 1.00, 질의당 8 ms.
→ 합성 계약서가 표준 원문을 거의 그대로 복사하기 때문에 나온 값이다. 실제 계약서는 문장을 바꿔 쓰므로 이보다 낮을 것이다.

**파이프라인 비교: 실제 LLM `claude-sonnet-5-5`, 합성 계약서 3개, 정답 라벨 24개 (2026-11-08)**

평가셋은 두 버전이다. `set-v2`는 `set-v1`과 같은 시드·같은 변형 24개에서 **생성기 버그 하나**(재번호 후 본문 속 조문 참조를 안 고친 것)만 고친 수정판이다. set-v1 결과는 지우지 않고 나란히 둔다.

| 평가셋 | config | Recall | Precision | Citation | Risk match | 계약서당 입력 토큰 | 계약서당 출력 토큰 |
|---|---|---|---|---|---|---|---|
| **set-v2** | baseline (전체 1회 호출) | 0.92 (22/24) | 0.81 (22/27) | 0.00 | **0.73** | **43,560** | **7,368** |
| **set-v2** | v1 (조항 분할 + BM25 + LLM) | 0.92 (22/24) | 0.92 (22/24) | 1.00 | 0.59 | 257,660 | 14,423 |
| **set-v2** | **v2 (+ 규칙 레이어 + 근거 검증)** | **1.00 (24/24)** | **1.00 (24/24)** | **1.00** | 0.62 | 257,866 | 12,867 |
| set-v1 | baseline | 0.92 (22/24) | 0.81 (22/27) | 0.00 | 0.82 | 42,887 | 8,311 |
| set-v1 | v1 | 0.96 (23/24) | 0.85 (23/27) | 1.00 | 0.57 | 251,952 | 14,341 |
| set-v1 | v2 | 1.00 (24/24) | 0.89 (24/27) | 1.00 | 0.62 | 252,158 | 12,826 |

세 config 모두 LLM 호출 실패 0, JSON 파싱 실패 0, 응답 잘림 0. 원본: `eval/results/2026-11-08_compare_anthropic.md`

**무엇을 바꿨더니 무엇이 변했나 (set-v2 기준)**
- **baseline → v1 (조항 분할 + 검색):** 오탐 5 → 2건(precision 0.81 → 0.92), 근거 조항이 검색된 표준 원문으로 고정되어 citation 0.00 → 1.00. recall은 같다(0.92). 대가로 **입력 토큰 약 5.9배**.
- **v1 → v2 (규칙 레이어):** recall 0.92 → 1.00, precision 0.92 → 1.00. v1이 계약서 02·03에서 "증액분 지급 기한 15일 → 60일"을 `payment_deadline`으로 분류해 **누락 2 + 오탐 2**가 났는데, v2는 규칙이 숫자로 잡아 `design_change`로 판정했다.
  같은 변형을 v1은 set-v1 계약서 02에서는 맞게, set-v2 계약서 02에서는 다르게 분류했다. **LLM 분류는 주변 문맥에 따라 흔들리고, 규칙은 흔들리지 않는다.**
  (공정하게 말하면 "지급 기한"이라 `payment_deadline`도 틀린 해석은 아니다. 카테고리 경계가 모호한 라벨이다.)
- **근거 검증은 이번 평가에서 효과 0:** Sonnet이 낸 인용은 전부 원문에 실제로 있어서 버린 finding이 0건이다. v2의 개선은 **전부 규칙 레이어에서** 나왔다.

**set-v1 → set-v2 (생성기 버그 수정)의 효과**
- set-v1에서 v1·v2의 오탐 3건은 모두 "제11조가 제11조에 따른 서면을 인용"하는 자기 참조였다. 버그를 고친 set-v2에서는 **사라졌다** → 모델 오류가 아니라 평가셋 결함이었다는 가설이 확인됐다.

**baseline의 citation 0.00과 기억에 의존한 법령 인용**
- baseline은 표준 원문을 받지 않아서, **계약서 자기 조항 번호를 "표준하도급계약서 제34조"처럼 적거나** "지체상금 조항"처럼 번호 없이 적었다. 정답 표준 조항 번호를 댄 경우는 0건이다.
- baseline이 설명과 함께 적은 하도급법 인용 21건을 `data/raw` 원문과 대조하니 **5건이 조문·항 번호가 원문과 맞지 않았다.**
  예: "발주자로부터 대금 수령 후 15일 이내 지급"을 제13조 제6항이라 했지만 원문에서 그 내용은 제13조 제3항이고, 제6항은 어음 할인료 조항이다.
  (증액분의 15일 기준은 제16조 제4항 "추가금액을 지급받은 날부터 15일이 지난 후 … 이자"에 있다.)
  "부당한 감액 금지"를 제12조의3이라 했지만 원문 제12조의3은 "기술자료 제공 요구 금지 등"이다.
- 파이프라인(v1·v2)은 근거를 검색된 원문에서 가져오고, v2는 규칙의 기준값마다 원문 인용을 붙여 이런 오류가 구조적으로 생기지 않는다.

반드시 같이 적어야 하는 한계
- **표본이 작다.** 라벨 24개라 1건이 recall 4.2%p다. v1 → v2 차이는 set-v2에서 2건(recall)과 2건(오탐)이다.
- **위험도 판정(risk match)은 baseline이 가장 좋다**(set-v2 0.73, set-v1 0.82). 조항별 판정은 위험도를 낮게 매기는 경향이 있고, 규칙은 법령 출처면 high로 올려 라벨(medium)과 어긋난다.
- **처리 시간은 비교할 수 없다.** 캐시를 켠 채 돌려서 v1·v2는 같은 프롬프트의 저장된 답을 재사용했다. 캐시 없이 잰 값은 baseline뿐이다(set-v1 첫 실행 53초, set-v2 48초/계약서; set-v1 첫 실행 값은 커밋 `79af582`의 결과 파일에 있다).
- 비용(USD)은 단가를 기억으로 쓰지 않기 위해 기록하지 않았다. 토큰 수로 비교한다.

<details><summary>FakeLLM(결정적 diff 판정기) 결과: 하네스 동작 확인용, 성능 지표 아님</summary>

| 평가셋 | config | recall | precision | citation | risk_match |
|---|---|---|---|---|---|
| set-v1 | baseline | 0.00 | – | – | – |
| set-v1 | v1 | 0.92 | 1.00 | 1.00 | 0.59 |
| set-v1 | v2 | 0.92 | 1.00 | 1.00 | 0.45 |

FakeLLM은 글자 diff라 set-v2에서 재번호된 참조("제11조"→"제10조")까지 차이로 본다(precision 0.74). 실제 LLM은 그렇지 않았다.
</details>

재현:
```bash
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... bash scripts/run_real_eval.sh                 # set-v1
DATASET=v2 LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... bash scripts/run_real_eval.sh      # set-v2
```

## 4. 실행

```bash
make setup                      # .venv + 의존성
cp .env.example .env            # LLM_PROVIDER=fake|openai|anthropic, 키는 여기에만
make test                       # 키 없이 통과
make eval                       # v2 평가 → eval/results/
make run                        # Streamlit: PDF 업로드 → 리포트
docker build -t contract-review . && docker run -p 8501:8501 --env-file .env contract-review
```

실제 LLM 평가 팁: `LLM_CACHE=1`이면 같은 프롬프트 응답을 `.cache/llm/`에 저장해 재실행 비용이 0이 된다
(처리 시간 지표는 캐시를 끄고 잰다). 429/5xx는 `LLM_MAX_RETRIES`(기본 5)만큼 지수 백오프로 재시도하고,
그래도 실패한 호출은 그 조항만 빠지고 결과표에 "LLM 호출 실패" 수로 남는다.

CLI로 리포트 1건:
```bash
.venv/bin/python -c "from pathlib import Path; from contract_review.graph import Pipeline; from contract_review.nodes.report import write_report; o=Pipeline('v2').run('data/synthetic/synthetic_contract_01.txt'); print(write_report(o['report'], Path('outputs')))"
```

## 5. 알려진 한계

1. **합성 데이터의 한계**: 변형이 표준 원문의 문자열 치환이라 검색·diff가 실제보다 쉽다(hit@3 1.00). 실제 계약서(문장 재작성, 특약 별지, 표 형식)에서의 recall은 측정되지 않았다. 당사자 명칭 치환으로 생긴 조사 어색함(`갑가`, `을는`)도 두 평가셋에 남아 있다.
2. **원문에 없는 기준값**: 지체상금 요율(국가계약법 시행규칙), 하자담보책임기간 상한(건설산업기본법 시행령)은 원문이 없어 규칙에서 뺐다. 이 카테고리는 LLM 판정에만 의존한다.
3. **HWP 직접 파싱 미지원**: 표준하도급계약서는 1회 변환한 txt를 쓴다. 스캔 PDF(OCR)도 비범위.
4. **근거 검증은 "인용이 실존하는가"만 본다**: 인용이 실제로 그 지적을 뒷받침하는지(관련성)는 검증하지 않는다.
   문장부호 차이(ㆍ/·, 「」/"", 전각 괄호)와 "…" 생략 인용은 허용한다 (`textnorm.py`).
5. **규칙 레이어는 문형이 표준과 같을 때만 숫자를 읽는다**: 문장을 통째로 바꿔 쓴 계약서면 규칙은 조용히 빠지고 LLM 이 판정한다.
   오탐은 늘지 않지만, 합성셋의 규칙 적중률(숫자형 변형 12/12)은 실제 계약서에서 낮아질 것이다.
6. 실제 LLM 평가는 모델 1개(claude-sonnet-5-5), 합성 계약서 3개, 1회 실행 결과다. 반복 실행에 따른 편차는 재지 않았다.

## 6. 다음 단계

- 캐시 끄고 처리 시간 재측정
- 국가계약법 시행규칙·건설산업기본법 시행령 원문 추가 → 지체상금·하자담보도 규칙 판정
- 실제 공개 계약서 샘플(예: 공공기관 공고 첨부) 몇 건으로 합성셋 밖 성능 점검
- 2차 사용자(중소 하도급 업체)용: "이 조항이 왜 불리한지" 쉬운 설명 모드

## 7. 문서

| 문서 | 내용 |
|---|---|
| [`docs/07_final_report.md`](docs/07_final_report.md) | **최종 보고: 지표표, 가장 효과 컸던 개선, 한계, 면접 질문** |
| [`docs/01_brief.md`](docs/01_brief.md) ~ [`04_readiness.md`](docs/04_readiness.md) | 문제 정의 · 요구사항 · 설계(ADR) · 준비물 (사후 작성) |
| [`docs/05_traceability.md`](docs/05_traceability.md) | 요구사항 → 설계 → 구현 → 테스트 추적표 |
| [`docs/06_retro.md`](docs/06_retro.md) | 회고 (KPT) |
| [`PROGRESS.md`](PROGRESS.md) | 날짜별 진행 로그 |

## 8. 레포 구조

```
src/contract_review/
  schemas.py        pydantic (Clause, RetrievedRef, RuleHit, Finding, ReviewReport, EvalCase)
  nodes/            parse · split_clauses · retrieve_standard · rule_check · llm_judge · report
  retrieval.py      BM25 + 선택적 임베딩(RRF)
  thresholds.py     data/thresholds.yaml 로더
  standards.py      기준 문서 로더 + 인용 검증
  llm.py            provider 팩토리, FakeLLM
  graph.py          LangGraph StateGraph (baseline/v1/v2)
  eval.py           평가 하네스, 비교표
data/raw/           공개 원문 (하도급법, 표준하도급계약서, 표준도급계약서)
data/thresholds.yaml 규칙 기준값 (원문 인용 포함)
data/synthetic/     합성 계약서 (SYNTHETIC)
eval/cases/         정답 라벨   eval/results/  평가 결과
scripts/            make_synthetic.py · inspect_raw.py
app/streamlit_app.py
docs/               SPEC.md · PLAN.md · raw_clauses.md     PROGRESS.md  진행 로그
```
