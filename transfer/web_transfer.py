# -*- coding: UTF-8 -*-
'''
Web api for django-sspanel
'''

import sys
import time
import logging
import traceback
from datetime import datetime

import requests

import importloader
from server_pool import ServerPool
from configloader import load_config, get_config
from shadowsocks import common, shell, lru_cache, obfs


class EhcoApi(object):
    '''
    提供发送get/post的抽象类
    '''

    def __init__(self):
        self.session_pool = requests.Session()
        self.TOKEN = get_config().TOKEN
        self.WEBAPI_URL = get_config().WEBAPI_URL

    def getApi(self, uri):
        res = None
        try:
            payload = {'token': self.TOKEN}
            url = self.WEBAPI_URL+uri
            res = self.session_pool.get(url, params=payload, timeout=10)
            time.sleep(0.005)
            try:
                data = res.json()
            except Exception:
                if res:
                    logging.error('接口返回值格式错误: {}'.format(res.text))
                return []

            if data['ret'] == -1:
                logging.error("接口返回值不正确:{}".format(res.text))
                logging.error("请求头：{}".format(uri))
                return []
            return data['data']

        except Exception:
            import traceback
            trace = traceback.format_exc()
            logging.error(trace)
            raise Exception(
                '网络问题，请保证api接口地址设置正确！当前接口地址：{}'.format(self.WEBAPI_URL))

    def postApi(self, uri, raw_data={}):
        res = None
        try:
            payload = {'token': self.TOKEN}
            url = self.WEBAPI_URL+uri
            res = self.session_pool.post(
                url, params=payload, json=raw_data, timeout=10)
            time.sleep(0.005)
            try:
                data = res.json()
            except Exception:
                if res:
                    logging.error('接口返回值格式错误: {}'.format(res.text))
                return []
            if data['ret'] == -1:
                logging.error("接口返回值不正确:{}".format(res.text))
                logging.error("请求头：{}".format(uri))
                return []
            return data['data']
        except Exception:
            import traceback
            trace = traceback.format_exc()
            logging.error(trace)
            raise Exception(
                '网络问题，请保证api接口地址设置正确！当前接口地址：{}'.format(self.WEBAPI_URL))

    def close(self):
        self.session_pool.close()


class WebTransfer(object):
    def __init__(self):
        import threading
        self.event = threading.Event()
        self.start_time = time.time()
        self.cfg = {}
        self.load_cfg()  # 载入流量比例设置

        self.last_get_transfer = {}  # 上一次的实际流量
        self.last_update_transfer = {}  # 上一次更新到的流量（小于等于实际流量）
        self.force_update_transfer = set()  # 强制推入数据库的ID
        self.port_uid_table = {}  # 端口到uid的映射（仅v3以上有用）
        self.onlineuser_cache = lru_cache.LRUCache(timeout=60 * 30)  # 用户在线状态记录
        self.pull_ok = False  # 记录是否已经拉出过数据
        self.mu_ports = {}

    def load_cfg(self):
        import json
        config_path = get_config().MYSQL_CONFIG
        cfg = None
        with open(config_path, 'rb+') as f:
            cfg = json.loads(f.read().decode('utf8'))

        if cfg:
            self.cfg.update(cfg)

    def push_db_all_user(self):
        if self.pull_ok is False:
            return
        # 更新用户流量到数据库
        last_transfer = self.last_update_transfer
        curr_transfer = ServerPool.get_instance().get_servers_transfer()
        # 上次和本次的增量
        dt_transfer = {}
        for id in self.force_update_transfer:  # 此表中的用户统计上次未计入的流量
            if id in self.last_get_transfer and id in last_transfer:
                dt_transfer[id] = [self.last_get_transfer[id][0] - last_transfer[id]
                                   [0], self.last_get_transfer[id][1] - last_transfer[id][1]]

        for id in curr_transfer.keys():
            if id in self.force_update_transfer or id in self.mu_ports:
                continue
            # 算出与上次记录的流量差值，保存于dt_transfer表
            if id in last_transfer:
                if curr_transfer[id][0] + curr_transfer[id][1] - last_transfer[id][0] - last_transfer[id][1] <= 0:
                    continue
                dt_transfer[id] = [curr_transfer[id][0] - last_transfer[id][0],
                                   curr_transfer[id][1] - last_transfer[id][1]]
            else:
                if curr_transfer[id][0] + curr_transfer[id][1] <= 0:
                    continue
                dt_transfer[id] = [curr_transfer[id][0], curr_transfer[id][1]]

            # 有流量的，先记录在线状态
            if id in self.last_get_transfer:
                if curr_transfer[id][0] + curr_transfer[id][1] > self.last_get_transfer[id][0] + self.last_get_transfer[id][1]:
                    self.onlineuser_cache[id] = curr_transfer[id][0] + \
                        curr_transfer[id][1]
            else:
                self.onlineuser_cache[id] = curr_transfer[id][0] + \
                    curr_transfer[id][1]

        self.onlineuser_cache.sweep()

        update_transfer = self.update_all_user(dt_transfer)  # 返回有更新的表
        for id in update_transfer.keys():  # 其增量加在此表
            if id not in self.force_update_transfer:  # 但排除在force_update_transfer内的
                last = self.last_update_transfer.get(id, [0, 0])
                self.last_update_transfer[id] = [
                    last[0] + update_transfer[id][0], last[1] + update_transfer[id][1]]
        self.last_get_transfer = curr_transfer
        for id in self.force_update_transfer:
            if id in self.last_update_transfer:
                del self.last_update_transfer[id]
            if id in self.last_get_transfer:
                del self.last_get_transfer[id]
        self.force_update_transfer = set()

    def del_server_out_of_bound_safe(self, last_rows, rows):
        # 停止超流量的服务
        # 启动没超流量的服务
        # 停止等级不足的服务
        try:
            switchrule = importloader.load('switchrule')
        except Exception as e:
            logging.error('load switchrule.py fail')
        cur_servers = {}
        new_servers = {}
        allow_users = {}
        mu_servers = {}
        config = shell.get_config(False)
        for row in rows:
            try:
                allow = switchrule.isTurnOn(
                    row) and row['enable'] == 1 and row['u'] + row['d'] < row['transfer_enable']
            except Exception as e:
                allow = False

            port = row['port']
            passwd = common.to_bytes(row['passwd'])
            if hasattr(passwd, 'encode'):
                passwd = passwd.encode('utf-8')
            cfg = {'password': passwd}
            if 'id' in row:
                self.port_uid_table[row['port']] = row['id']

            read_config_keys = ['method', 'obfs', 'obfs_param', 'protocol', 'protocol_param',
                                'forbidden_ip', 'forbidden_port', 'speed_limit_per_con', 'speed_limit_per_user']
            for name in read_config_keys:
                if name in row and row[name]:
                    cfg[name] = row[name]

            merge_config_keys = ['password'] + read_config_keys
            for name in cfg.keys():
                if hasattr(cfg[name], 'encode'):
                    try:
                        cfg[name] = cfg[name].encode('utf-8')
                    except Exception as e:
                        logging.warning(
                            'encode cfg key "{}" fail, val "{}"'.format(name, cfg[name]))

            if port not in cur_servers:
                cur_servers[port] = passwd
            else:
                logging.error(
                    'more than one user use the same port [{}]'.format(port,))
                continue

            if 'protocol' in cfg and 'protocol_param' in cfg and common.to_str(cfg['protocol']) in obfs.mu_protocol():
                if '#' in common.to_str(cfg['protocol_param']):
                    mu_servers[port] = passwd
                    allow = True

            if allow:
                if port not in mu_servers:
                    allow_users[port] = cfg

                cfgchange = False
                if port in ServerPool.get_instance().tcp_servers_pool:
                    relay = ServerPool.get_instance().tcp_servers_pool[port]
                    for name in merge_config_keys:
                        if name in cfg and not self.cmp(cfg[name], relay._config[name]):
                            cfgchange = True
                            break
                if not cfgchange and port in ServerPool.get_instance().tcp_ipv6_servers_pool:
                    relay = ServerPool.get_instance(
                    ).tcp_ipv6_servers_pool[port]
                    for name in merge_config_keys:
                        if (name in cfg) and ((name not in relay._config) or not self.cmp(cfg[name], relay._config[name])):
                            cfgchange = True
                            break

            if port in mu_servers:
                if ServerPool.get_instance().server_is_run(port) > 0:
                    if cfgchange:
                        logging.info(
                            'db stop server at port [{}] reason: config changed: {}'.format(port, cfg))
                        ServerPool.get_instance().cb_del_server(port)
                        self.force_update_transfer.add(port)
                        new_servers[port] = (passwd, cfg)
                else:
                    self.new_server(port, passwd, cfg)
            else:
                if ServerPool.get_instance().server_is_run(port) > 0:
                    if config['additional_ports_only'] or not allow:
                        logging.info(
                            'db stop server at port [{}]'.format(port,))
                        ServerPool.get_instance().cb_del_server(port)
                        self.force_update_transfer.add(port)
                    else:
                        if cfgchange:
                            logging.info(
                                'db stop server at port [{}] reason: config changed: {}'.format(port, cfg))
                            ServerPool.get_instance().cb_del_server(port)
                            self.force_update_transfer.add(port)
                            new_servers[port] = (passwd, cfg)

                elif not config['additional_ports_only'] and allow and port > 0 and port < 65536 and ServerPool.get_instance().server_run_status(port) is False:
                    self.new_server(port, passwd, cfg)

        for row in last_rows:
            if row['port'] in cur_servers:
                pass
            else:
                logging.info(
                    'db stop server at port [{}] reason: port not exist'.format(row['port']))
                ServerPool.get_instance().cb_del_server(row['port'])
                self.clear_cache(row['port'])
                if row['port'] in self.port_uid_table:
                    del self.port_uid_table[row['port']]

        if len(new_servers) > 0:
            from shadowsocks import eventloop
            self.event.wait(eventloop.TIMEOUT_PRECISION +
                            eventloop.TIMEOUT_PRECISION / 2)
            for port in new_servers.keys():
                passwd, cfg = new_servers[port]
                self.new_server(port, passwd, cfg)

        logging.debug('db allow users {} \nmu_servers {}'.format(
            allow_users, mu_servers))
        for port in mu_servers:
            ServerPool.get_instance().update_mu_users(port, allow_users)

        self.mu_ports = mu_servers

    def clear_cache(self, port):
        if port in self.force_update_transfer:
            del self.force_update_transfer[port]
        if port in self.last_get_transfer:
            del self.last_get_transfer[port]
        if port in self.last_update_transfer:
            del self.last_update_transfer[port]

    def new_server(self, port, passwd, cfg):
        protocol = cfg.get(
            'protocol', ServerPool.get_instance().config.get('protocol', 'origin'))
        method = cfg.get(
            'method', ServerPool.get_instance().config.get('method', 'None'))
        obfs = cfg.get(
            'obfs', ServerPool.get_instance().config.get('obfs', 'plain'))
        logging.info('db start server at port [{}] pass [{}] protocol [{}] method [{}] obfs [{}]'.format(
            port, passwd, protocol, method, obfs))
        ServerPool.get_instance().new_server(port, cfg)

    def cmp(self, val1, val2):
        if type(val1) is bytes:
            val1 = common.to_str(val1)
        if type(val2) is bytes:
            val2 = common.to_str(val2)
        return val1 == val2

    def pull_db_all_user(self):
        '''
        拉取符合要求的用户信息
        '''
        global webapi
        # api = EhcoApi()
        node_id = get_config().NODE_ID

        # 获取节点流量比例信息
        nodeinfo = webapi.getApi('/nodes/{}'.format(node_id))
        if not nodeinfo:
            logging.warn(
                '没有查询到满足要求的节点，请检查自己的node_id!,或者该节点流量已经用光,当前节点ID:{}'.format(node_id))
            rows = []
            return rows

        # 流量比例设置
        node_info_keys = ['traffic_rate', ]
        node_info_dict = {}
        for column in range(len(nodeinfo)):
            node_info_dict[node_info_keys[column]] = nodeinfo[column]
        self.cfg['transfer_mul'] = float(node_info_dict['traffic_rate'])

        # 获取符合条件的用户信息
        data = webapi.getApi('/users/nodes/{}'.format(node_id))
        if not data:
            rows = []
            logging.warn(
                '没有查询到满足要求的user，请检查自己的node_id!')
            return rows
        rows = data
        return rows

    def update_all_user(self, dt_transfer):
        global webapi
        node_id = get_config().NODE_ID
        update_transfer = {}

        # 用户流量上报
        data = []
        for id in dt_transfer.keys():
            if dt_transfer[id][0] == 0 and dt_transfer[id][1] == 0:
                continue
            data.append({'u': dt_transfer[id][0], 'd': dt_transfer[
                        id][1], 'user_id': self.port_uid_table[id]})
            update_transfer[id] = dt_transfer[id]
        if len(data) > 0:
            tarffic_data = {'node_id': node_id,
                            'data': data}
            webapi.postApi('/traffic/upload', tarffic_data)

        # 节点在线ip上报
        node_online_ip = ServerPool.get_instance().get_servers_ip_list()
        ip_data = {}
        for k, v in node_online_ip.items():
            ip_data[self.port_uid_table[k]] = v
        webapi.postApi('/nodes/aliveip',
                       {'node_id': node_id,
                        'data': ip_data})

        # 节点人数上报
        alive_user_count = len(self.onlineuser_cache)
        online_data = {'node_id': node_id,
                       'online_user': alive_user_count}
        webapi.postApi('/nodes/online', online_data)

        return update_transfer

    def load(self):
        import os
        try:
            return os.popen("cat /proc/loadavg | awk '{ print $1\" \"$2\" \"$3 }'").readlines()[0]
        except:
            return '系统不支持负载检测'

    def uptime(self):
        return round(time.time() - self.start_time)

    @staticmethod
    def del_servers():
        for port in [v for v in ServerPool.get_instance().tcp_servers_pool.keys()]:
            if ServerPool.get_instance().server_is_run(port) > 0:
                ServerPool.get_instance().cb_del_server(port)
        for port in [v for v in ServerPool.get_instance().tcp_ipv6_servers_pool.keys()]:
            if ServerPool.get_instance().server_is_run(port) > 0:
                ServerPool.get_instance().cb_del_server(port)

    @staticmethod
    def thread_db(obj):
        import socket
        import time
        global db_instance
        global webapi
        timeout = 60
        socket.setdefaulttimeout(timeout)
        last_rows = []
        db_instance = obj()
        ServerPool.get_instance()
        shell.log_shadowsocks_version()
        webapi = EhcoApi()

        try:
            import resource
            logging.info('current process RLIMIT_NOFILE resource: soft %d hard %d' %
                         resource.getrlimit(resource.RLIMIT_NOFILE))
        except:
            pass

        try:
            while True:
                load_config()
                db_instance.load_cfg()
                try:
                    db_instance.push_db_all_user()
                    rows = db_instance.pull_db_all_user()
                    if rows:
                        db_instance.pull_ok = True
                        config = shell.get_config(False)
                        for port in config['additional_ports']:
                            val = config['additional_ports'][port]
                            val['port'] = int(port)
                            val['enable'] = 1
                            val['transfer_enable'] = 1024 ** 7
                            val['u'] = 0
                            val['d'] = 0
                            if "password" in val:
                                val["passwd"] = val["password"]
                            rows.append(val)
                    db_instance.del_server_out_of_bound_safe(last_rows, rows)
                    last_rows = rows
                except Exception as e:
                    trace = traceback.format_exc()
                    logging.error(trace)
                    # logging.warn('db thread except:%s' % e)
                if db_instance.event.wait(get_config().UPDATE_TIME) or not ServerPool.get_instance().thread.is_alive():
                    break
        except KeyboardInterrupt as e:
            pass
        db_instance.del_servers()
        ServerPool.get_instance().stop()
        db_instance = None

    @staticmethod
    def thread_db_stop():
        global db_instance
        db_instance.event.set()
