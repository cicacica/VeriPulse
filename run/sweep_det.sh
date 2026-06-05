#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
#export OMP_NUM_THREADS=1
#export MKL_NUM_THREADS=1
#export OPENBLAS_NUM_THREADS=1
#export NUMEXPR_NUM_THREADS=1

cd "$(dirname "$0")"

DET="$1"

uv run python -u run_sampling_data.py -p 40 -m GRAPE_AVG -l 0.05 -n 5 -det $DET
