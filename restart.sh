#!/bin/bash
cd `dirname $0`
bash stop.sh
bash logrun.sh

echo "`date '+%Y-%m-%d %T'` node restart" >> restart.log