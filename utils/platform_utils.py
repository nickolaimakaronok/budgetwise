"""
utils/platform_utils.py
The few things that differ between macOS, Windows and Linux.

All OS checks live here, so the rest of the app never looks at
sys.platform itself.
"""

import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


def is_mac() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")

APP_FOLDER   = "BudgetWise"
DATA_DIR_ENV = "BUDGETWISE_DATA_DIR"


def app_data_dir() -> str:
    """
    Folder for the database, backups and log — the place each OS keeps
    app data in (not synced to iCloud/OneDrive, no permission prompts):
      macOS:   ~/Library/Application Support/BudgetWise
      Windows: BudgetWise in %LOCALAPPDATA% (C:/Users/<name>/AppData/Local)
      Linux:   ~/.local/share/BudgetWise (or $XDG_DATA_HOME/BudgetWise)
    The BUDGETWISE_DATA_DIR environment variable overrides it (tests use this).
    """
    custom = os.environ.get(DATA_DIR_ENV)
    if custom:
        return os.path.abspath(os.path.expanduser(custom))
    home = os.path.expanduser("~")
    if is_mac():
        base = os.path.join(home, "Library", "Application Support")
    elif is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, APP_FOLDER)


def legacy_data_dir() -> str:
    """Where versions up to 1.8 kept their data."""
    return os.path.join(os.path.expanduser("~"), "Documents", APP_FOLDER)

def shortcut_modifier() -> str:
    """Tk name of the shortcut key: Command (⌘) on macOS, Control elsewhere."""
    return "Command" if is_mac() else "Control"


def open_path(path: str) -> bool:
    """
    Opens a folder or file in the system file manager:
    Finder on macOS, Explorer on Windows, the default file manager on Linux.
    Returns False if it couldn't be opened.
    """
    try:
        if is_windows():
            os.startfile(path)
        elif is_mac():
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except OSError as e:
        logger.warning(f"Could not open {path}: {e}")
        return False




def show_notification(title: str, message: str) -> bool:
    """
    Shows a system notification. Returns True if the system accepted it.
      macOS:   osascript — built into every Mac, needs no extra packages
               (plyer needs pyobjus there and an API deprecated since macOS 11)
      Windows: plyer → notification balloon / toast
      Linux:   plyer → D-Bus or notify-send
    """
    try:
        if is_mac():
            # title/message go in as separate arguments (argv), not glued into
            # the script text, so quotes in a category name can't break it
            subprocess.run(
                ["osascript",
                 "-e", "on run argv",
                 "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
                 "-e", "end run",
                 title, message],
                check=True, capture_output=True, timeout=10,
            )
        else:
            from plyer import notification
            notification.notify(title=title, message=message,
                                app_name="BudgetWise", timeout=8)
        return True
    except Exception as e:
        logger.warning(f"Could not show notification: {e}")
        return False