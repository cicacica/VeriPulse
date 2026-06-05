#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# 0.01, 0.05, 0.10, 0.20
for D in 0.01 0.05 0.1 0.2; do
  oarsub -l /nodes=1/core=48,walltime=24:0:0 \
         -p "host like 'big%'" \
         "$(pwd)/sweep_det.sh $D"
done
