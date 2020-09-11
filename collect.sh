#!/bin/bash
set -e
for env in venv*; do
    . $env/bin/activate
    numactl -C0 ./httpbench.py --csv all http://localhost:8999/bucket/small-10mb.npy > results/$env-10mb.txt
done
