# -*- mode: python -*-

block_cipher = None


a = Analysis(['..\\core\\main.py'],
             pathex=['D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\venv\\Lib\\site-packages\\PyQt5\\Qt\\bin', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\res', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\conf', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\control', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\model', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\view', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\view', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\log', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\build'],
             binaries=[('D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\venv\\Lib\\site-packages\\cv2\\opencv_ffmpeg341_64.dll', './cv2')],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='main',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , version='D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\res\\file_version_info.txt', icon='D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\res\\main.ico')
