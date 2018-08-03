#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# __Author__: WangGuobao(guobao.v@gmail.com)
# __Date__: 2018/7/23 0023

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

"""
main的模型类
"""
from easydict import EasyDict
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox

import proc_thread
from control.logger import *


class MainModel(QObject):
    """
    信号与槽函数类
    """
    success_signal = pyqtSignal()
    get_background_success=pyqtSignal()

    def __init__(self, view):
        super(MainModel, self).__init__()
        # todo:简化变量
        self.view = view
        # 缓存路径
        self._fname_temp = "../data"
        self._dname_temp = "../data"

        # 初始化设置界面
        self._init_scene_args()

        # 初始化系统信号与连接
        self.view.pBtn_getFile.clicked.connect(self._on_pBtn_getFile_clicked)
        self.view.pBtn_getDir.clicked.connect(self._on_pBtn_getDir_clicked)
        self.view.action_run.triggered.connect(self._on_action_run_triggered)
        self.view.action_pause.triggered.connect(self._on_action_pause_triggered)
        self.view.action_stop.triggered.connect(self._on_action_stop_triggered)
        self.view.cBox_scene.currentIndexChanged.connect(self._on_cBox_scene_changed)
        self.view.pBtn_getBackground.clicked.connect(self._on_pBtn_getBackground_clicked)
        self.view.pBtn_showBackground.clicked.connect(self._on_pBtn_showBackground_clicked)
        # todo: 添加视图控制,且应根据更新项更新而不是统一更新

        # 界面及参数更新信号
        self.view.cBox_shadow.stateChanged.connect(self._on_var_change)
        self.view.cBox_foreproc.stateChanged.connect(self._on_var_change)
        self.view.sBox_history.valueChanged.connect(self._on_var_change)
        self.view.sBox_threshold.valueChanged.connect(self._on_var_change)
        self.view.sBox_area.valueChanged.connect(self._on_var_change)
        self.view.dsBox_ratio.valueChanged.connect(self._on_var_change)
        self.view.sBox_blursize.valueChanged.connect(self._on_var_change)
        self.view.cBox_erodeshape.currentIndexChanged.connect(self._on_var_change)
        self.view.sBox_undetframes.valueChanged.connect(self._on_var_change)

        # 自定义信号与槽
        self.success_signal.connect(self._on_success_triggered)
        self.get_background_success.connect(self._on_get_background_success_triggered)

    def _init_scene_args(self):
        # todo:配置使用外部文件加载
        # 定义默认和自定义设置
        self.cfg = EasyDict()
        self.cfg.DEFAULT = EasyDict()
        self.cfg.CUSTOM = EasyDict()
        # 默认设置
        self.cfg.DEFAULT.HISTORY = 600
        self.cfg.DEFAULT.THRESHOLD = 100
        self.cfg.DEFAULT.HAS_DET_SHADOW = 0
        self.cfg.DEFAULT.BACK_RATIO = 0.85
        self.cfg.DEFAULT.BLUR_SIZE = 5
        self.cfg.DEFAULT.HAS_FORE_PROC = 2
        self.cfg.DEFAULT.ERODE_SHAPE = 2
        self.cfg.DEFAULT.AREA_SIZE = 500
        self.cfg.DEFAULT.UN_DET_SIZE = 10
        # 自定义设置
        self.cfg.CUSTOM.HISTORY = 600
        self.cfg.CUSTOM.THRESHOLD = 100
        self.cfg.CUSTOM.HAS_DET_SHADOW = 0
        self.cfg.CUSTOM.BACK_RATIO = 0.85
        self.cfg.CUSTOM.BLUR_SIZE = 5
        self.cfg.CUSTOM.HAS_FORE_PROC = 2
        self.cfg.CUSTOM.ERODE_SHAPE = 2
        self.cfg.CUSTOM.AREA_SIZE = 500
        self.cfg.CUSTOM.UN_DET_SIZE = 10

        # 显示参数
        self.view.cBox_shadow.setChecked(self.cfg.DEFAULT.HAS_DET_SHADOW)
        self.view.cBox_foreproc.setChecked(self.cfg.DEFAULT.HAS_FORE_PROC)
        self.view.sBox_history.setValue(self.cfg.DEFAULT.HISTORY)
        self.view.sBox_threshold.setValue(self.cfg.DEFAULT.THRESHOLD)
        self.view.sBox_area.setValue(self.cfg.DEFAULT.AREA_SIZE)
        self.view.dsBox_ratio.setValue(self.cfg.DEFAULT.BACK_RATIO)
        self.view.sBox_blursize.setValue(self.cfg.DEFAULT.BLUR_SIZE)
        self.view.cBox_erodeshape.setCurrentIndex(self.cfg.DEFAULT.ERODE_SHAPE)
        self.view.sBox_undetframes.setValue(self.cfg.DEFAULT.UN_DET_SIZE)

    def _on_pBtn_getFile_clicked(self):
        # todo: 可以开启多文件选择，选择的文件通过多线程进一步处理

        fname, ftype = QFileDialog.getOpenFileName(self.view, "选取文件", self._fname_temp,
                                                   "Video Files(*.mp4;*.avi;*.wmv;*.rmvb;*.flv;*.mpg;*.rm;*.mkv);;All Files(*.*)")
        if fname:
            self.view.lineEdit_videoFile.setText(fname)
            self._fname_temp = fname

    def _on_pBtn_getDir_clicked(self):
        dname = QFileDialog.getExistingDirectory(self.view, "选取文件夹", self._dname_temp)
        if dname:
            self.view.lineEdit_saveDir.setText(dname)
            self._dname_temp = dname

    def _on_action_triggered_view_enabled(self, bool):
        # 视图可编辑状态变化
        self.view.tabWidget.setEnabled(bool)
        self.view.widget_set.setEnabled(bool)
        self.view.progressBar.setEnabled(not bool)

        # 鼠标指针状态变化
        if bool == False:
            self.view.dockWidgetContents_frame.setCursor(QtGui.QCursor(QtCore.Qt.BusyCursor))
            self.view.dockWidget_settings.setCursor(QtGui.QCursor(QtCore.Qt.BusyCursor))
        else:
            self.view.dockWidgetContents_frame.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            self.view.dockWidget_settings.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    def _on_action_run_triggered(self):
        if self.view.action_stop.isEnabled():
            logger.debug("当前线程暂停，执行恢复动作")
            # 若为暂停状态
            self.thread.resume()
            self._on_action_triggered_view_enabled(False)
            self.view.action_run.setEnabled(False)
            self.view.action_pause.setEnabled(True)
            self.view.action_stop.setEnabled(True)
            self.view.statusbar.showMessage("已恢复", 3000)
            return 0

        self.view.action_run.setEnabled(False)
        self.view.action_pause.setEnabled(True)
        self.view.action_stop.setEnabled(True)

        if self.view.tabWidget.currentIndex() == 0:
            self.input = self.view.lineEdit_videoFile.displayText()
            self.output_dir_name = self.view.lineEdit_saveDir.displayText()
        elif self.view.tabWidget.currentIndex() == 1:
            self.input = self.view.sBox_cam_num.value()
            self.output_dir_name = None
        else:
            self.input = 0
            self.output_dir_name = None

        self.thread = proc_thread.MotionDetThread(model=self)
        self.thread.setDaemon(True)  # 设置守护线程，以在主线程退出后退出
        self.thread.setDirs(self.input, self.output_dir_name)

        self.thread.setArgs(history=self.view.sBox_history.value(),
                            threshold=self.view.sBox_threshold.value(),
                            detshadow=self.view.cBox_shadow.checkState(),
                            backratio=self.view.dsBox_ratio.value(),
                            blursize=self.view.sBox_blursize.value(),
                            foreproc=self.view.cBox_foreproc.checkState(),
                            erodeshape=tuple(eval(self.view.cBox_erodeshape.currentText())),
                            areasize=self.view.sBox_area.value(),
                            undetsize=self.view.sBox_undetframes.value())

        self._on_action_triggered_view_enabled(False)
        self.view.statusbar.showMessage("开始处理视频！", 3000)
        logger.debug("开始处理视频")
        self.thread.start()
        # self.thread.join()  # 等待完成但是会阻塞线程

    def _on_action_pause_triggered(self):

        if self.thread._isNotPause.isSet():
            self.thread.pause()
            self._on_action_triggered_view_enabled(True)
            self.view.action_run.setEnabled(True)
            self.view.action_pause.setEnabled(False)
            self.view.action_stop.setEnabled(True)
            self.view.statusbar.showMessage("已暂停", 3000)
            logger.debug("线程已暂停")
        else:
            self.thread.resume()
            self._on_action_triggered_view_enabled(False)
            self.view.statusbar.showMessage("已恢复", 3000)
            logger.debug("线程已恢复")

    def _on_action_stop_triggered(self):
        if self.thread.isAlive():
            self._on_action_triggered_view_enabled(True)
            self.view.action_run.setEnabled(True)
            self.view.action_pause.setEnabled(False)
            self.view.action_stop.setEnabled(False)
            self.thread.stop()
            self.thread.join()
            self.view.statusbar.showMessage("已停止", 3000)
            logger.debug("线程已停止")
        else:
            QMessageBox.question(self.view, "提示", "Can't stop！",
                                 QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)

    def _on_cBox_scene_changed(self):
        # 与_on_var_change的信号互斥，进行相关动作需要屏蔽引起_on_var_change的信号
        self.view.cBox_shadow.blockSignals(True)
        self.view.cBox_foreproc.blockSignals(True)
        self.view.sBox_history.blockSignals(True)
        self.view.sBox_threshold.blockSignals(True)
        self.view.sBox_area.blockSignals(True)
        self.view.dsBox_ratio.blockSignals(True)
        self.view.sBox_blursize.blockSignals(True)
        self.view.cBox_erodeshape.blockSignals(True)
        self.view.sBox_undetframes.blockSignals(True)

        if self.view.cBox_scene.currentText() == "默认":
            # 显示参数设置
            logger.debug("显示默认参数")
            self.view.cBox_shadow.setChecked(self.cfg.DEFAULT.DET_SHADOW_FLAG)
            self.view.cBox_foreproc.setChecked(self.cfg.DEFAULT.FORE_PROC_FLAG)
            self.view.sBox_history.setValue(self.cfg.DEFAULT.HISTORY)
            self.view.sBox_threshold.setValue(self.cfg.DEFAULT.THRESHOLD)
            self.view.sBox_area.setValue(self.cfg.DEFAULT.AREA_SIZE)
            self.view.dsBox_ratio.setValue(self.cfg.DEFAULT.BACK_RATIO)
            self.view.sBox_blursize.setValue(self.cfg.DEFAULT.BLUR_SIZE)
            self.view.cBox_erodeshape.setCurrentIndex(self.cfg.DEFAULT.ERODE_SHAPE)
            self.view.sBox_undetframes.setValue(self.cfg.DEFAULT.UN_DET_SIZE)
        else:
            # 显示参数设置
            logger.debug("显示自定义参数")
            self.view.cBox_shadow.setChecked(self.cfg.CUSTOM.DET_SHADOW_FLAG)
            self.view.cBox_foreproc.setChecked(self.cfg.CUSTOM.FORE_PROC_FLAG)
            self.view.sBox_history.setValue(self.cfg.CUSTOM.HISTORY)
            self.view.sBox_threshold.setValue(self.cfg.CUSTOM.THRESHOLD)
            self.view.sBox_area.setValue(self.cfg.CUSTOM.AREA_SIZE)
            self.view.dsBox_ratio.setValue(self.cfg.CUSTOM.BACK_RATIO)
            self.view.sBox_blursize.setValue(self.cfg.CUSTOM.BLUR_SIZE)
            self.view.cBox_erodeshape.setCurrentIndex(self.cfg.CUSTOM.ERODE_SHAPE)
            self.view.sBox_undetframes.setValue(self.cfg.CUSTOM.UN_DET_SIZE)

        self.view.cBox_shadow.blockSignals(False)
        self.view.cBox_foreproc.blockSignals(False)
        self.view.sBox_history.blockSignals(False)
        self.view.sBox_threshold.blockSignals(False)
        self.view.sBox_area.blockSignals(False)
        self.view.dsBox_ratio.blockSignals(False)
        self.view.sBox_blursize.blockSignals(False)
        self.view.cBox_erodeshape.blockSignals(False)
        self.view.sBox_undetframes.blockSignals(False)

    def _on_pBtn_getBackground_clicked(self):
        # 设置背景更新
        self.thread.setLearningRate(-1)

        # if self.view.tabWidget.currentIndex() == 0:
        #     self.input = self.view.lineEdit_videoFile.displayText()
        # elif self.view.tabWidget.currentIndex() == 1:
        #     self.input = self.view.sBox_cam_num.value()
        # else:
        #     self.input = 0
        #
        # self.GetBackgroundThread = proc_thread.GetBackgroundThread(model=self)
        # self.GetBackgroundThread.setDaemon(True)  # 设置守护线程，以在主线程退出后退出
        # self.GetBackgroundThread.setInput(self.input)
        # self.GetBackgroundThread.setArgs(history=self.view.sBox_history.value(),
        #                     threshold=self.view.sBox_threshold.value(),
        #                     detshadow=self.view.cBox_shadow.checkState(),
        #                     backratio=self.view.dsBox_ratio.value())
        #
        # self._on_action_triggered_view_enabled(False)
        # self.view.statusbar.showMessage("开始提取背景！", 3000)
        # logger.debug("开始提取背景")
        # self.GetBackgroundThread.start()

    def _on_pBtn_showBackground_clicked(self):
        #todo :显示背景图片
        pass

    def _on_var_change(self):
        # 获取参数设置
        logger.debug("获取自定义参数")
        self.cfg.CUSTOM.DET_SHADOW_FLAG = self.view.cBox_shadow.checkState()
        self.cfg.CUSTOM.FORE_PROC_FLAG = self.view.cBox_foreproc.checkState()
        self.cfg.CUSTOM.HISTORY = self.view.sBox_history.value()
        self.cfg.CUSTOM.THRESHOLD = self.view.sBox_threshold.value()
        self.cfg.CUSTOM.AREA_SIZE = self.view.sBox_area.value()
        self.cfg.CUSTOM.BACK_RATIO = self.view.dsBox_ratio.value()
        self.cfg.CUSTOM.BLUR_SIZE = self.view.sBox_blursize.value()
        self.cfg.CUSTOM.ERODE_SHAPE = self.view.cBox_erodeshape.currentIndex()
        self.cfg.CUSTOM.UN_DET_SIZE = self.view.sBox_undetframes.value()

        # 切换多选框状态
        if self.cfg.CUSTOM != self.cfg.DEFAULT:
            logger.debug("切换多选框状态")
            # 与_on_cBox_scene_changed的信号互斥，进行相关动作时需要屏蔽引起_on_cBox_scene_changed的信号
            self.view.cBox_scene.blockSignals(True)
            self.view.cBox_scene.setCurrentText("自定义")
            self.view.cBox_scene.blockSignals(False)

    def _on_success_triggered(self):
        # 线程完成，处理UI状态
        logger.debug("线程正常完成，收尾处理UI状态")
        self._on_action_triggered_view_enabled(True)
        self.view.action_run.setEnabled(True)
        self.view.action_pause.setEnabled(False)
        self.view.action_stop.setEnabled(False)
        self.view.statusbar.showMessage("处理完成！", 100000)

    def _on_get_background_success_triggered(self):
        logger.debug("背景提取完成，收尾处理UI状态")
        self._on_action_triggered_view_enabled(True)
        self.view.statusbar.showMessage("背景更新完成！", 100000)
