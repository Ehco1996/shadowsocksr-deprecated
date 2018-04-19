#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import sys
from os.path import abspath, dirname

path = dirname((abspath(dirname(__file__))))
sys.path.insert(0, path)


def load(name):
    try:
        obj = __import__(name)
        reload(obj)
        return obj
    except:
        pass

    try:
        import importlib
        obj = importlib.import_module(name)
        importlib.reload(obj)
        return obj
    except:
        pass


def loads(namelist):
    for name in namelist:
        obj = load(name)
        if obj is not None:
            return obj
