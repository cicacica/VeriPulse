# run in serial
nohup bash -c '
uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -dum -l 0.1 -n 5 &> logs/grape_avg.log 
 '  &> logs/batch1.log &
