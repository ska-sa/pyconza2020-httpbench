#!/bin/bash
set -e
for env in venv*; do
    . $env/bin/activate
    numactl -C0 ./httpbench.py --csv all http://localhost:8999/bucket/big-1gb.npy > results/$env-1gb.csv
done
