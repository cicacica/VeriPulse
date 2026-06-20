#!/bin/bash
# run_warm_start_grid.sh
# ----------------------
# Run warm-start GRAPE_AVG over full grid in serial.
# Each (source, detuning, drive_error, id) combination runs sequentially.

SOURCE="CRAB"          # GRAPE or CRAB
NUM_TSLOTS=40
LAM=0.05               # 0.05 for dummyless, 0.026 for dummyyes
NUM_SAMPLES=5           # ids 1..N
DUMMY=""                # set to "-dum" for dummy qubits
VERBOSE=""              # set to "-v" for verbose

DETUNINGS=(0.0 0.05 0.10 0.20)
DRIVE_ERRORS=(0.0 0.05 0.10)

mkdir -p logs

nohup bash -c '
for det in '"${DETUNINGS[*]}"'; do
    for err in '"${DRIVE_ERRORS[*]}"'; do
        for i in $(seq 1 '"$NUM_SAMPLES"'); do
            echo "=== SOURCE='"$SOURCE"'  det=$det  err=$err  id=$i ===" 
            uv run python -u run_warm_start.py \
                -s '"$SOURCE"' \
                -p '"$NUM_TSLOTS"' \
                -det $det \
                -e $err \
                -i $i \
                -l '"$LAM"' \
                '"$DUMMY"' \
                '"$VERBOSE"' \
                &>> logs/warm_start_${det}_${err}.log &&
            echo "done: det=$det err=$err id=$i"
        done
    done
done
' &> logs/warm_start_batch.log &

echo "Batch started. PID=$!"
echo "Tail logs with: tail -f logs/warm_start_batch.log"
