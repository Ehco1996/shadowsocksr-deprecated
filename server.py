# -*- coding: utf-8 -*-
import time
import sys
import threading
import os

from shadowsocks import shell

from utils import server_pool
from transfer import web_transfer, db_transfer
from utils.configloader import get_config


class MainThread(threading.Thread):
    def __init__(self, obj):
        super(MainThread, self).__init__()
        self.daemon = True
        self.obj = obj

    def run(self):
        self.obj.thread_db(self.obj)

    def stop(self):
        self.obj.thread_db_stop()


def main():
    shell.check_python()
    if get_config().API_INTERFACE == 'mudbjson':
        thread = MainThread(db_transfer.MuJsonTransfer)
    elif get_config().API_INTERFACE == 'ehcomod':
        thread = MainThread(db_transfer.EhcoDbTransfer)
    elif get_config().API_INTERFACE == 'webapi':
        thread = MainThread(web_transfer.WebTransfer)
    else:
        print('请设置正确的接口模式!')
        sys.exit()
    thread.start()
    try:
        while thread.is_alive():
            thread.join(10.0)
    except (KeyboardInterrupt, IOError, OSError) as e:
        import traceback
        traceback.print_exc()
        thread.stop()


if __name__ == '__main__':
    main()
