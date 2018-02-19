import base64
# Config
API_INTERFACE = 'ehcomod'  # ehcomod <谜之屋专用>
# API_INTERFACE = 'webapi'  # webapi <谜之屋专用>
UPDATE_TIME = 60
SERVER_PUB_ADDR = '127.0.0.1'  # mujson_mgr need this to generate ssr link


# django-sspanel 管理员账号
USERNAME = 'ehco'
# django-sspanel 理员端口
PORT = 2345
# Webapi token
TOKEN = base64.b64encode(
    bytes('{}+{}'.format(USERNAME, PORT), 'utf8')).decode()

# api网址 ： 你的域名+/api
WEBAPI_URL = 'http://127.0.0.1:8000/api'
# 节点id
NODE_ID = 1

# Mysql
MYSQL_CONFIG = 'usermysql.json'

# MUDJSNO API
MUAPI_CONFIG = 'usermuapi.json'
