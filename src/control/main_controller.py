#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# __Author__: WangGuobao(guobao.v@gmail.com)
# __Date__: 2018/7/9 0009

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

"""
窗口控制类
"""
from PyQt5.QtWidgets import QMainWindow

from src.view.ui_main import *
from src.model.main_mod import *
from src.view import resource_rc


class Window(QMainWindow, Ui_MainWindow):
    """
    窗口控制类，初始化窗口并且连接UI视图与逻辑模型
    """

    # todo: 应该用signal传递信号在本类中处理，而不是把view传入model处理?
    def __init__(self):
        # 构造函数
        super(Window, self).__init__()
        self._init_ui()

    def _init_ui(self):
        # 初始化UI（视图）
        self.setupUi(self)
        self._init_connect()

    def _init_connect(self):
        # 调用自定义信号和槽函数类（模型）
        self.model = MainModel(view=self)
