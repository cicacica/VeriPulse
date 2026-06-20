#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# det 0.01, 0.05, 0.10, 0.20
# err 0.05, 0.1
#
# Core 3x3 grid: CRAB/GRAPE
#for D in 0.0 0.05 0.10 0.2; do
#  for err in 0.0 0.05 0.1; do
#    oarsub -l /nodes=1/core=24,walltime=150:0:0 -p "host like 'small%'" \
#           "$(pwd)/sweep.sh $D $err"
#  done
#done

# Stress test
#oarsub -l /nodes=1/core=48,walltime=24:0:0 -p "host like 'big%'" \
#       "$(pwd)/sweep.sh 0.20 0.0"
#

# lambda sweep 
# dummyless [0.005, 0.01 , 0.025, 0.04 , 0.05 , 0.06 , 0.1  , 0.5  , 5.   ])
# dummyyes  [0.0005,0.005,0.01,0.025,0.026,0.05,0.1,0.5,5]
for lam in 0.005 0.01 0.025 0.04 0.05 0.06 0.1 0.5 5.0 ; do
    oarsub -l /nodes=1/core=64,walltime=10:0:0 -p "host like 'tall%'" -n "lamb warm grape dummy yes" \
           "$(pwd)/sweep.sh $lam"
done
