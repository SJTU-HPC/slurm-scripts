#!/bin/bash
set -e -o pipefail

while true
do
    python job-statistics-user.py -S `date +"%Y-%m-%dT%T" -d '24 hour ago'` -E `date +"%Y-%m-%dT%T"` -d 2>&1 | tee log/`date +"%Y-%m-%dT%T"`.log
    sleep 86400
done
