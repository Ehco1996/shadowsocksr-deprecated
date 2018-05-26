# shadowsockesr
ssr mod version for django-sspanel

# dev 分支正在开发，线上请用master分支！

### 版本说明

改版ssr在原版的基础上加了点小功能
并且只对django——sspanel进行支持和维护

>django-sspanel 是我开发的面板
>项目地址：https://github.com/Ehco1996/django-sspanel

* 节点流量日志上报
* 节点在线ip统计
* webapi mode  （推荐）
* ehcomod mode （直连mysql）
* 兼容Python2/3

### 安装教程


* 克隆项目到本地

`git clone https://github.com/Ehco1996/shadowsocksr.git`

* 安装依赖

```sh
wget https://bootstrap.pypa.io/get-pip.py

python get-pip.py

pip install -r requirements.txt
```

* 配置接口

```sh
# 进入脚本文件夹
cd scripts

#初始化配置
bash initcfg.sh

#编辑配置文件
nano userapiconfig.py

API_INTERFACE 的选择
    ehcomod  数据直连，选择使用这个需要单独配置 usermysql.json 里面就是你主站数据库的配置
    webapi   走http协议的web接口 选择使用这个需要配置 web token

Token 的配置
    这里要填写你django-sspanel里 admin user 的用户名和对应的端口

WEBAPI_URL 设置
    api请求的地址 应为你的域名/api/
    例如: https:www.xxx.com/api

NODE_ID
    节点id 必须唯一

UPDATE_TIME = 75
    节点上报数据的时间间隔,60~75为佳
```

**下面是默认配置（走webapi）**

```python
# API_INTERFACE = 'ehcomod'  # ehcomod <谜之屋专用>
API_INTERFACE = 'webapi'  # webapi <谜之屋专用>
UPDATE_TIME = 10

# Webapi token
TOKEN = "you own token"

WEBAPI_URL = 'http://127.0.0.1:8000/api'
NODE_ID = 1

# Mysql
MYSQL_CONFIG = 'configs/usermysql.json'

# MUJSON API
MUAPI_CONFIG = 'usermuapi.json'
SERVER_PUB_ADDR = '127.0.0.1'  # mujson_mgr need this to generate ssr link
```

### 基本使用命令

**测试是否联通:**

`python server.py`

**日志方式启动:**

`./logrun.sh`

**关闭服务:**

`./stop.sh`

**重启节点:**

`./restart.sh`
