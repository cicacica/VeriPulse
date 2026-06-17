# run in serial
# [0.06,0.04,5,0.5,0.1,0.05,0.01,0.025,0.005,0.0005
# 0.01, 0.05, 0.10, 0.20

nohup bash -c '
uv run python -u run_sampling_data.py -p 120 -m "GRAPE_AVG" -l 0.05 -det 0.01 -i 2 &> logs/grape_avg.log  
 '  &> logs/batch1.log &
