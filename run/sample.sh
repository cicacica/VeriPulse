# run in serial
# [0.06,0.04,5,0.5,0.1,0.05,0.01,0.025,0.005,0.0005

nohup bash -c '
uv run python -u run_sampling_data.py -p 70 -dum -m "GRAPE_AVG"  -l 0.04 -n 5  &> logs/grape_avg.log  &&
uv run python -u run_sampling_data.py -p 70 -dum -m "GRAPE_AVG"  -l 0.01 -n 5  &> logs/grape_avg.log  &&
uv run python -u run_sampling_data.py -p 70 -dum -m "GRAPE_AVG"  -l 0.025 -n 5  &> logs/grape_avg.log  
 '  &> logs/batch1.log &
