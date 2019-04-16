#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# __Author__: WangGuobao(guobao.v@gmail.com)
# __Date__: 2018/7/23 0023

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

"""
main的model模块
"""
import cv2
import os.path as osp
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QSettings
from PyQt5.QtGui import QImage, QCursor, QPixmap
from PyQt5.QtWidgets import QApplication, QFileDialog, QDialog
from easydict import EasyDict

import init_path
from src.model import proc_thread
from src.control.logger import *
from src.view.ui_dialog import *


class MainModel(QObject):
    """
    信号与槽函数类
    """
    proc_finish_signal = pyqtSignal(float)
    progress_signal = pyqtSignal(int, float)
    frame_signal = pyqtSignal(object)
    view_refresh_signal = pyqtSignal()
    back_ready_signal = pyqtSignal()

    # get_background_success = pyqtSignal()

    def __init__(self, view):
        super(MainModel, self).__init__()
        self.view = view

        # 缓存窗口状态
        path = osp.join(init_path.project_dir, "conf/window_status.ini")
        self.window_status = QSettings(path, QSettings.IniFormat)

        # 缓存路径
        self._fname_temp = "../data"
        self._dname_temp = "../data"

        # 隐藏centralwidget，以让dock占满窗口
        self.view.centralwidget.hide()

        # 初始化设置界面
        self._init_scene_args()

        # 初始化系统信号与连接
        self.view.pBtn_getFile.clicked.connect(self.on_pbtn_getfile_clicked)
        self.view.pBtn_getDir.clicked.connect(self.on_pbtn_getdir_clicked)
        self.view.action_run.triggered.connect(self.on_action_run_triggered)
        self.view.action_pause.triggered.connect(self.on_action_pause_triggered)
        self.view.action_stop.triggered.connect(self.on_action_stop_triggered)
        self.view.cBox_scene.currentIndexChanged.connect(self.on_cbox_scene_changed)
        self.view.pBtn_getBackground.clicked.connect(self.on_pbtn_getbackground_clicked)
        self.view.pBtn_showBackground.clicked.connect(self.on_pbtn_showbackground_clicked)
        self.view.action_stop.triggered.connect(self.on_action_stop_triggered)
        self.view.action_view_restore.triggered.connect(self.on_action_view_restore_triggered)
        self.view.action_about.triggered.connect(self.on_action_about_triggered)

        # 界面及参数更新信号
        self.view.cBox_shadow.stateChanged.connect(self.on_var_change)
        self.view.cBox_foreproc.stateChanged.connect(self.on_var_change)
        self.view.sBox_history.valueChanged.connect(self.on_var_change)
        self.view.sBox_threshold.valueChanged.connect(self.on_var_change)
        self.view.sBox_area.valueChanged.connect(self.on_var_change)
        self.view.dsBox_ratio.valueChanged.connect(self.on_var_change)
        self.view.sBox_blursize.valueChanged.connect(self.on_var_change)
        self.view.cBox_erodeshape.currentIndexChanged.connect(self.on_var_change)
        self.view.sBox_undetframes.valueChanged.connect(self.on_var_change)
        self.view.cBox_autoback.stateChanged.connect(self.on_var_change)
        self.view.dsBox_shadowvar.valueChanged.connect(self.on_var_change)

        # 自定义信号与槽
        self.proc_finish_signal.connect(self.on_proc_finish_signal_triggered)
        self.progress_signal.connect(self.on_progress_signal_refresh)
        self.frame_signal.connect(self.on_frame_signal_refresh)
        self.view_refresh_signal.connect(self.on_view_refresh_signal_triggered)
        self.back_ready_signal.connect(self.on_back_ready_signal_triggered)

    def _init_scene_args(self):
        # 初始化设置界面

        # 从外部配置文件读取
        self.cfg = EasyDict(settings.read_cfg())

        # 显示设置参数,参数详情看UI或settings
        self.view.sBox_history.setValue(self.cfg.DEFAULT.HISTORY)
        self.view.sBox_threshold.setValue(self.cfg.DEFAULT.THRESHOLD)
        self.view.sBox_area.setValue(self.cfg.DEFAULT.AREA_SIZE)
        self.view.dsBox_ratio.setValue(self.cfg.DEFAULT.BACK_RATIO)
        self.view.sBox_undetframes.setValue(self.cfg.DEFAULT.UN_DET_SIZE)
        self.view.sBox_blursize.setValue(self.cfg.DEFAULT.BLUR_SIZE)
        self.view.cBox_autoback.setChecked(self.cfg.DEFAULT.IS_AUTO_BACK)
        self.view.cBox_shadow.setChecked(self.cfg.DEFAULT.HAS_DET_SHADOW)
        self.view.dsBox_shadowvar.setValue(self.cfg.DEFAULT.DET_SHADOW_VAR)
        self.view.cBox_foreproc.setChecked(self.cfg.DEFAULT.HAS_FORE_PROC)
        self.view.cBox_erodeshape.setCurrentIndex(self.cfg.DEFAULT.ERODE_SHAPE)

        self.view.pBtn_getBackground.setEnabled(False)

        self.view.progressBar.hide()

        # 保存视图初始状态
        self.window_status.setValue("window_status", self.view.saveState())

    def on_pbtn_getfile_clicked(self):
        # TODO 可以开启多文件选择，选择的文件通过多进程进一步处理

        fname, ftype = QFileDialog.getOpenFileName(self.view, "选取文件", self._fname_temp,
                                                   "Video Files(*.mp4;*.avi;*.rmvb;*.mkv;*.wmv;*.3gp);;All Files(*.*)")
        if fname:
            self.view.lineEdit_videoFile.setText(fname)
            self._fname_temp = fname

    def on_pbtn_getdir_clicked(self):
        dname = QFileDialog.getExistingDirectory(self.view, "选取文件夹", self._dname_temp)
        if dname:
            self.view.lineEdit_saveDir.setText(dname)
            self._dname_temp = dname

    def on_action_triggered_view_enabled(self, flag):
        # 主要控件，视图可编辑状态变化

        self.view.tabWidget.setEnabled(flag)
        self.view.widget_set.setEnabled(flag)
        self.view.progressBar.setEnabled(not flag)

        # 鼠标指针状态变化
        if not flag:
            self.view.dockWidgetContents_frame.setCursor(QCursor(Qt.BusyCursor))
            self.view.dockWidget_settings.setCursor(QCursor(Qt.BusyCursor))
        else:
            self.view.dockWidgetContents_frame.setCursor(QCursor(Qt.ArrowCursor))
            self.view.dockWidget_settings.setCursor(QCursor(Qt.ArrowCursor))

    def on_action_run_triggered(self):
        if self.view.action_stop.isEnabled():
            logger.debug("当前线程暂停，执行恢复动作")
            # 若为暂停状态
            self.thread.resume()

            self.on_action_triggered_view_enabled(False)

            self.view.action_run.setEnabled(False)
            self.view.action_pause.setEnabled(True)
            self.view.action_stop.setEnabled(True)

            self.view.statusbar.showMessage("已恢复", 3000)
            return 0

        self.view.progressBar.show()

        self.view.action_run.setEnabled(False)
        self.view.action_pause.setEnabled(True)
        self.view.action_stop.setEnabled(True)

        if self.view.tabWidget.currentIndex() == 0:
            # 文件模式
            self.input = self.view.lineEdit_videoFile.displayText()
            self.output_dir_name = self.view.lineEdit_saveDir.displayText()
        elif self.view.tabWidget.currentIndex() == 1:
            # 摄像模式
            self.input = self.view.sBox_cam_num.value()
            self.output_dir_name = None
        else:
            self.input = 0
            self.output_dir_name = None

        if self.input is not "":
            self.thread = proc_thread.MotionDetThread(model=self)
            self.thread.setDaemon(True)  # 设置守护线程，以在主线程退出后退出
            self.thread.set_dirs(self.input, self.output_dir_name)
            self.thread.set_args(history=self.view.sBox_history.value(),
                                 threshold=self.view.sBox_threshold.value(),
                                 has_det_shadow=self.view.cBox_shadow.checkState(),
                                 background_ratio=self.view.dsBox_ratio.value(),
                                 blur_size=self.view.sBox_blursize.value(),
                                 fore_proc=self.view.cBox_foreproc.checkState(),
                                 erode_shape=tuple(eval(self.view.cBox_erodeshape.currentText())),
                                 area_size=self.view.sBox_area.value(),
                                 undetected_size=self.view.sBox_undetframes.value(),
                                 is_auto_back=self.view.cBox_autoback.checkState(),
                                 det_shadow_var=self.view.dsBox_shadowvar.value())

            self.on_action_triggered_view_enabled(False)

            if self.view.cBox_autoback.checkState() == 0:
                # 未选中自动更新，设置更新背景按钮可点击
                self.view.pBtn_getBackground.setEnabled(True)
            else:
                self.view.pBtn_getBackground.setEnabled(False)

            self.thread.start()

            self.view.statusbar.showMessage("开始处理！", 3000)
            logger.debug("开始处理")
        else:
            self.view.pBtn_getBackground.setEnabled(False)
            self.view.action_run.setEnabled(True)
            self.view.action_pause.setEnabled(False)
            self.view.action_stop.setEnabled(False)
            self.view.statusbar.showMessage("Error,参数错误！", 3000)
            logger.exception("Error，参数错误")

    def on_action_pause_triggered(self):
        # TODO 暂停时参数可修改（此处设置UI更新）
        logger.debug("准备暂停")
        if self.view.cBox_autoback.checkState() == 0:
            self.view.pBtn_getBackground.setEnabled(True)

        if self.thread._isNotPause.isSet():
            self.thread.pause()
            self.on_action_triggered_view_enabled(False)
            self.view.action_run.setEnabled(True)
            self.view.action_pause.setEnabled(False)
            self.view.action_stop.setEnabled(True)
            self.view.statusbar.showMessage("已暂停", 3000)
            logger.debug("线程已暂停")
        else:
            self.thread.resume()
            self.on_action_triggered_view_enabled(False)
            self.view.statusbar.showMessage("已恢复", 3000)
            logger.debug("线程已恢复")

    def on_action_stop_triggered(self):

        logger.debug("准备停止")
        if self.thread.isAlive():
            self.thread.stop()
            # 等待工作线程停止完毕
            self.thread.join()

            self.on_action_triggered_view_enabled(True)

            self.view.progressBar.hide()

            self.view.action_run.setEnabled(True)
            self.view.action_pause.setEnabled(False)
            self.view.action_stop.setEnabled(False)

            if self.view.cBox_autoback.checkState() == 0:
                # 未选中自动更新，设置更新背景按钮可点击
                self.view.pBtn_getBackground.setEnabled(True)

            # 按钮信息状态还原
            self.view.pBtn_getBackground.setText("更新背景")
            self.view.pBtn_showBackground.setText("显示背景图片")

            self.view.statusbar.showMessage("已停止", 3000)
            logger.debug("线程停止")
        else:
            logger.debug("线程已停止！")
            # QMessageBox.question(self.view, "提示", "Can't stop！",
            #                      QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)

    def on_cbox_scene_changed(self):
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
        self.view.cBox_autoback.blockSignals(True)
        self.view.dsBox_shadowvar.blockSignals(True)

        if self.view.cBox_scene.currentText() == "默认":
            # 显示参数设置
            self.view.cBox_shadow.setChecked(self.cfg.DEFAULT.HAS_DET_SHADOW)
            self.view.cBox_foreproc.setChecked(self.cfg.DEFAULT.HAS_FORE_PROC)
            self.view.sBox_history.setValue(self.cfg.DEFAULT.HISTORY)
            self.view.sBox_threshold.setValue(self.cfg.DEFAULT.THRESHOLD)
            self.view.sBox_area.setValue(self.cfg.DEFAULT.AREA_SIZE)
            self.view.dsBox_ratio.setValue(self.cfg.DEFAULT.BACK_RATIO)
            self.view.sBox_blursize.setValue(self.cfg.DEFAULT.BLUR_SIZE)
            self.view.cBox_erodeshape.setCurrentIndex(self.cfg.DEFAULT.ERODE_SHAPE)
            self.view.sBox_undetframes.setValue(self.cfg.DEFAULT.UN_DET_SIZE)
            self.view.cBox_autoback.setChecked(self.cfg.DEFAULT.IS_AUTO_BACK)
            self.view.dsBox_shadowvar.setValue(self.cfg.DEFAULT.DET_SHADOW_VAR)
        else:
            # 显示参数设置
            self.view.cBox_shadow.setChecked(self.cfg.CUSTOM.HAS_DET_SHADOW)
            self.view.cBox_foreproc.setChecked(self.cfg.CUSTOM.HAS_FORE_PROC)
            self.view.sBox_history.setValue(self.cfg.CUSTOM.HISTORY)
            self.view.sBox_threshold.setValue(self.cfg.CUSTOM.THRESHOLD)
            self.view.sBox_area.setValue(self.cfg.CUSTOM.AREA_SIZE)
            self.view.dsBox_ratio.setValue(self.cfg.CUSTOM.BACK_RATIO)
            self.view.sBox_blursize.setValue(self.cfg.CUSTOM.BLUR_SIZE)
            self.view.cBox_erodeshape.setCurrentIndex(self.cfg.CUSTOM.ERODE_SHAPE)
            self.view.sBox_undetframes.setValue(self.cfg.CUSTOM.UN_DET_SIZE)
            self.view.cBox_autoback.setChecked(self.cfg.CUSTOM.IS_AUTO_BACK)
            self.view.dsBox_shadowvar.setValue(self.cfg.CUSTOM.DET_SHADOW_VAR)

        self.view.cBox_shadow.blockSignals(False)
        self.view.cBox_foreproc.blockSignals(False)
        self.view.sBox_history.blockSignals(False)
        self.view.sBox_threshold.blockSignals(False)
        self.view.sBox_area.blockSignals(False)
        self.view.dsBox_ratio.blockSignals(False)
        self.view.sBox_blursize.blockSignals(False)
        self.view.cBox_erodeshape.blockSignals(False)
        self.view.sBox_undetframes.blockSignals(False)
        self.view.cBox_autoback.blockSignals(False)
        self.view.dsBox_shadowvar.blockSignals(False)

    def on_pbtn_getbackground_clicked(self):
        # 设置手动背景更新，点击将重新开始背景学习的循环
        try:
            self.thread.set_learningrate(-1)
        except:
            self.view.statusbar.showMessage("无法设置背景更新!", 3000)
            logger.exception("无法设置背景更新!")
        else:
            self.view.pBtn_getBackground.setText("更新背景(Start)")
            self.view.pBtn_showBackground.setText("显示背景图片")
            self.view.statusbar.showMessage("重启背景更新！（参考历史帧数：{}）".format(self.view.sBox_history.value()), 3000)
            logger.debug("重新开始背景更新")

    def on_pbtn_showbackground_clicked(self):
        logger.debug("显示背景图片")
        back_img_path = osp.join(init_path.project_dir, "data\\background.jpg")
        try:
            background = cv2.imread(back_img_path)
            background = cv2.resize(background, None, fx=0.5, fy=0.5)
            cv2.imshow("Background", background)
        except:
            self.view.statusbar.showMessage("{},图片不存在或无法打开图片！".format(back_img_path), 3000)
            logger.exception("图片不存在或无法打开图片！")
        else:
            self.view.statusbar.showMessage("成功打开背景图片！{}".format(back_img_path), 3000)
            logger.debug("成功打开背景图片")

    def on_action_view_restore_triggered(self):
        # 重置视图
        self.view.restoreState(self.window_status.value("window_status"))

    def on_action_about_triggered(self):
        # 显示关于页
        self.view.dialog = QDialog()
        about = Ui_Dialog()
        about.setupUi(self.view.dialog)

        # 只保留关闭按钮
        self.view.dialog.setWindowFlags(Qt.WindowCloseButtonHint)

        # 使用exec方法显示
        self.view.dialog.exec_()

    def on_var_change(self):
        # TODO 线程暂停时参数可修改（背景需自动更新）

        # 获取参数设置
        logger.debug("获取自定义参数")
        self.cfg.CUSTOM.HAS_DET_SHADOW = self.view.cBox_shadow.checkState()
        self.cfg.CUSTOM.HAS_FORE_PROC = self.view.cBox_foreproc.checkState()
        self.cfg.CUSTOM.HISTORY = self.view.sBox_history.value()
        self.cfg.CUSTOM.THRESHOLD = self.view.sBox_threshold.value()
        self.cfg.CUSTOM.AREA_SIZE = self.view.sBox_area.value()
        self.cfg.CUSTOM.BACK_RATIO = self.view.dsBox_ratio.value()
        self.cfg.CUSTOM.BLUR_SIZE = self.view.sBox_blursize.value()
        self.cfg.CUSTOM.ERODE_SHAPE = self.view.cBox_erodeshape.currentIndex()
        self.cfg.CUSTOM.UN_DET_SIZE = self.view.sBox_undetframes.value()
        self.cfg.CUSTOM.IS_AUTO_BACK = self.view.cBox_autoback.checkState()
        self.cfg.CUSTOM.DET_SHADOW_VAR = self.view.dsBox_shadowvar.value()

        # 保存到文件
        settings.write_cfg(self.cfg)

        # 切换多选框状态
        if self.cfg.CUSTOM != self.cfg.DEFAULT:
            logger.debug("切换多选框状态")
            # 与_on_cBox_scene_changed的信号互斥，程序内部进行相关动作时需要屏蔽该信号
            self.view.cBox_scene.blockSignals(True)
            self.view.cBox_scene.setCurrentText("自定义")
            self.view.cBox_scene.blockSignals(False)

    def on_proc_finish_signal_triggered(self, average_time):
        # 线程完成，处理UI状态

        logger.debug("线程完成或退出，收尾处理UI状态")
        self.on_action_triggered_view_enabled(True)

        self.view.action_run.setEnabled(True)
        self.view.action_pause.setEnabled(False)
        self.view.action_stop.setEnabled(False)

        if self.view.cBox_autoback.checkState() == 0:
            # 未选中自动更新，设置更新背景按钮可点击
            self.view.pBtn_getBackground.setEnabled(True)

        # 按钮信息状态还原
        self.view.pBtn_getBackground.setText("更新背景")
        self.view.pBtn_showBackground.setText("显示背景图片")

        self.view.statusbar.showMessage("处理完成！帧平均处理用时：{:.2f} ms".format(average_time), 1000000)

    def on_progress_signal_refresh(self, progress_value, frame_proc_time):
        # 接收工作线程的进度信号与帧处理时间并显示
        self.view.statusbar.showMessage("处理中: {} % , 当前帧用时：{:.2f} ms".format(progress_value, frame_proc_time), 1000000)
        if progress_value == -1:
            self.view.progressBar.setMaximum(0)
        else:
            self.view.progressBar.setValue(progress_value)

    def on_frame_signal_refresh(self, frame):
        # 接收工作线程的帧图像并显示
        # TODO 画面比例调整可选自适应或固定模式
        # 画面比例调整,自适应 
        width = self.view.label_showFrame.width()  # 960
        height = self.view.label_showFrame.height()  # 540
        fx = width / frame.shape[1]
        fy = height / frame.shape[0]

        # 缩放
        frame = cv2.resize(frame, None, fx=fx, fy=fy)
        # 转为QImage，且BGR2RGB
        image = QImage(frame, frame.shape[1], frame.shape[0], frame.shape[1] * 3,
                       QImage.Format_RGB888).rgbSwapped()
        # 显示
        self.view.label_showFrame.setPixmap(QPixmap(image))

    @staticmethod
    def on_view_refresh_signal_triggered():
        # 接收工作线程的view刷新信号并刷新
        QApplication.processEvents()

    def on_back_ready_signal_triggered(self):
        # 背景图片已保存，UI状态更新
        self.view.pBtn_showBackground.setText("显示背景图片(Ready)")
        if self.view.pBtn_getBackground.text() == "更新背景(Start)":
            self.view.pBtn_getBackground.setText("更新背景(Finish)")
