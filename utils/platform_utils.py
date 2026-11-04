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