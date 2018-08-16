#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# __Author__: WangGuobao(guobao.v@gmail.com)
# __Date__: 2018/8/7 0007

"""
获取相关目录路径
"""
import os,sys

project_dir = os.path.dirname(os.path.abspath(__file__))

def add_path(path):
    if path not in sys.path:
        sys.path.insert(0, path)

# # Add lib to PYTHONPATH
# view_path = osp.join(project_dir, "core", "view") # resource_rc
# add_path(view_path)