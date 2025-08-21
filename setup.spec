# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[
				 ('plugins/tools/unveilr.exe', 'plugins/tools'),
                 ('gui/*', 'gui/'),
                 ('resources/*', 'resources/'),
                 ('plugins/*', 'plugins/'),
				 ('core/*','core/'),
				 ('icon/*','icon/'),
			],
             hiddenimports=[
                 # PyQt5依赖
                 'PyQt5',
                 'PyQt5.QtWidgets',
                 'PyQt5.QtCore', 
                 'PyQt5.QtGui',
                 # 插件模块
                 'plugins',
                 'plugins.base_plugin',
                 'plugins.directory_scanner',
                 'plugins.security_search',
                 'plugins.wxapp_unpacker',
                 'plugins.sensitive_info_scanner',
                 'plugins.frontend_downloader',
                 'plugins.office_tools',
                 'plugins.image_processor',
                 'plugins.text_processor',
                 # 核心模块
                 'core',
                 'core.plugin_manager',
                 'core.scanner',
                 'core.utils',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=['PyQt6'],  # 添加这一行来排除PyQt6
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Ash',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='icon/Ash.ico')