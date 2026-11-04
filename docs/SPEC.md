# SPEC: 건설 하도급 계약 검토 에이전트

> 상태: **M0 초안 (보스 승인 대기)**. 카테고리별 판정 기준값은 M1에서 `data/raw/` 원문을 파싱한 뒤 출처와 함께 확정한다. 이 문서에는 법령 수치를 기억으로 적지 않는다.

## 1. 문제 정의
- 원청의 계약 검토 담당자가 하도급 계약서를 받으면, 표준계약서와 하도급법에 비해 **불리하거나 벗어난 조항**을 사람이 조항마다 대조해야 한다.
- 이 도구는 그 대조를 자동화해서 **의심 조항, 대응 표준 조항, 근거 원문 인용**을 위험도순으로 보여준다.
- 사용자: (1차) 원청 계약 검토 담당자, (2차) 중소 하도급 업체
- 이 도구는 **법률 자문이 아닌 검토 보조 도구**다.

## 2. 파이프라인
```
PDF → parse → split_clauses → retrieve_standard → rule_check → llm_judge → report
```
LangGraph `StateGraph` 하나로 구현한다. 노드마다 입력과 출력을 pydantic 모델로 정의한다 (`src/contract_review/schemas.py`).

| 노드 | 입력 | 출력 | 비고 |
|---|---|---|---|
| `parse` | `pdf_path` | `ParsedDocument(doc_id, text, pages)` | `pypdf`. 스캔 PDF(OCR)는 비범위 |
| `split_clauses` | `ParsedDocument` | `list[Clause]` | "제n조(제목)" 패턴. `clause_id`(예: `제12조`), `title`, `text` |
| `retrieve_standard` | `Clause` | `list[RetrievedRef]` (top-k) | BM25 + 임베딩 하이브리드. 임베딩 불가 시 BM25 단독 |
| `rule_check` | `Clause`, `RetrievedRef` | `list[RuleHit]` | 숫자 판정(일수, 비율)을 LLM 없이 결정적으로. 기준값은 원문 추출값 + 출처 |
| `llm_judge` | `Clause`, refs, rule hits | `list[Finding]` | 구조화 출력. `evidence_quote` 검증 실패 시 해당 finding 폐기 |
| `report` | `list[Finding]` | `ReviewReport` (MD + JSON) | 위험도순 정렬, 근거 인용, 면책 고지 |

## 3. 입력 스키마
- 텍스트 레이어가 있는 PDF 1개 (하도급 계약서). 텍스트 파일(.txt)도 허용 (합성 평가셋용).
- 기준 문서(`data/raw/`):
  - 공정거래위원회 건설업종 표준하도급계약서 (주 비교 대상)
  - 국토교통부 민간건설공사 표준도급계약서 (보조 비교 대상)
  - 하도급거래 공정화에 관한 법률 (기준값, 강행 규정 근거)

## 4. 출력 스키마
### Finding
| 필드 | 타입 | 설명 |
|---|---|---|
| `clause_id` | str | 검토 대상 계약서의 조항 ID (예: `제12조`) |
| `category` | `Category` enum | 아래 5절 카테고리 중 하나 |
| `risk_level` | `high` \| `medium` \| `low` \| `none` | 아래 6절 기준 |
| `contract_text` | str | 계약서 해당 조항 원문 (발췌) |
| `standard_ref` | str | 대응 표준 조항 참조 (예: `표준하도급계약서 제n조`) |
| `deviation_summary` | str | 무엇이 어떻게 다른지 한국어 1~3문장 |
| `evidence_quote` | str | 기준 문서에 **실제로 있는 문자열**. 코드로 부분문자열 검증(공백 정규화 후), 실패 시 finding 폐기 |
| `source` | `rule` \| `llm` | 판정 주체 |

### ReviewReport
`contract_id`, `generated_at`, `config`, `findings`(위험도순), `stats`(조항 수, 처리 시간, 토큰 수), `disclaimer`.
산출물: `report.md`(한국어 마크다운), `report.json`.

## 5. 검토 카테고리 (초기안)
`Category` enum 값과 의미. 각 카테고리의 대응 표준 조항과 기준값은 **M1 원문 파싱 후 출처와 함께 아래 표를 채운다.**

| enum | 카테고리 | 판정 방식 | 대응 표준 조항 / 기준값 / 출처 |
|---|---|---|---|
| `payment_deadline` | 대금 지급 기한 | 규칙(일수) + LLM | TODO(source-needed) |
| `delay_penalty` | 지체상금 | 규칙(요율, 상한) + LLM | TODO(source-needed) |
| `defect_liability` | 하자담보 책임 | 규칙(기간) + LLM | TODO(source-needed) |
| `design_change` | 설계변경과 대금 조정 | 규칙(기한 일수) + LLM | TODO(source-needed) |
| `termination` | 계약 해제·해지 | LLM | TODO(source-needed) |
| `unfair_special_terms` | 부당 특약·책임 전가 | LLM | TODO(source-needed) |
| `damages_cap` | 손해배상 한도 | LLM | TODO(source-needed) |
| `other` | 기타 | LLM | – |

## 6. 위험도 판정 기준
| risk_level | 기준 |
|---|---|
| `high` | 하도급법 등 법령 기준을 명백히 위반하거나(규칙 판정), 하도급인에게 일방적 책임·권리 포기를 지우는 조항 |
| `medium` | 표준계약서 대비 하도급인에게 불리하게 기한·비율·범위가 변경되었으나 법령 위반은 불명확 |
| `low` | 표현·절차 차이로 해석 여지가 있는 경미한 편차 |
| `none` | 표준과 실질적으로 같음 (리포트에는 미표시, 평가에서는 "지적 안 함"으로 취급) |

규칙 레이어가 판정한 항목은 LLM 판정보다 우선한다 (같은 `clause_id`+`category`면 rule 결과 유지).

## 7. 평가 (요약, 상세는 PLAN M2·M5)
- 정답 라벨: `eval/cases/*.yaml` — `contract_id, clause_id, category, expected_risk, injected_change`
- 합성 계약서 3개 × 변형 7~10개 (라벨 20개 이상) + 변형 없는 정상 조항 (오탐 측정용). 시드 고정.
- 매칭 기준: 예측 finding(`risk_level != none`)과 라벨이 `(contract_id, clause_id, category)` 일치하면 TP.

| 지표 | 정의 |
|---|---|
| Recall | TP / 주입 변형 수 |
| Precision | TP / 지적한 finding 수 (`risk_level != none`) |
| Citation accuracy | TP 중 `standard_ref`가 정답 표준 조항을 가리킨 비율 |
| Retrieval hit@3 | 변형 조항마다 정답 표준 조항이 검색 top-3에 든 비율 |
| 처리 시간 / 토큰 | 계약서당 평균 처리 시간(초), 입력+출력 토큰, 추정 비용 |

비교 config: `baseline`(전체 조항을 LLM 한 번에) / `v1`(분할 + BM25 + LLM) / `v2`(하이브리드 + 규칙 + 근거 검증).

## 8. 설정
환경변수 (`.env.example`): `LLM_PROVIDER`(`fake`|`openai`|`anthropic`), `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER`(`none`|`openai`). `fake`는 결정적 응답으로 API 키 없이 테스트를 통과시킨다.

## 9. 비범위 (Non-goals)
- 로그인·회원 관리, DB 서버, 배포 인프라, 화면 꾸미기
- OCR (스캔 PDF)
- 멀티 에이전트 구조 확장 (단일 그래프로 끝낸다)
- 법률 자문, 조항 자동 수정안 생성
- 실제(비공개) 계약서 데이터, SK에코플랜트 내부 자료
