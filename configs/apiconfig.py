import base64
# Config

# API_INTERFACE = 'ehcomod'  # ehcomod <谜之屋专用> # webapi
API_INTERFACE = 'webapi'  # ehcomod <谜之屋专用> # webapi
UPDATE_TIME = 60


# Webapi token
USERNAME = 'ehco'
PORT = 2345
try:
    TOKEN = base64.b64encode(
        bytes('{}+{}'.format(USERNAME, PORT), 'utf8')).decode()
except:
    TOKEN = base64.b64encode(
        bytes('{}+{}'.format(USERNAME, PORT))).decode()


WEBAPI_URL = 'http://127.0.0.1:8000/api'
NODE_ID = 1


# Mysql
MYSQL_CONFIG = 'usermysql.json'

# MUJSON API
MUAPI_CONFIG = 'usermuapi.json'
SERVER_PUB_ADDR = '127.0.0.1'  # mujson_mgr need this to generate ssr link
