# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['lecooTool2.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('config.ini', '.'),  # Include config file
        ('pkids/*.ini', 'pkids')  # Include pkids directory .ini files
    ],
    hiddenimports=['lecoo_pkidreader', 'pandas', 'xlrd', 'requests', 'numpy.linalg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'sympy', 'networkx', 'filelock', 'fsspec', 'Jinja2', 'MarkupSafe',
        'mpmath', 'tensorflow', 'PyQt5', 'django', 'flask', 'pytorch', 'seaborn',
        'matplotlib', 'scipy', 'numpy.fft'
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lecooTool2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
