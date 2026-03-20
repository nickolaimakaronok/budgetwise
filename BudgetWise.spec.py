# BudgetWise.spec
# PyInstaller build configuration for macOS .app
# Run with: pyinstaller BudgetWise.spec

import os
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE

# Project root directory
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    # Entry point
    [os.path.join(ROOT, 'main.py')],

    pathex=[ROOT],

    # All packages that need to be bundled
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'peewee',
        'plyer',
        'plyer.platforms.macosx.notification',
    ],

    # Data files to include (non-Python files)
    datas=[
        (
        '/Users/nickolaimakaronok/Documents/DevelopAndProgramming/budgetwise/.venv/lib/python3.12/site-packages/customtkinter',
        'customtkinter/'),
    ],

    # No extra binaries needed
    binaries=[],

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
    [],
    exclude_binaries=True,
    name='BudgetWise',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # No terminal window on launch
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

# Create the .app bundle
app = BUNDLE(
    coll,
    name='BudgetWise.app',
    icon='assets/BudgetWise.icns',
    bundle_identifier='com.budgetwise.app',

    # macOS app metadata
    info_plist={
        'CFBundleName':             'BudgetWise',
        'CFBundleDisplayName':      'BudgetWise',
        'CFBundleVersion':          '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable':  True,
        'NSRequiresAquaSystemAppearance': False,  # supports dark mode
        'LSMinimumSystemVersion':   '10.13.0',
    },
)