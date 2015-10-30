#!/bin/bash
if [ "$#" -gt 1 ]; then
    echo "Usage: \"spawnceleryworkers.sh N\" where N is the number of parameters. N defaults to 1 if not specified."
fi
n_workers=1
if [ "$#" -eq 1 ]; then
    n_workers=$1
fi
for i in $(seq 1 $n_workers)
do
    celery worker --hostname=c$i.%h --app=app:celery --detach
done
