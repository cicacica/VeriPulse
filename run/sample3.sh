# run in serial
#lam40_dummyless = np.sort([0.005,0.01,0.025,0.04,0.05,0.06,0.1,0.5,5])
#lam40_dummyyes = np.sort([0.0005,0.005,0.01,0.025,0.026,0.05,0.1,0.5,5])
# det 0.05, 0.10, 0.2
# err   0.05, 0.10
#
nohup bash -c '
uv run python -u run_warm_start.py -p 40 -s "CRAB" -dum -l 0.026 -det 0.1 -e 0.05  -n 5   &> logs/wgrape_avg.log && 
uv run python -u run_warm_start.py -p 40 -s "CRAB" -dum -l 0.026 -det 0.1 -e 0.1  -n 5   &> logs/wgrape_avg.log && 
uv run python -u run_warm_start.py -p 40 -s "CRAB" -dum -l 0.026 -e 0.1  -n 5   &> logs/wgrape_avg.log && 
uv run python -u run_warm_start.py -p 40 -s "CRAB" -dum -l 0.026 -e 0.05  -n 5   &> logs/wgrape_avg.log && 
uv run python -u run_warm_start.py -p 40 -s "GRAPE" -dum -l 0.026 -e 0.05  -n 5   &> logs/wgrape_avg.log && 
uv run python -u run_warm_start.py -p 40 -s "GRAPE" -dum -l 0.026 -e 0.1  -n 5   &> logs/wgrape_avg.log 
 '  &> batch.log &
