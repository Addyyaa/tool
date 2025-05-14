# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 收集资源和隐式导入
datas = collect_data_files('PIL') + collect_data_files('customtkinter')
hiddenimports = collect_submodules('PIL') + collect_submodules('customtkinter')

a = Analysis(
    ['image_compress.py'],
    pathex=[],
    binaries=[],
    datas=datas,  # ✅ 使用上方收集的 datas
    hiddenimports=hiddenimports,  # ✅ 使用上方收集的 hiddenimports
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='image_compress',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # ✅ 如果你是 GUI 程序建议改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
