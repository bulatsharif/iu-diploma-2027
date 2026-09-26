#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

exec .venv/bin/vllm serve models/Qwen3-8B \
  --served-model-name qwen3-8b \
  --dtype bfloat16 \
  --no-enable-prefix-caching \
  --per-request-spec-decode-metrics summary
