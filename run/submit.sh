#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# det 0.01, 0.05, 0.10, 0.20
# err 0.05, 0.1
#
# Core 3x3 grid: GRAPE
for D in 0.0 0.05 0.10 0.2; do
  for err in 0.0 0.05 0.10; do
    oarsub -l /nodes=1/core=24,walltime=48:0:0 -p "host like 'big%'" \
           "$(pwd)/sweep.sh $D $err"
  done
done

# Stress test
#oarsub -l /nodes=1/core=48,walltime=24:0:0 -p "host like 'big%'" \
#       "$(pwd)/sweep.sh 0.20 0.0"
