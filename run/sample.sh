# run in serial
nohup bash -c '
uv run python -u run_sampling_data.py -p 70 -m "GRAPE_AVG"  -l 0.005 -i 3  &> logs/grape_avg.log && 
uv run python -u run_sampling_data.py -p 70 -m "GRAPE_AVG"  -l 0.005 -i 4  &> logs/grape_avg.log && 
uv run python -u run_sampling_data.py -p 70 -m "GRAPE_AVG"  -l 0.005 -i 5  &> logs/grape_avg.log && 
uv run python -u run_sampling_data.py -p 70 -m "GRAPE_AVG"  -l 0.05 -i 4  &> logs/grape_avg.log && 
uv run python -u run_sampling_data.py -p 70 -m "GRAPE_AVG"  -l 0.05 -i 5  &> logs/grape_avg.log  
 '  &> logs/batch1.log &
