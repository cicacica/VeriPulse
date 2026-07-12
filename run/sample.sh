# run in serial
# [0.06,0.04,5,0.5,0.1,0.05,0.01,0.025,0.005,0.0005
# 0.01, 0.05, 0.10, 0.20

#lambdas = [0.1, 0.05, 0.01]
#tslots_list = [30,40,50,60,70,80]
# lambdas40: [0.005,0.01,0.025,0.04,0.05,0.06,0.1,0.5]
#
#nohup
bash -c '
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.005 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.01 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.025 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.04 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.05 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.06 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.1 -n 5 &> logs/grape_avg.log &&  
uv run python -u run_sampling_data.py -dum -p 40 -m "GRAPE_AVG" -l 0.5 -n 5 &> logs/grape_avg.log  
 '  
 #&> logs/batch1.log &
