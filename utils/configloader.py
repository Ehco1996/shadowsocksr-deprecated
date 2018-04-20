
# -*- coding: UTF-8 -*-
import os
import sys
from os.path import abspath, dirname

path = dirname((abspath(dirname(__file__))))
sys.path.insert(0, path)

from utils import importloader

g_config = None


def load_config():
    global g_config
    g_config = importloader.loads(
        ['configs.userapiconfig', 'config.apiconfig'])


def get_config():
    return g_config


def get_switch_rule():
    return importloader.load('utils.switch_rule')

load_config()