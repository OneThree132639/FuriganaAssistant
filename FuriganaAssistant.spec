# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['main.py'],
    pathex=["."],
    binaries=[],
    datas=[("./resources", "resources")],
    hiddenimports=["Utils"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    exclude_binaries=True,
    name='FuriganaAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="./resources/icon.icns",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FuriganaAssistant',
)
app = BUNDLE(
    coll,
    name='FuriganaAssistant.app',
    icon="./resources/icon.icns",
    bundle_identifier="com.onethree.FuriganaAssistant.app",
    info_plist={
        'CFBundleName': 'FuriganaAssistant',
        'CFBundleDisplayName': 'Furigana Assistant',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',  # 标准应用类型
        'CFBundleSignature': '????',    # 通用签名
        'NSHighResolutionCapable': True,  # 支持 Retina 显示
        'NSHumanReadableCopyright': '© 2026 OneThree',  # 可选：版权信息
        # 如需文件拖拽支持，取消注释以下行：
        # 'CFBundleDocumentTypes': [
        #     {
        #         'CFBundleTypeName': 'Text File',
        #         'CFBundleTypeExtensions': ['txt', 'md'],
        #         'CFBundleTypeRole': 'Editor'
        #     }
        # ]
    },
)
