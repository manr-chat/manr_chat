# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('manr', 'manr')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DAnimation',
        'PySide6.QtDataVisualization',
        'PySide6.QtCharts',
        'PySide6.QtQuick',
        'PySide6.QtQuick3D',
        'PySide6.QtQml',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtSensors',
        'PySide6.QtLocation',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Exclude PySide6 translations
def filter(f):
    return f.startswith('PySide6/Qt/translations') or \
           f.startswith('PySide6\\Qt\\translations') or \
           'qtwebengine_devtools_resources' in f or \
           f == '.gitignore' or \
           f == '__pycache__'

a.datas = [f for f in a.datas if not filter(f[0])]

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='manr',
    icon='manr/resources/img/icon.ico',
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
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='manr',
)
