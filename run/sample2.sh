# run in serial
nohup bash -c '
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.05 -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.05 -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.05 -e 0.1 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.2 -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.2 -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.2 -e 0.1 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.1 -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.1 -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "CRAB" -l 0.026 -det 0.1 -e 0.1 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.2 -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.2 -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.2 -e 0.1 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.1 -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.1 -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.1 -e 0.1 -n 5   &> logs/grape_avg.log &&  
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.05 -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.05 -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026 -det 0.05 -e 0.1 -n 5   &> logs/grape_avg.log  
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026  -e 0.0 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026  -e 0.05 -n 5   &> logs/grape_avg.log && 
uv run python -u run_warm_start.py -p 40 -dum -s "GRAPE" -l 0.026  -e 0.1 -n 5   &> logs/grape_avg.log  
 '  &> batch.log &
