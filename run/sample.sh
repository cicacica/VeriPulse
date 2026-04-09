# run in serial
 nohup bash -c '
 uv run python -u run_sampling_data.py -p 60 -m "GRAPE_AVG" -l 0.05 -n 5  &> p60avg.log &&
 uv run python -u run_sampling_data.py -p 80 -m "GRAPE" -n 5  &> p80grape.log &&
 uv run python -u run_sampling_data.py -p 80 -m "CRAB" -n 5   &> p80crab.log && 
 uv run python -u run_sampling_data.py -p 80 -m "GRAPE_AVG" -l 0.1 -n 5  &> p80avg.log &&
 uv run python -u run_sampling_data.py -p 80 -m "GRAPE_AVG" -l 0.01 -n 5  &> p80avg.log &&
 uv run python -u run_sampling_data.py -p 80 -m "GRAPE_AVG" -l 0.05 -n 5  &> p80avg.log 
 '  &> batch1.log &
