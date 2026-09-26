#!/usr/bin/env bash
# Usage: bash scripts/benchmark.sh [ru_100] [rps|concurrency] [value] [output_dir]
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

profile=${1:-ru_100}
mode=${2:-rps}
value=${3:-1}
output_dir=${4:-results/$(date -u +%Y%m%d_%H%M%S)_${profile}_${mode}_${value}}

case "$mode" in
  rps) load_args=(--request-rate "$value" --arrival-pattern poisson) ;;
  concurrency) load_args=(--concurrency "$value") ;;
  *) echo "Mode must be rps or concurrency" >&2; exit 2 ;;
esac

exec .venv/bin/aiperf profile \
  --model qwen3-8b --tokenizer models/Qwen3-8B \
  --url "${BENCHMARK_URL:-http://localhost:8000}" --endpoint-type chat \
  --input-file "data/prompts/${profile}.jsonl" --custom-dataset-type raw_payload \
  --streaming --use-server-token-count --per-chunk-usage \
  --warmup-duration 30 --benchmark-duration 120 \
  --artifact-dir "$output_dir" \
  "${load_args[@]}"
