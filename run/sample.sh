# run in serial
# [0.06,0.04,5,0.5,0.1,0.05,0.01,0.025,0.005,0.0005
# 0.01, 0.05, 0.10, 0.20

#lambdas = [0.1, 0.05, 0.01]
#tslots_list = [30,40,50,60,70,80]
# lambdas40: [0.005,0.01,0.025,0.04,0.05,0.06,0.1,0.5]
#
#nohup
bash -c '
uv run python run_warm_start.py -s GRAPE -p 30 -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s CRAB -p 30  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s GRAPE -p 50  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s CRAB -p 50  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s GRAPE -p 60  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s CRAB -p 60  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s GRAPE -p 70  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s CRAB -p 70  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s GRAPE -p 80  -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log &&  
uv run python run_warm_start.py -s CRAB -p 80 -det 0.0 -e 0.0 -n 5 -l 0.05 &> logs/wgrape.log  
'&> logs/batch1.log &
