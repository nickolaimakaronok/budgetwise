# BudgetWise.spec — PyInstaller build for macOS (.app), Windows and Linux.
#
#   python -m PyInstaller --noconfirm --clean BudgetWise.spec
#
# Output: dist/BudgetWise.app on macOS, dist/BudgetWise/BudgetWise(.exe) elsewhere.
# No paths of a particular computer: everything is found from the project
# folder and the installed packages, so it builds the same on any machine
# and in GitHub Actions.

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

sys.path.insert(0, SPECPATH)                     # SPECPATH = the folder of this file
from utils.constants import APP_NAME, APP_VERSION

ICON = os.path.join(SPECPATH, "assets", "BudgetWise.icns")   # Pillow converts it to .ico on Windows

# customtkinter loads its themes (.json) and fonts from its package folder at runtime
datas = collect_data_files("customtkinter")

# Modules imported in ways PyInstaller can't see, listed by hand:
#  - PIL._tkinter_finder: matplotlib draws charts into Tk through Pillow,
#    which needs it (without it the Analytics page crashed in the built app)
#  - plyer picks its notification module by name at runtime
#    (only Windows/Linux — macOS uses osascript)
hiddenimports = ["PIL._tkinter_finder"]
if sys.platform.startswith("win"):
    hiddenimports += collect_submodules("plyer.platforms.win")
elif sys.platform.startswith("linux"):
    hiddenimports += collect_submodules("plyer.platforms.linux")

a = Analysis(
    [os.path.join(SPECPATH, "main.py")],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,                               # a window app, no terminal next to it
    icon=ICON,
)

coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=ICON,
        bundle_identifier="com.nickolaimakaronok.budgetwise",
        info_plist={
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,     # sharp text on Retina screens
        },
    )