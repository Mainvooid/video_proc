#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# __Author__: WangGuobao(guobao.v@gmail.com)
# __Date__: 2018/7/23 0023

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

"""
线程处理模块
"""
import time
import threading
import cv2
import numpy as np
import os
import os.path as osp

from core.control.logger import *
import init_path


# todo:使用QThread替换threading.Thread
class MotionDetThread(threading.Thread):
    """
    动作检测线程类,只是为了和UI分离，并非并发
    """

    def __init__(self, model):
        super(MotionDetThread, self).__init__()
        # 线程标志
        self._isRunning = threading.Event()  # 用于停止线程
        self._isRunning.set()  # 设置为True
        self._isNotPause = threading.Event()  # 用于暂停线程
        self._isNotPause.set()  # 设置为True

        # ui类
        self.model = model

        # 相关参数
        self.fps = None
        self.LearningRate = -1

    def setDirs(self, input, output_dir_name):
        # 文件路径
        self.input = input
        self.output_dir = output_dir_name

    def setArgs(self, history, threshold, detshadow, backratio, blursize, foreproc,
                erodeshape, areasize, undetsize):
        self.mog2_history = history
        self.mog2_varThreshold = threshold
        self.DETECT_SHADOWS_FLAG = detshadow
        self.background_ratio = backratio
        self.medianBlur_ksize = blursize
        self.FORE_PROC_FLAG = foreproc
        self.e_shape = erodeshape
        self.d_shape = erodeshape
        self.area_size = areasize
        self.undetected_size = undetsize

    def setFPS(self, fps):
        # 设置帧率
        self.fps = fps

    def setLearningRate(self, LearningRate):
        # 设置帧率
        self.LearningRate = LearningRate
        # 初始化计数
        self.learningFrameNo = 0

    def run(self):
        # 打开视频
        try:
            self.capture = cv2.VideoCapture(self.input)
        except:
            logger.exception("打开视频异常!")
        else:
            logger.debug("成功打开视频!")
            # 高斯背景建模对象
        # history：用于训练背景的帧数，默认500，若.apply设置自动更新learningRate(-1)，此时history越大，learningRate越小，背景更新越慢
        # varThreshold：方差阈值，用于判断当前像素是前景还是背景。一般默认16，如果光照变化明显，如阳光下的水面，建议设为25-36
        mog2 = cv2.createBackgroundSubtractorMOG2(history=self.mog2_history,
                                                  varThreshold=self.mog2_varThreshold,
                                                  detectShadows=self.DETECT_SHADOWS_FLAG)

        # 设置背景比率，取太高多背景模型叠加会模糊（类似滤波），取太低细节会不够（类似腐蚀）
        mog2.setBackgroundRatio(ratio=self.background_ratio)
        # 设置高斯模型数
        mog2.setNMixtures(5)
        # 阴影阈值
        if self.DETECT_SHADOWS_FLAG:
            mog2.setShadowThreshold(0.8)
        total_frame_num = 0
        total_frame_time = 0
        if isinstance(self.input, int):
            # 摄像模式
            logger.debug("摄像模式")

            # 读帧并处理
            self.frameNo = 0  # 第几帧
            self.learningFrameNo = 0
            motion_start, motion_count = 0, 0  # 运动帧计数
            while (True):
                start_time = time.time()
                # 阻塞标志
                self._isNotPause.wait()
                if self._isRunning.isSet() == False:
                    break

                if self.learningFrameNo == self.mog2_history:
                    # 停止背景更新
                    self.LearningRate = 0
                    self.learningFrameNo = 0
                    # 保存背景
                    back_img_path = osp.join(init_path.project_dir, "data\\background.jpg")
                    # 目录不存在则创建目录(为pyinstaller的兼容)
                    if osp.exists(osp.split(back_img_path)[0]) == False:
                        os.mkdir(osp.split(back_img_path)[0])
                    # 写入图片
                    ok=cv2.imwrite(back_img_path, mog2.getBackgroundImage())
                    if ok :
                        self.model.back_ready_signal.emit()
                        logger.debug("背景保存成功")
                    else:
                        logger.debug("背景保存失败")

                ok, frame = self.capture.read()
                if not ok:
                    logger.exception("读取视频异常!")
                self.frameNo += 1
                self.learningFrameNo += 1
                total_frame_num += 1

                # 混合高斯建模获取前景与背景

                try:
                    rows, cols, ch = frame.shape
                except AttributeError:
                    logger.debug("读取帧大小错误或未能识别摄像头")
                    # todo:错误信息显示
                else:
                    foreground = np.zeros(shape=(rows, cols, 1), dtype=np.uint8)

                # 计算前景蒙版,动态设置学习率，为0时背景不更新，为1时逐帧更新，默认为-1，即算法自动更新；
                mog2.apply(image=frame, fgmask=foreground, learningRate=self.LearningRate)

                # 中值滤波
                cv2.medianBlur(src=foreground, dst=foreground, ksize=self.medianBlur_ksize)

                # 前景处理过程，形态学腐蚀，膨胀
                if self.FORE_PROC_FLAG is True:
                    cv2.erode(src=foreground, dst=foreground, kernel=np.ones(shape=self.e_shape, dtype=np.uint8))
                    cv2.dilate(src=foreground, dst=foreground, kernel=np.ones(shape=self.d_shape, dtype=np.uint8))

                # 在二值前景图中找轮廓，用最小矩形包围
                image, contours, hierarchy = cv2.findContours(image=foreground,
                                                              mode=cv2.RETR_TREE,
                                                              method=cv2.CHAIN_APPROX_SIMPLE)
                metion_flag = False
                cv2.drawContours(foreground, contours, -1, (0, 0, 255), 3, hierarchy=hierarchy)  # 会抵消掉上一层的轮廓
                # 降噪后重新找轮廓
                image, contours, hierarchy = cv2.findContours(image=foreground,
                                                              mode=cv2.RETR_TREE,
                                                              method=cv2.CHAIN_APPROX_SIMPLE)
                # 显示轮廓
                rect = []
                for i, c in enumerate(contours):
                    # 判断轮廓面积
                    if cv2.contourArea(c) > self.area_size:
                        metion_flag = True
                        # 包住轮廓的最小矩形的坐标（x，y为左上点坐标）
                        (x, y, w, h) = cv2.boundingRect(c)
                        rect.append(np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]]))
                if len(rect) == 1:
                    # 若当前帧只找到一个轮廓
                    end_time = time.time()
                    # 计算帧处理时间,s->ms
                    frame_proc_time = (end_time - start_time) * 1000
                    # 统计总时间，更新进度
                    total_frame_time += frame_proc_time
                    progress_value = self.frameNo / total_frame_num * 100
                    # 跨线程发送进度和时间信号，更新UI
                    self.model.progress_signal.emit(progress_value, frame_proc_time)
                    # 刷新页面防止卡顿
                    self.model.view_refresh_signal.emit()
                    continue
                else:
                    for j in range(len(rect)):
                        r0 = cv2.minAreaRect(rect[0])
                        # 循环中是否找到相交点
                        isFind = False
                        for k in range(1, len(rect)):
                            r1 = cv2.minAreaRect(rect[k])
                            # 计算相交区域的顶点
                            retval, intersectingRegion = cv2.rotatedRectangleIntersection(r0, r1)
                            if retval == cv2.INTERSECT_PARTIAL or cv2.INTERSECT_FULL:
                                # 如果相交或内含，由合并点集计算最小正矩形
                                # logger.debug("存在交或含")
                                points = np.vstack((rect[0], rect[k]))
                                (x, y, w, h) = cv2.boundingRect(points)
                                # 列表元素变化
                                # logger.debug("j:{},k:{}".format(0, k))
                                rect.pop(0)
                                rect.pop(k - 1)
                                rect.append(np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]]))
                                isFind = True
                                break
                        if isFind == False:
                            # logger.debug("当前没有交或含")
                            rect.append(rect[0])
                            rect.pop(0)
                # 画矩形框
                for r in rect:
                    p = r.tolist()
                    (x, y) = p[0]
                    w = p[3][0] - x
                    h = p[3][1] - y
                    cv2.rectangle(img=frame, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0), thickness=3)

                # 更新运动帧计数并打印
                if metion_flag and self.frameNo != 1:
                    if motion_start == 0:
                        motion_start = self.frameNo

                        # 在UI界面显示
                        self.model.frame_signal.emit(frame)

                    elif self.frameNo <= motion_start + motion_count + self.undetected_size:  # 允许n帧以内不连续的误差
                        motion_count += 1

                        # 在UI界面显示
                        self.model.frame_signal.emit(frame)

                    else:
                        # print("运动帧：%d-%d" % (motion_start, motion_start + motion_count))
                        motion_start, motion_count = 0, 0

                end_time = time.time()
                # 计算帧处理时间,s->ms
                frame_proc_time = (end_time - start_time) * 1000
                # 统计总时间
                total_frame_time += frame_proc_time
                # 跨线程发送进度和时间信号，更新UI
                progress_value = 99
                self.model.progress_signal.emit(progress_value, frame_proc_time)
                # 刷新页面防止卡顿
                self.model.view_refresh_signal.emit()
        else:
            # 文件模式
            logger.debug("文件模式")

            # 读帧并处理
            self.frameNo = 0  # 第几帧
            self.learningFrameNo = 0  # 记录背景更新帧数
            motion_start, motion_count = 0, 0  # 运动帧计数

            # 视频写入
            self.writer = cv2.VideoWriter()
            codec = cv2.VideoWriter_fourcc(*'X264')  # X264(压缩率最高)，DIVX(基于MPEG-4标准),MJPG(文件大)，XVID(DIVX的开源改进版)
            #codec = -1 # 从系统中选取
            if self.fps == None:
                self.fps = self.capture.get(cv2.CAP_PROP_FPS)
            isColor = True
            frame_size = (
                int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))

            # 视频保存路径
            output_name = osp.splitext(osp.basename(self.input))[0]
            output_file_name = osp.join(self.output_dir, "gen_" + output_name + ".avi")

            self.writer.open(output_file_name, fourcc=codec, fps=self.fps, frameSize=frame_size, isColor=isColor)

            # 视频帧数
            total_frame_num = self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
            total_frame_time = 0

            # #p
            # self.writer1 = cv2.VideoWriter()
            # # 视频保存路径
            # output_name1 = osp.splitext(osp.basename(self.input))[0]
            # output_file_name1 = osp.join(self.output_dir, "proc_" + output_name1 + ".avi")
            #
            # self.writer1.open(output_file_name1, fourcc=codec, fps=self.fps, frameSize=frame_size, isColor=isColor)

            while (True):
                start_time = time.time()
                # 阻塞标志
                self._isNotPause.wait()
                if (self._isRunning.isSet() == False) or (total_frame_num == self.frameNo):
                    break

                if self.learningFrameNo == self.mog2_history:
                    # 停止背景更新
                    self.LearningRate = 0
                    self.learningFrameNo = 0
                    # 保存背景
                    back_img_path = osp.join(init_path.project_dir, "data\\background.jpg")
                    # 目录不存在则创建目录(为pyinstaller的兼容)
                    if osp.exists(osp.split(back_img_path)[0]) == False:
                        os.mkdir(osp.split(back_img_path)[0])
                    # 写入图片
                    ok=cv2.imwrite(back_img_path, mog2.getBackgroundImage())
                    if ok :
                        self.model.back_ready_signal.emit()
                        logger.debug("背景保存成功")
                    else:
                        logger.debug("背景保存失败")

                ok, frame = self.capture.read()
                if not ok:
                    logger.exception("读取视频异常!")
                self.frameNo += 1
                self.learningFrameNo += 1

                # 混合高斯建模获取前景与背景
                rows, cols, ch = frame.shape
                foreground = np.zeros(shape=(rows, cols, 1), dtype=np.uint8)

                # 计算前景蒙版,动态设置学习率，为0时背景不更新，为1时逐帧更新，默认为-1，即算法自动更新；
                mog2.apply(image=frame, fgmask=foreground, learningRate=self.LearningRate)

                # 中值滤波
                cv2.medianBlur(src=foreground, dst=foreground, ksize=self.medianBlur_ksize)

                # 前景处理过程，形态学腐蚀，膨胀
                if self.FORE_PROC_FLAG is True:
                    cv2.dilate(src=foreground, dst=foreground, kernel=np.ones(shape=self.d_shape, dtype=np.uint8))
                    cv2.erode(src=foreground, dst=foreground, kernel=np.ones(shape=self.e_shape, dtype=np.uint8))
                    # # 创建一个3*3的椭圆核
                    # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                    # # 形态学开运算去噪点
                    # foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)

                # todo:对二值图进行更有效的滤波
                # 在二值前景图中找轮廓，用最小矩形包围,hierarchy[i][.]:下一条0；前一条1,第一条子轮廓2，父轮廓3
                image, contours, hierarchy = cv2.findContours(image=foreground,
                                                              mode=cv2.RETR_TREE,
                                                              method=cv2.CHAIN_APPROX_SIMPLE)
                metion_flag = False

                # a0 = cv2.resize(foreground, None, fx=0.5, fy=0.5)
                # cv2.imshow("image0", a0)
                # cv2.waitKey(1)

                # 下面俩步为了滤波，似乎挺有效
                cv2.drawContours(foreground, contours, -1, (0, 0, 255), 3, hierarchy=hierarchy)  # 会抵消掉上一层的轮廓

                # a = cv2.resize(foreground, None, fx=0.5, fy=0.5)
                # cv2.imshow("image", a)
                # cv2.waitKey(1)

                image, contours, hierarchy = cv2.findContours(image=foreground,
                                                              mode=cv2.RETR_TREE,
                                                              method=cv2.CHAIN_APPROX_SIMPLE)

                # 显示轮廓
                rect = []
                for i, c in enumerate(contours):
                    # print("c:\n",c)#c=contours[i]
                    # # 下一层轮廓 蓝色
                    # if (hierarchy[0][i][0] != -1 and hierarchy != []):
                    #     cv2.drawContours(frame, contours, i, (255, 0, 0), 3)

                    # # 上一层轮廓 绿色
                    # if (hierarchy[0][i][1] != -1 and hierarchy != []):
                    #     cv2.drawContours(frame, contours, i, (0,255,0), 3)

                    # #父轮廓 黄色
                    # if (hierarchy[0][i][2] != -1 and hierarchy != []):
                    # cv2.drawContours(frame, contours, i, (0,255,255), 3)
                    # # 子轮廓 红色
                    # if (hierarchy[0][i][3] != -1 and hierarchy != []):
                    #     cv2.drawContours(frame, contours, i, (0, 0, 255), 3)
                    # if c is not None:
                    #     for a in c:
                    #         print("a[0]:",a[0])
                    #         cv2.circle(img, tuple(eval(a[0])), 2, (0, 0, 255))# 在图像中画出特征点，2是圆的半径
                    #         cv2.imshow("img",img)
                    #         cv2.waitKey(1)

                    # 判断轮廓面积
                    if cv2.contourArea(c) > self.area_size:
                        # 判断为运动帧
                        metion_flag = True
                        # 包住轮廓的最小矩形的坐标（x，y为左上点坐标）
                        (x, y, w, h) = cv2.boundingRect(c)

                        rect.append(np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]]))

                if len(rect) == 1:
                    # 若当前帧只找到一个轮廓
                    end_time = time.time()
                    # 计算帧处理时间,s->ms
                    frame_proc_time = (end_time - start_time) * 1000
                    # 统计总时间，更新进度
                    total_frame_time += frame_proc_time
                    progress_value = self.frameNo / total_frame_num * 100
                    # 跨线程发送进度和时间信号，更新UI
                    self.model.progress_signal.emit(progress_value, frame_proc_time)
                    # 刷新页面防止卡顿
                    self.model.view_refresh_signal.emit()
                    continue
                else:
                    for j in range(len(rect)):
                        r0 = cv2.minAreaRect(rect[0])
                        # 循环中是否找到相交点
                        isFind = False
                        for k in range(1, len(rect)):
                            r1 = cv2.minAreaRect(rect[k])
                            # 计算相交区域的顶点
                            retval, intersectingRegion = cv2.rotatedRectangleIntersection(r0, r1)
                            if retval == cv2.INTERSECT_PARTIAL or cv2.INTERSECT_FULL:
                                # 如果相交或内含，由合并点集计算最小正矩形
                                # logger.debug("存在交或含")
                                points = np.vstack((rect[0], rect[k]))
                                (x, y, w, h) = cv2.boundingRect(points)
                                # 列表元素变化
                                rect.pop(0)
                                rect.pop(k - 1)
                                rect.append(np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]]))
                                isFind = True
                                break
                        if isFind == False:
                            # logger.debug("当前没有交或含")
                            rect.append(rect[0])
                            rect.pop(0)

                # 画矩形框
                for r in rect:
                    p = r.tolist()
                    (x, y) = p[0]
                    w = p[3][0] - x
                    h = p[3][1] - y
                    cv2.rectangle(img=foreground, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0),
                                  thickness=3)
                    cv2.rectangle(img=frame, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0), thickness=3)

                # a=cv2.resize(foreground,None,fx=0.5,fy=0.5)
                # cv2.imshow("foreground",a)
                # cv2.waitKey(1)

                # 更新运动帧计数并打印

                if metion_flag and self.frameNo != 1:
                    if motion_start == 0:
                        motion_start = self.frameNo
                        # 写入视频
                        self.writer.write(frame)
                        # 在UI界面显示
                        self.model.frame_signal.emit(frame)

                    elif self.frameNo <= motion_start + motion_count + self.undetected_size:  # 允许n帧以内不连续的误差
                        motion_count += 1
                        # 写入视频
                        self.writer.write(frame)
                        # 在UI界面显示
                        self.model.frame_signal.emit(frame)

                    else:
                        # print("运动帧：%d-%d" % (motion_start, motion_start + motion_count))
                        motion_start, motion_count = 0, 0
                end_time = time.time()
                # 计算帧处理时间,s->ms
                frame_proc_time = (end_time - start_time) * 1000
                # 统计总时间
                total_frame_time += frame_proc_time
                # 跨线程发送进度和时间信号，更新UI
                progress_value = self.frameNo / total_frame_num * 100
                self.model.progress_signal.emit(progress_value, frame_proc_time)
                # 刷新页面防止卡顿
                self.model.view_refresh_signal.emit()
            self.writer.release()
        self.capture.release()
        average_time = total_frame_time / total_frame_num
        self.model.proc_finish_signal.emit(average_time)
        if self._isRunning.isSet() == False:
            # 若因为停止线程而退出
            logger.debug("因为用户停止，线程退出")
        else:
            logger.debug("线程执行完成！")
        return 0

    def pause(self):
        self._isNotPause.clear()  # 设为Flase 让线程阻塞

    def resume(self):
        self._isNotPause.set()  # 设为True 停止阻塞

    def stop(self):
        self._isNotPause.set()  # 从暂停状态恢复
        self._isRunning.clear()  # 设置为False,停止线程

# class GetBackgroundThread(threading.Thread):
#     """
#     获取视频背景的线程类
#     """
#
#     def __init__(self, model):
#         super(GetBackgroundThread, self).__init__()
#         # ui类
#         self.model = model
#         self.view = model.view
#         self.flag = True
#
#     def setInput(self, input):
#         # 输入视频
#         self.input = input
#
#     def setFlag(self, flag):
#         # 是否停止提取背景
#         self.flag = flag
#
#     def setArgs(self, history, threshold, detshadow, backratio):
#         self.mog2_history = history
#         self.mog2_varThreshold = threshold
#         self.DETECT_SHADOWS_FLAG = detshadow
#         self.background_ratio = backratio
#
#     @property
#     def run(self):
#         # 打开视频
#         try:
#             self.capture = cv2.VideoCapture(self.input)
#         except:
#             logger.exception("打开视频异常!")
#         else:
#             logger.debug("成功打开视频!")
#             # 高斯背景建模对象
#         # history：用于训练背景的帧数，默认500，若.apply设置自动更新learningRate(-1)，此时history越大，learningRate越小，背景更新越慢
#         # varThreshold：方差阈值，用于判断当前像素是前景还是背景。一般默认16，如果光照变化明显，如阳光下的水面，建议设为25-36
#         mog2 = cv2.createBackgroundSubtractorMOG2(history=self.mog2_history,
#                                                   varThreshold=self.mog2_varThreshold,
#                                                   detectShadows=self.DETECT_SHADOWS_FLAG)
#
#         # 设置背景比率，取太高多背景模型叠加会模糊（类似滤波），取太低细节会不够（类似腐蚀）
#         mog2.setBackgroundRatio(ratio=self.background_ratio)
#         # 设置高斯模型数
#         mog2.setNMixtures(5)
#
#         if isinstance(self.input, int):
#             # 摄像模式
#             # 读帧并处理
#             self.frameNo = 0  # 第几帧
#             while (True):
#                 if self.mog2_history == self.frameNo:
#                     break
#                 if self.flag==False:
#                     break
#                 flag, frame = self.capture.read()
#                 self.frameNo += 1
#
#                 progress_value = self.frameNo / self.mog2_history * 100
#                 self.view.statusbar.showMessage("处理中: %d%%" % progress_value, 500)
#                 self.view.progressBar.setValue(progress_value)
#
#                 # 混合高斯建模获取背景
#                 rows, cols, ch = frame.shape
#                 self.background = np.zeros(shape=(rows, cols, 3), dtype=np.uint8)
#                 foreground = np.zeros(shape=(rows, cols, 1), dtype=np.uint8)
#
#
#                 # 计算背景前景
#                 mog2.apply(image=frame, fgmask=foreground, learningRate=-1)
#                 mog2.getBackgroundImage(self.background)
#                 # 在UI界面显示
#                 fx=1.0
#                 fy=1.0
#                 pixmap = cv2.resize(self.background, None, fx=fx, fy=fy)
#                 pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                                 QImage.Format_RGB888).rgbSwapped()
#                 self.view.label_showFrame.setPixmap(QPixmap(pixmap))
#                 # fx=1
#                 # fy=1
#                 # # 在UI界面显示
#                 # pixmap = cv2.resize(self.background, None, fx=fx, fy=fy)
#                 # pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                 #                 QImage.Format_RGB888).rgbSwapped()
#                 # self.view.dialog=QDialog()
#                 # self.view.dialog.setObjectName("Dialog")
#                 # self.view.dialog.setWindowTitle("背景图像")
#                 # self.view.verticalLayout_dialog = QtWidgets.QVBoxLayout(self.view.dialog)
#                 # self.view.verticalLayout_dialog.setObjectName("verticalLayout_dialog")
#                 # self.view.label_dialog = QtWidgets.QLabel(self.view.dialog)
#                 # self.view.label_dialog.setText("")
#                 # self.view.label_dialog.setObjectName("label_dialog")
#                 # self.view.verticalLayout_dialog.addWidget(self.view.label_dialog)
#                 # self.view.label_dialog.setPixmap(QPixmap(pixmap))
#                 # self.view.dialog.exec_()
#         else:
#             # 文件模式
#             logger.debug("文件模式")
#             # 读帧并处理
#             self.frameNo = 0  # 第几帧
#
#             while (True):
#                 # 阻塞标志
#                 if self.mog2_history == self.frameNo:
#                     break
#                 if self.flag==False:
#                     break
#                 flag, frame = self.capture.read()
#                 self.frameNo += 1
#
#                 progress_value = self.frameNo / self.mog2_history * 100
#                 self.view.statusbar.showMessage("处理中: %d%%" % progress_value, 500)
#                 self.view.progressBar.setValue(progress_value)
#
#                 # 混合高斯建模获取背景
#                 rows, cols, ch = frame.shape
#                 self.background = np.zeros(shape=(rows, cols, 3), dtype=np.uint8)
#                 foreground = np.zeros(shape=(rows, cols, 1), dtype=np.uint8)
#
#                 # 计算背景前景
#                 mog2.apply(image=frame, fgmask=foreground, learningRate=-1)
#                 mog2.getBackgroundImage(self.background)
#                 logger.debug("在UI界面显示")
#                 # 在UI界面显示
#                 fx=0.5
#                 fy=0.5
#                 pixmap = cv2.resize(self.background, None, fx=fx, fy=fy)
#                 pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                                 QImage.Format_RGB888).rgbSwapped()
#                 self.view.label_showFrame.setPixmap(QPixmap(pixmap))
#
#         logger.debug("准备写入背景")
#         cv2.imwrite("./background.jpg", self.background)
#         self.capture.release()
#         self.model.get_background_success.emit()
#         return 0
#
# class MotionDetBaseOnBackgroundThread(threading.Thread):
#     """
#     动作检测线程类,只是为了和UI分离，并非并发（基于背景减除）
#     """
#
#     def __init__(self, model):
#         super(MotionDetBaseOnBackgroundThread, self).__init__()
#         # 线程标志
#         self._isRunning = threading.Event()  # 用于停止线程
#         self._isRunning.set()  # 设置为True
#         self._isNotPause = threading.Event()  # 用于暂停线程
#         self._isNotPause.set()  # 设置为True
#
#         # ui类
#         self.model = model
#         self.view = model.view
#
#         # 相关参数
#         self.fps = None
#
#     def setDirs(self, input, output_dir_name):
#         # 文件路径
#         self.input = input
#         self.output_dir = output_dir_name
#
#     def setArgs(self,areasize, undetsize):
#         self.area_size = areasize
#         self.undetected_size = undetsize
#
#     def setFPS(self, fps):
#         # 设置帧率
#         self.fps = fps
#
#     @property
#     def run(self):
#         # 打开视频
#         try:
#             self.capture = cv2.VideoCapture(self.input)
#         except:
#             logger.exception("打开视频异常!")
#         else:
#             logger.debug("成功读取视频!")
#
#         # 读取背景图片
#         try:
#             self.background = cv2.imread("./background.jpg")
#         except:
#             logger.exception("打开图片异常!")
#         else:
#             logger.debug("成功读取图片!")
#
#         if isinstance(self.input, int):
#             # 摄像模式
#
#             # 读帧并处理
#             self.frameNo = 0  # 第几帧
#             motion_start, motion_count = 0, 0  # 运动帧计数
#             while (True):
#                 # 阻塞标志
#                 self._isNotPause.wait()
#                 if self._isRunning.isSet() == False:
#                     break
#
#                 flag, frame = self.capture.read()
#                 self.frameNo += 1
#
#                 progress_value = 99
#                 self.view.statusbar.showMessage("处理中: %d%%" % progress_value, 500)
#                 self.view.progressBar.setValue(progress_value)
#
#                 self.foreground=cv2.subtract(frame,self.background)
#
#                 # 在二值前景图中找轮廓，用最小矩形包围
#                 image, contours, hierarchy = cv2.findContours(image=self.foreground,
#                                                               mode=cv2.RETR_TREE,
#                                                               method=cv2.CHAIN_APPROX_SIMPLE)
#                 metion_flag = False
#                 # 显示轮廓
#                 for c in contours:
#                     # 判断轮廓面积
#                     if cv2.contourArea(c) > self.area_size:
#                         metion_flag = True
#                         # 包住轮廓的最小矩形的坐标
#                         (x, y, w, h) = cv2.boundingRect(c)
#
#                         # 画矩形框
#                         cv2.rectangle(img=self.foreground, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0),
#                                       thickness=3)
#                         cv2.rectangle(img=frame, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0), thickness=3)
#
#                 # 更新运动帧计数并打印
#                 fx = 1.0
#                 fy = 1.0
#                 if metion_flag and self.frameNo != 1:
#                     if motion_start == 0:
#                         motion_start = self.frameNo
#
#                         # 在UI界面显示
#                         pixmap = cv2.resize(frame, None, fx=fx, fy=fy)
#                         pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                                         QImage.Format_RGB888).rgbSwapped()
#                         self.view.label_showFrame.setPixmap(QPixmap(pixmap))
#
#                     elif self.frameNo <= motion_start + motion_count + self.undetected_size:  # 允许n帧以内不连续的误差
#                         motion_count += 1
#
#                         # 在UI界面显示
#                         pixmap = cv2.resize(frame, None, fx=fx, fy=fy)
#                         pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                                         QImage.Format_RGB888).rgbSwapped()
#                         self.view.label_showFrame.setPixmap(QPixmap(pixmap))
#
#                     else:
#                         # print("运动帧：%d-%d" % (motion_start, motion_start + motion_count))
#                         motion_start, motion_count = 0, 0
#         else:
#             # 文件模式
#
#             # 读帧并处理
#             self.frameNo = 0  # 第几帧
#             motion_start, motion_count = 0, 0  # 运动帧计数
#
#             # 视频写入
#             self.writer = cv2.VideoWriter()
#             codec = cv2.VideoWriter_fourcc(*'X264')  # X264(压缩率最高)，DIVX(基于MPEG-4标准),MJPG(文件大)，XVID(DIVX的开源改进版)
#             if self.fps == None:
#                 self.fps = self.capture.get(cv2.CAP_PROP_FPS)
#             isColor = True
#             frame_size = (
#                 int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
#
#             # 视频保存路径
#             output_name = osp.splitext(osp.basename(self.input))[0]
#             output_file_name = osp.join(self.output_dir, "gen_" + output_name + ".avi")
#
#             self.writer.open(output_file_name, fourcc=codec, fps=self.fps, frameSize=frame_size, isColor=isColor)
#
#             # 视频帧数
#             total_frame_num = self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
#
#             while (True):
#                 # 阻塞标志
#                 self._isNotPause.wait()
#                 if (self._isRunning.isSet() == False) or (total_frame_num == self.frameNo):
#                     break
#
#                 flag, frame = self.capture.read()
#                 cv2.namedWindow("frame")
#                 fr=cv2.resize(frame, None, fx=0.5, fy=0.5)
#                 cv2.imshow("frame",fr)
#                 cv2.waitKey(1)
#                 self.frameNo += 1
#
#                 progress_value = self.frameNo / total_frame_num * 100
#                 self.view.statusbar.showMessage("处理中: %d%%" % progress_value, 500)
#                 self.view.progressBar.setValue(progress_value)
#                 self.foreground = cv2.subtract(frame, self.background)
#                 cv2.namedWindow("foreground")
#
#                 fo=cv2.resize(self.foreground, None, fx=0.5, fy=0.5)
#                 cv2.imshow("foreground",fo )
#                 cv2.waitKey(1)
#                 #灰度化
#                 foreground_gray=cv2.cvtColor(self.foreground, cv2.COLOR_BGR2GRAY)
#
#                 #自适应阈值化
#                 maxValue = 255
#                 blockSize = 3
#                 C = 4.5
#                 foreground_gray = cv2.adaptiveThreshold(foreground_gray, maxValue,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, blockSize, C)
#                 cv2.namedWindow("foreground_gray")
#                 fog=cv2.resize(foreground_gray, None, fx=0.5, fy=0.5)
#                 cv2.imshow("foreground_gray",fog)
#                 cv2.waitKey(1)
#                 # 在二值前景图中找轮廓，用最小矩形包围
#                 image, contours, hierarchy = cv2.findContours(image=foreground_gray,
#                                                               mode=cv2.RETR_TREE,
#                                                               method=cv2.CHAIN_APPROX_SIMPLE)
#
#                 metion_flag = False
#                 # 显示轮廓
#                 for c in contours:
#                     # 判断轮廓面积
#                     if cv2.contourArea(c) > self.area_size:
#                         metion_flag = True
#                         # 包住轮廓的最小矩形的坐标
#                         (x, y, w, h) = cv2.boundingRect(c)
#
#                         # 画矩形框
#                         cv2.rectangle(img=self.foreground, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0),
#                                       thickness=3)
#                         cv2.rectangle(img=frame, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0), thickness=3)
#
#                 # 更新运动帧计数并打印
#                 fx = 0.5
#                 fy = 0.5
#                 if metion_flag and self.frameNo != 1:
#                     if motion_start == 0:
#                         motion_start = self.frameNo
#                         self.writer.write(self.foreground)
#
#                         # 在UI界面显示
#                         pixmap = cv2.resize(self.foreground, None, fx=fx, fy=fy)
#                         pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                                         QImage.Format_RGB888).rgbSwapped()
#                         self.view.label_showFrame.setPixmap(QPixmap(pixmap))
#
#                     elif self.frameNo <= motion_start + motion_count + self.undetected_size:  # 允许n帧以内不连续的误差
#                         motion_count += 1
#                         self.writer.write(self.foreground)
#
#                         # 在UI界面显示
#                         pixmap = cv2.resize(self.foreground, None, fx=fx, fy=fy)
#                         pixmap = QImage(pixmap, pixmap.shape[1], pixmap.shape[0], pixmap.shape[1] * 3,
#                                         QImage.Format_RGB888).rgbSwapped()
#                         self.view.label_showFrame.setPixmap(QPixmap(pixmap))
#
#                     else:
#                         # print("运动帧：%d-%d" % (motion_start, motion_start + motion_count))
#                         motion_start, motion_count = 0, 0
#                 # 阻塞标志
#                 self._isNotPause.wait()
#             self.writer.release()
#         self.capture.release()
#
#         if self._isRunning.isSet() == False:
#             # 若因为停止线程而退出
#             logger.debug("因为用户停止，线程退出")
#             return 0
#
#         self.model.success_signal.emit()
#         logger.debug("线程执行完成！")
#         return 0
#
#     def pause(self):
#         self._isNotPause.clear()  # 设为Flase 让线程阻塞
#
#     def resume(self):
#         self._isNotPause.set()  # 设为True 停止阻塞
#
#     def stop(self):
#         self._isNotPause.set()  # 从暂停状态恢复
#         self._isRunning.clear()  # 设置为False,停止线程
