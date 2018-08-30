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

from src.control.logger import *
from src.control import settings
import init_path


# todo:使用QThread替换threading.Thread
class MotionDetThread(threading.Thread):
    """
    动作检测线程类,只是为了和UI分离，并非并发
    """

    def __init__(self, model):
        super(MotionDetThread, self).__init__()
        # 线程控制标志
        self._isRunning = threading.Event()  # 用于停止线程
        self._isRunning.set()  # 设置为True
        self._isNotPause = threading.Event()  # 用于暂停线程
        self._isNotPause.set()  # 设置为True

        # ui类
        self.model = model

        # 相关参数
        self.fps = None
        self.LearningRate = -1

    def set_dirs(self, video_input, output_dir_name):
        # 文件路径
        self.input = video_input
        self.output_dir = output_dir_name

    # TODO 使用*args 和 **kwargs替换
    def set_args(self, history, threshold, area_size, background_ratio, undetected_size, blur_size, is_auto_back,
                 has_det_shadow, det_shadow_var, fore_proc, erode_shape):
        self.mog2_history = history
        self.mog2_varThreshold = threshold
        self.DETECT_SHADOWS_FLAG = has_det_shadow
        self.background_ratio = background_ratio
        self.medianBlur_ksize = blur_size
        self.FORE_PROC_FLAG = fore_proc
        self.e_shape = erode_shape
        self.d_shape = erode_shape
        self.area_size = area_size
        self.undetected_size = undetected_size
        self.AUTO_BACK_FLAG = is_auto_back
        self.det_shadow_var = det_shadow_var

    def set_fps(self, fps):
        # 设置帧率
        self.fps = fps

    def set_learningrate(self, learningrate):
        # 设置帧率
        self.LearningRate = learningrate

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
        # KNN 综合速度快20-30%，但是精度相对低一些，需要调试
        # self.knn_history=100
        # mog2=cv2.createBackgroundSubtractorKNN(history=self.knn_history,detectShadows=True)

        # 设置背景比率，取太高多背景模型叠加会模糊（类似滤波），取太低细节会不够（类似腐蚀）
        mog2.setBackgroundRatio(ratio=self.background_ratio)

        # 设置高斯模型数
        mog2.setNMixtures(5)

        # 阴影阈值
        if self.DETECT_SHADOWS_FLAG:
            mog2.setShadowThreshold(self.det_shadow_var)

        # 统计时间
        total_frame_time = 0
        # 记录视频帧数
        total_frame_num = -1

        # 读帧并处理
        frame_no = 0  # 第几帧
        learning_frame_no = 0  # 记录背景更新帧数
        is_first_learn = True  # 是否是第一次更新背景
        motion_start, motion_count = 0, 0  # 运动帧计数

        if isinstance(self.input, int):
            # 摄像模式
            logger.debug("摄像模式")

        else:
            # 文件模式
            logger.debug("文件模式")

            # 视频写入对象
            self.writer = cv2.VideoWriter()

            # 编解码器
            codec = cv2.VideoWriter_fourcc(*'X264')  # X264(压缩率最高)，DIVX(基于MPEG-4标准),MJPG(文件大)，XVID(DIVX的开源改进版)
            # codec = -1 # 从系统中选取

            # 视频帧率
            if self.fps is None:
                self.fps = self.capture.get(cv2.CAP_PROP_FPS)

            # 视频通道数
            is_color = True

            # 视频大小
            frame_size = (
                int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))

            # 视频保存路径
            output_name = osp.splitext(osp.basename(self.input))[0]
            output_file_name = osp.join(self.output_dir, "gen_" + output_name + ".avi")

            # 打开文件准备写入
            self.writer.open(output_file_name, fourcc=codec, fps=self.fps, frameSize=frame_size, isColor=is_color)

            # 视频帧数
            total_frame_num = self.capture.get(cv2.CAP_PROP_FRAME_COUNT)

        while True:
            start_time = time.time()

            # 线程阻塞标志
            self._isNotPause.wait()
            if (self._isRunning.isSet() is False) or (total_frame_num == frame_no):
                break

            if (is_first_learn or self.AUTO_BACK_FLAG) and learning_frame_no == self.mog2_history:
                # 保存第一次产生的背景，保存自动更新背景第一次产生背景之后的背景（非自动更新就不保存）

                # 重置背景更新帧计数
                learning_frame_no = 0

                # 重置标识
                is_first_learn = False

                # 若自动背景更新未开启则停止背景更新
                if not self.AUTO_BACK_FLAG:
                    self.LearningRate = 0

                # 保存的背景路径
                back_img_path = osp.join(init_path.project_dir, "data\\background.jpg")

                # 目录不存在则创建目录(为pyinstaller的兼容，正常应自动创建)
                if not osp.exists(osp.split(back_img_path)[0]):
                    os.mkdir(osp.split(back_img_path)[0])

                # 保存图片
                ok = cv2.imwrite(back_img_path, mog2.getBackgroundImage())
                if ok:
                    self.model.back_ready_signal.emit()
                    logger.debug("背景保存成功")
                else:
                    logger.debug("背景保存失败")

            # 读取视频帧
            ok, frame = self.capture.read()
            if not ok:
                logger.exception("读取视频异常!")

            frame_no += 1
            learning_frame_no += 1

            # # 2层降采样可以提高20%效率，写入视频有BUG
            # frame=cv2.pyrDown(frame)
            # frame = cv2.pyrDown(frame)

            # 混合高斯建模获取前景与背景
            try:
                rows, cols, ch = frame.shape
            except AttributeError:
                logger.debug("读取帧大小错误或未能识别摄像头")
                # TODO 错误信息显示，emit发送信号
            else:
                self.foreground = np.zeros(shape=(rows, cols, 1), dtype=np.uint8)

            # 计算前景蒙版,动态设置学习率，为0时背景不更新，为1时逐帧更新，默认为-1，即算法自动更新；
            mog2.apply(image=frame, fgmask=self.foreground, learningRate=self.LearningRate)

            if settings.isDEBUG:
                a0 = cv2.resize(self.foreground, None, fx=0.25, fy=0.25)
                cv2.imshow("0 foreground", a0)
                cv2.waitKey(1)

            # 二值化阈值处理，前景掩码含有前景的白色值以及阴影的灰色值，开启阴影检测后，在阈值化图像中，将非纯白色（244~255）的所有像素都设为0，而不是255
            if self.DETECT_SHADOWS_FLAG:
                self.foreground = cv2.threshold(self.foreground, 244, 255, cv2.THRESH_BINARY)[1]

                if settings.isDEBUG:
                    a1 = cv2.resize(self.foreground, None, fx=0.25, fy=0.25)
                    cv2.imshow("1 after threshold", a1)
                    cv2.waitKey(1)

            # 中值滤波
            cv2.medianBlur(src=self.foreground, dst=self.foreground, ksize=self.medianBlur_ksize)

            if settings.isDEBUG:
                a2 = cv2.resize(self.foreground, None, fx=0.25, fy=0.25)
                cv2.imshow("2 after medianBlur", a2)
                cv2.waitKey(1)

            # 前景处理过程，形态学腐蚀，膨胀
            if self.FORE_PROC_FLAG is True:
                cv2.dilate(src=self.foreground, dst=self.foreground, kernel=np.ones(shape=self.d_shape, dtype=np.uint8))
                cv2.erode(src=self.foreground, dst=self.foreground, kernel=np.ones(shape=self.e_shape, dtype=np.uint8))

                if settings.isDEBUG:
                    a3 = cv2.resize(self.foreground, None, fx=0.25, fy=0.25)
                    cv2.imshow("3 after dilate erode", a3)
                    cv2.waitKey(1)

                # # 创建一个3*3的椭圆核
                # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                # # 形态学开运算去噪点
                # foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)

            # TODO 对二值图进行更有效的滤波
            # 在二值前景图中找轮廓，用最小矩形包围,hierarchy[i][.]:下一条0；前一条1,第一条子轮廓2，父轮廓3
            image, contours, hierarchy = cv2.findContours(image=self.foreground,
                                                          mode=cv2.RETR_TREE,
                                                          method=cv2.CHAIN_APPROX_SIMPLE)
            # 下面俩步为了增强光照鲁棒性，有时候轮廓的行为像噪声，可以尝试减除
            # TODO 提高对光照的鲁棒性，有时候轮廓的行为像噪声，可以尝试减除，或者判断当小轮廓太多时重新启用背景更新
            for i, c in enumerate(contours):
                # 面积太小的轮廓当成噪音
                if cv2.contourArea(c) < self.area_size:
                    # 上一层轮廓 绿色
                    if hierarchy[0][i][1] != -1 and hierarchy != []:
                        cv2.drawContours(image=self.foreground, contours=contours, contourIdx=i, color=(0, 255, 0),
                                         thickness=3)

                    # 父轮廓 黄色
                    if hierarchy[0][i][2] != -1 and hierarchy != []:
                        cv2.drawContours(image=self.foreground, contours=contours, contourIdx=i, color=(0, 255, 255),
                                         thickness=3)

            # cv2.drawContours(self.foreground, contours, -1, (0, 0, 255), 1, hierarchy=hierarchy)  # 会抵消掉所有轮廓，有一定自适应去噪效果（可以增强光照鲁棒性）

            if settings.isDEBUG:
                a4 = cv2.resize(self.foreground, None, fx=0.25, fy=0.25)
                cv2.imshow("4 after drawContours", a4)
                cv2.waitKey(1)

            # 去掉轮廓本身的噪音后重新计算轮廓
            image, contours, hierarchy = cv2.findContours(image=self.foreground,
                                                          mode=cv2.RETR_TREE,
                                                          method=cv2.CHAIN_APPROX_SIMPLE)

            # 显示轮廓
            rect = []
            metion_flag = False

            # 判断当前帧是否是运动帧
            for i, c in enumerate(contours):
                # 判断轮廓面积
                if cv2.contourArea(c) > self.area_size:
                    # TODO 计算轮廓，判断运动帧，是否可以采用图像金字塔先降采样
                    # 判断为运动帧
                    metion_flag = True

                    # 包住轮廓的最小矩形的坐标（x，y为左上点坐标）
                    (x, y, w, h) = cv2.boundingRect(c)

                    # 列表追加符合阈值的轮廓
                    rect.append(np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]]))

                    if settings.isDEBUG:
                        # DEBUG模式，画出相关轮廓
                        # TODO 不画已经被剔除的轮廓
                        # # 下一层轮廓 蓝色
                        # if (hierarchy[0][i][0] != -1 and hierarchy != []):
                        #     cv2.drawContours(frame, contours, i, (255, 0, 0), 3)

                        # 上一层轮廓 绿色
                        if hierarchy[0][i][1] != -1 and hierarchy != []:
                            cv2.drawContours(image=frame, contours=contours, contourIdx=i, color=(0, 255, 0),
                                             thickness=3)

                        # 父轮廓 黄色
                        if hierarchy[0][i][2] != -1 and hierarchy != []:
                            cv2.drawContours(image=frame, contours=contours, contourIdx=i, color=(0, 255, 255),
                                             thickness=3)

                        # # 子轮廓 红色
                        # if (hierarchy[0][i][3] != -1 and hierarchy != []):
                        #     cv2.drawContours(frame, contours, i, (0, 0, 255), 3)

            if not metion_flag:
                # 若当前帧非运动帧，跳到下一帧
                logger.debug("当前帧非运动帧")

                end_time = time.time()

                # 计算帧处理时间,s->ms
                frame_proc_time = (end_time - start_time) * 1000

                # 统计总时间，更新进度
                total_frame_time += frame_proc_time

                # 跨线程发送进度和时间信号，更新UI
                if isinstance(self.input, int):
                    progress_value = -1
                    self.model.progress_signal.emit(progress_value, frame_proc_time)
                else:
                    progress_value = frame_no / total_frame_num * 100
                    self.model.progress_signal.emit(progress_value, frame_proc_time)

                # 刷新页面防止卡顿
                self.model.view_refresh_signal.emit()

                continue

            elif len(rect) == 1:
                # 若当前帧只有一个轮廓
                logger.debug("当前帧只有一个轮廓")
                pass
            else:
                # 合并列表中所有相交轮廓

                # 连续未相交的计数
                unintersected_num = 0

                while True:
                    if unintersected_num >= len(rect) - 1:
                        # 连续len-1长度内未相交判定结束
                        break

                    # 寻找最小矩形区域，返回旋转矩形：((中心点坐标)，(高宽），旋转角度)
                    r0 = cv2.minAreaRect(rect[0])  # input numpy array or scalar

                    # 循环中是否找到相交点的标记
                    is_find = False

                    # 从列表第2位开始搜索直到相交
                    for k in range(1, len(rect)):
                        # 寻找最小旋转矩形
                        rk = cv2.minAreaRect(rect[k])

                        # 碰撞检测,判断是否相交，并计算相交区域的顶点（冗余）,输出左上,右下，右上,左下点坐标
                        retval, intersecting_region = cv2.rotatedRectangleIntersection(r0, rk)

                        # if True 时，以所有前景合成一个框
                        if retval != cv2.INTERSECT_NONE:
                            # 如果相交或内含，合并点集
                            points = np.vstack((rect[0], rect[k]))

                            # 计算最小正矩形（左上角坐标+宽高）
                            (x, y, w, h) = cv2.boundingRect(points)

                            # # TODO 边界处理,4个边界，因矩形框可能溢出画面，
                            # if x < 0:
                            #     x = 0
                            # if y < 0:
                            #     y = 0

                            # 列表元素变化
                            rect.pop(k)
                            rect.pop(0)

                            # 追加合并的矩形
                            rect.append(np.array([[x, y], [x + w, y], [x, y + h], [x + w, y + h]]))

                            is_find = True
                            unintersected_num = 0

                            break

                    if not is_find:
                        # logger.debug("当前没有交或含")

                        # 0位移到末尾参与后面可能发生的合并
                        rect.append(rect[0])
                        rect.pop(0)

                        # 未相交计数
                        unintersected_num += 1

            # 处理合并完轮廓后，绘制矩形框
            for r in rect:
                temp = r.tolist()
                (x, y) = temp[0]
                w = temp[3][0] - x
                h = temp[3][1] - y
                cv2.rectangle(img=frame, pt1=(x, y), pt2=(x + w, y + h), color=(255, 255, 0), thickness=3)

            # 更新运动帧计数并打印
            if metion_flag and frame_no != 1:
                if motion_start == 0:
                    motion_start = frame_no

                    # 在UI界面显示
                    self.model.frame_signal.emit(frame)

                    # 文件模式，写入视频
                    if not isinstance(self.input, int):
                        self.writer.write(frame)

                elif frame_no <= motion_start + motion_count + self.undetected_size:  # 允许n帧以内不连续的误差
                    motion_count += 1

                    # 在UI界面显示
                    self.model.frame_signal.emit(frame)

                    # 文件模式，写入视频
                    if not isinstance(self.input, int):
                        self.writer.write(frame)

                else:
                    # 连续N帧内未检测到运动，重新计数运动帧
                    logger.debug("运动帧：%d-%d" % (motion_start, motion_start + motion_count))
                    motion_start, motion_count = 0, 0

            # 结束当前帧计时
            end_time = time.time()

            # 计算帧处理时间,s->ms
            frame_proc_time = (end_time - start_time) * 1000

            # 统计总时间
            total_frame_time += frame_proc_time

            # 跨线程发送进度和时间信号，更新UI
            if isinstance(self.input, int):
                progress_value = 99
                self.model.progress_signal.emit(progress_value, frame_proc_time)
            else:
                progress_value = frame_no / total_frame_num * 100
                self.model.progress_signal.emit(progress_value, frame_proc_time)

            # 刷新页面防止卡顿
            self.model.view_refresh_signal.emit()

        # 完成处理，释放相关资源
        if not isinstance(self.input, int):
            self.writer.release()
        self.capture.release()
        cv2.destroyAllWindows()

        # 计算平均处理时间
        average_time = total_frame_time / frame_no

        # 发送处理完成信号
        self.model.proc_finish_signal.emit(average_time)

        logger.debug("帧平均处理时间:{}".format(average_time))

        if not self._isRunning.isSet():
            logger.debug("因为用户停止，线程退出")
        else:
            logger.debug("线程执行完成！")

        return 0

    def pause(self):
        # 设为False 让线程阻塞
        self._isNotPause.clear()

    def resume(self):
        # 设为True 停止阻塞
        self._isNotPause.set()

    def stop(self):
        # 从暂停状态恢复
        self._isNotPause.set()

        # 设置为False,停止线程
        self._isRunning.clear()
