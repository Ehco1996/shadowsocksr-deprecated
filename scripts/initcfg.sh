#!/bin/bash

chmod +x *.sh
chmod +x ../shadowsocks/*.sh
cd ../configs/
cp -n apiconfig.py userapiconfig.py
cp -n config.json user-config.json
cp -n mysql.json usermysql.json

