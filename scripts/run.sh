#!/bin/bash
cd $(pwd)/..
python_ver=$(ls /usr/bin|grep -e "^python[23]\.[1-9]\+$"|tail -1)
eval $(ps -ef | grep "[0-9] ${python_ver} server\\.py m" | awk '{print "kill "$2}')
ulimit -n 512000
nohup ${python_ver} server.py >> /dev/null 2>&1 &

