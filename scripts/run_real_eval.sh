#!/usr/bin/env bash
# 실제 LLM 으로 baseline / v1 / v2 평가 + 비교표 + 샘플 리포트 1건 (M4·M5 DoD).
# 사용: LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... bash scripts/run_real_eval.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
: "${LLM_PROVIDER:?LLM_PROVIDER 를 anthropic 또는 openai 로 지정하세요}"
export LLM_CACHE="${LLM_CACHE:-1}"   # 같은 프롬프트 재호출 비용 0 (재실행 대비)

echo "== 1/5 연결 확인 (호출 1회)"
$PY -c "
from contract_review.config import load_settings
from contract_review.llm import get_llm
llm = get_llm(load_settings())
text, tin, tout = llm.complete('한 단어로만 답하세요: 대한민국의 수도는?')
print(f'  {llm.name}: {text.strip()[:30]!r} (토큰 {tin}/{tout})')
"

for cfg in baseline v1 v2; do
  echo "== 평가: $cfg"
  $PY -m contract_review.eval --config "$cfg" | grep -E "Recall|Precision|Citation|처리 시간|실패|잘린|⚠️|저장" || true
done

echo "== 비교표"
$PY -m contract_review.eval --compare --llm-filter "$LLM_PROVIDER"

echo "== 샘플 리포트 1건 (v2, 캐시 재사용)"
$PY - <<'PYEOF'
from pathlib import Path
from contract_review.graph import Pipeline
from contract_review.nodes.report import write_report
out = Pipeline("v2").run("data/synthetic/synthetic_contract_01.txt")
md, js = write_report(out["report"], Path("eval/results/sample_report"))
print(f"  {md}\n  {js}")
PYEOF
echo "끝. 결과: eval/results/"
