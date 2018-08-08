#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# __Author__: WangGuobao(guobao.v@gmail.com)
# __Date__: 2018/7/25 0025

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

"""
设置
"""

from easydict import EasyDict
import json
import os

import init_path

# 初始化
__C = EasyDict()
__C.DEFAULT = EasyDict()
__C.CUSTOM = EasyDict()

# 外部引用
motion_det_cfg = __C

# 默认设置
__C.DEFAULT.HISTORY = 600
__C.DEFAULT.THRESHOLD = 100
__C.DEFAULT.HAS_DET_SHADOW = 0  # False
__C.DEFAULT.BACK_RATIO = 0.85
__C.DEFAULT.BLUR_SIZE = 5
__C.DEFAULT.HAS_FORE_PROC = 2  # True
__C.DEFAULT.ERODE_SHAPE = 2
__C.DEFAULT.AREA_SIZE = 500
__C.DEFAULT.UN_DET_SIZE = 10
# 自定义设置
__C.CUSTOM.HISTORY = 600
__C.CUSTOM.THRESHOLD = 100
__C.CUSTOM.HAS_DET_SHADOW = 0
__C.CUSTOM.BACK_RATIO = 0.85
__C.CUSTOM.BLUR_SIZE = 5
__C.CUSTOM.HAS_FORE_PROC = 2
__C.CUSTOM.ERODE_SHAPE = 2
__C.CUSTOM.AREA_SIZE = 500
__C.CUSTOM.UN_DET_SIZE = 10


def init_cfg(cfg=None):
    # debug
    write_cfg(cfg)


def write_cfg(cfg, path=os.path.join(init_path.project_dir, "conf/settings.json")):
    with open(path, "w") as f:
        f.write(json.dumps(cfg, sort_keys=True, indent=4, separators=(',', ': ')))


def read_cfg(path=os.path.join(init_path.project_dir, "conf/settings.json")):
    with open(path, "r") as f:
        cfg = json.loads(f.read())
    return cfg


def update_cfg(cfg=None):
    cfg.update(read_cfg())

# init_cfg(motion_det_cfg)

