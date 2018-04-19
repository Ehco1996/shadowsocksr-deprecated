#!/usr/bin/python
# -*- coding: UTF-8 -*-
from utils import importloader

g_config = None


def load_config():
    global g_config
    g_config = importloader.loads(
        ['configs.userapiconfig', 'config.sapiconfig'])


def get_config():
    return g_config


load_config()
