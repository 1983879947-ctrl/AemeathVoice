# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置 - 打包 AemeathVoice EXE

策略：把 api/、scripts/、web/、gpt_sovits/、text/ 全部复制到 _internal/AV/
（避免和 Python module 名同名冲突：api、scripts、web 在某些库中也是 module）
"""
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve()

# 内部目录：_internal/AV/（统一前缀）
INT = "AV"

# ============== 数据文件 ==============
datas = [
    # 用绝对路径
    (str(ROOT / "api"),                f"{INT}/api"),
    (str(ROOT / "scripts"),            f"{INT}/scripts"),
    (str(ROOT / "web"),                f"{INT}/web"),
    # 精简版 GPT-SoVITS 推理代码
    (str(ROOT / "AemeathVoice_Portable" / "gpt_sovits"), f"{INT}/gpt_sovits"),
    (str(ROOT / "AemeathVoice_Portable" / "text"),        f"{INT}/text"),
    # launcher
    (str(ROOT / "AemeathVoice.py"),    f"{INT}/AemeathVoice.py"),
]

# ============== 隐藏导入 ==============
hiddenimports = []
hiddenimports += collect_submodules('gpt_sovits')
hiddenimports += collect_submodules('gpt_sovits.AR')
hiddenimports += collect_submodules('gpt_sovits.module')
hiddenimports += collect_submodules('gpt_sovits.text')
hiddenimports += collect_submodules('gpt_sovits.feature_extractor')

a = Analysis(
    ['AemeathVoice.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy.tests', 'scipy.tests',
        'pandas', 'pytest', 'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AemeathVoice',
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
    icon=None,
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AemeathVoice',
)