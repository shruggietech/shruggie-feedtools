# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\shruggie_feedtools\\gui\\app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/shruggie_feedtools/gui', 'shruggie_feedtools/gui'),
        ('brand/favicon.ico', 'brand'),
        ('brand', 'brand'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='shruggie-feedtools-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='brand/favicon.ico',
)
