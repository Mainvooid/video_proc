# -*- mode: python -*-

block_cipher = None


a = Analysis(['..\\main.py'],
             pathex=['D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\venv\\Lib\\site-packages\\PyQt5\\Qt\\bin', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\res', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\lib', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\view', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\model', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\core\\control', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\conf', 'D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\build'],
             binaries=[('D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\lib\\opencv_ffmpeg400_64.dll', './'), ('D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\lib\\openh264-1.8.0-win64.dll', './')],
             datas=[('D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\conf\\settings.json', './conf')],
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
          [],
          exclude_binaries=True,
          name='main',
          debug=False,
          strip=False,
          upx=True,
          console=True , version='D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\res\\file_version_info.txt', icon='D:\\ProgramSourceCode\\PycharmProjects\\video_proc\\res\\main.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='main')
