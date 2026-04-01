# run in serial
 nohup bash -c '
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.1 -i 3  &> p40l01-3.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.1 -i 4  &> p40l01-4.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.01 -i 2  &> p40l001-2.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.01 -i 3  &> p40l001-3.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.01 -i 4  &> p40l001-4.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.01 -i 5  &> p40l001-5.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.05 -i 2  &> p40l005-2.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.05 -i 3  &> p40l005-3.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.05 -i 4  &> p40l005-4.log &&
 uv run python -u run_sampling_data.py -p 40 -m "GRAPE_AVG" -l 0.05 -i 5  &> p40l005-5.log &&
 uv run python -u run_sampling_data.py -p 120 -m "GRAPE_AVG" -l 0.1 -n 5  &> p120l01.log 
 '  &> batch1.log &
