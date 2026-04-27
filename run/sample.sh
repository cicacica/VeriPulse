# run in serial
nohup bash -c '
uv run python -u run_sampling_data.py -dum False -p 40 -m "GRAPE_AVG"  -l 5 -n 5 &> logs/grape_avg.log &&
uv run python -u run_sampling_data.py -dum False -p 40 -m "GRAPE_AVG"  -l 0.5 -n 5 &> logs/grape_avg.log &&
uv run python -u run_sampling_data.py -dum False -p 40 -m "GRAPE_AVG"  -l 0.025 -n 5 &> logs/grape_avg.log &&
uv run python -u run_sampling_data.py -dum False -p 40 -m "GRAPE_AVG"  -l 0.005 -n 5 &> logs/grape_avg.log &&
uv run python -u run_sampling_data.py -dum False -p 40 -m "GRAPE_AVG"  -l 0.0005 -n 5 &> logs/grape_avg.log 
 '  &> logs/batch1.log &
