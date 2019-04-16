# [video_proc](https://github.com/Mainvooid/video_proc)
[![LICENSE](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/996icu/996.ICU/blob/master/LICENSE)
![video_proc](icon.svg)

## 介绍

一个运动视频摘要Demo,基于PyQt5以及OpenCV.打包工具Pyinstaller.也可以作为PyQt5项目的模板.

## 目录结构
```
.        
├─bin                     - 可执行文件目录
│  └─main                     - Pyinstaller打包结果目录                 
├─build                   - 构建目录
│  │  main.spec               - Pyinstaller配置文件(需要修改)
│  └─main                     - Pyinstaller打包临时目录
├─conf                    - 配置目录
│     resource.qrc            - PyQt5资源配置
│     settings.json           - 算法参数配置
│     window_status.ini       - 窗口位置配置
│      
├─data                    - 数据目录(存放视频数据或者建模出来的背景图片)
├─docs                    - 项目文档目录    
├─lib                     - 第三方库目录
├─log                     - 日志文件目录
├─res                     - 应用程序资源目录
├─src                     - 源码目录
   ├─control                  - 控制器目录
   │  │  logger.py               - 日志处理
   │  │  main_controller.py      - 窗口控制
   │  └─ settings.py             - 项目设置
   ├─model                    - 模型目录
   │  │  main_mod.py             - 主界面模型
   │  └─ proc_thread.py          - 线程处理
   └─view                     - 视图目录
      │  dialog.ui               - 帮助页视图
      │  main.ui                 - 主界面视图
      │  resource_rc.py          - 项目图标资源
      │  ui_dialog.py            - 帮助页布局
      └─ ui_main.py              - 主界面布局
```
## 应用界面
![image_1](docs/image_1.jpg)
![image_2](docs/image_2.jpg)
![image_3](docs/image_3.png)
