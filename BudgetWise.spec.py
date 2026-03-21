# BudgetWise.spec
import os
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.dirname(os.path.abspath(SPEC))

# Collect numpy and matplotlib fully — fixes "cannot load module twice" error
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
mpl_datas, mpl_binaries, mpl_hiddenimports = collect_all('matplotlib')

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    hiddenimports=[
                      'customtkinter',
                      'PIL',
                      'PIL._tkinter_finder',
                      'peewee',
                      'plyer',
                      'plyer.platforms.macosx.notification',
                      'numpy._core._exceptions',
                      'numpy._core._multiarray_umath',
                      'numpy._core.multiarray',
                      'numpy._core._methods',
                      'numpy._core.numeric',
                      'numpy._core.umath',
                      'numpy.lib.stride_tricks',
                  ] + numpy_hiddenimports + mpl_hiddenimports,
    datas=[
        ('/Users/nickolaimakaronok/Documents/DevelopAndProgramming/budgetwise/.venv/lib/python3.12/site-packages/customtkinter',
         'customtkinter/'),
    ] + numpy_datas + mpl_datas,
    binaries=[] + numpy_binaries + mpl_binaries,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['conda', 'conda_package_handling', 'conda_env'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BudgetWise',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/BudgetWise.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BudgetWise',
)

app = BUNDLE(
    coll,
    name='BudgetWise.app',
    icon='assets/BudgetWise.icns',
    bundle_identifier='com.budgetwise.app',
    info_plist={
        'CFBundleName':               'BudgetWise',
        'CFBundleDisplayName':        'BudgetWise',
        'CFBundleVersion':            '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable':    True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion':     '10.13.0',
    },
)