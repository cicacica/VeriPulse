#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
#export OMP_NUM_THREADS=1
#export MKL_NUM_THREADS=1
#export OPENBLAS_NUM_THREADS=1
#export NUMEXPR_NUM_THREADS=1

cd "$(dirname "$0")"

DET="$1"
ERR="$2"
#RID="$1"

#uv run python -u run_sampling_data.py -p 40 -m GRAPE_AVG -l 0.05 -det $DET -e $ERR -n 5
#uv run python -u run_sampling_data.py -p 40 -m CRAB -dum -l 0.026 -det $DET -e $ERR -n 5
uv run python -u run_sampling_data.py -p 40 -m GRAPE -dum -det $DET -e $ERR -n 5
