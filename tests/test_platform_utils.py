"""
tests/test_platform_utils.py
Checks the OS-specific helpers by pretending to be each OS.
Nothing is really opened: the launchers are replaced with fakes.
"""

import os
import subprocess
import sys

from utils.platform_utils import open_path, shortcut_modifier
from utils.i18n import TRANSLATIONS


class _FakePopen:
    calls = []

    def __init__(self, args):
        _FakePopen.calls.append(args)


def _fake_launchers(monkeypatch):
    _FakePopen.calls = []
    started = []
    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(os, "startfile", started.append, raising=False)
    return started


def test_shortcut_is_command_on_mac(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert shortcut_modifier() == "Command"


def test_shortcut_is_control_on_windows_and_linux(monkeypatch):
    for name in ("win32", "linux"):
        monkeypatch.setattr(sys, "platform", name)
        assert shortcut_modifier() == "Control"


def test_open_path_mac_uses_open(monkeypatch):
    started = _fake_launchers(monkeypatch)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert open_path("/Users/me/backups") is True
    assert _FakePopen.calls == [["open", "/Users/me/backups"]]
    assert started == []


def test_open_path_windows_uses_startfile(monkeypatch):
    started = _fake_launchers(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    assert open_path(r"C:\Users\me\backups") is True
    assert started == [r"C:\Users\me\backups"]
    assert _FakePopen.calls == []


def test_open_path_linux_uses_xdg_open(monkeypatch):
    _fake_launchers(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    assert open_path("/home/me/backups") is True
    assert _FakePopen.calls == [["xdg-open", "/home/me/backups"]]


def test_path_with_quote_stays_one_argument(monkeypatch):
    """The old os.system(f"open '{path}'") broke on a ' in the path."""
    _fake_launchers(monkeypatch)
    monkeypatch.setattr(sys, "platform", "darwin")
    path = "/Users/O'Brien/Documents/BudgetWise/backups"
    open_path(path)
    assert _FakePopen.calls == [["open", path]]


def test_open_path_returns_false_when_launcher_missing(monkeypatch):
    def _missing(args):
        raise FileNotFoundError("xdg-open")
    monkeypatch.setattr(subprocess, "Popen", _missing)
    monkeypatch.setattr(sys, "platform", "linux")
    assert open_path("/home/me/backups") is False


def test_no_language_mentions_macos_in_notifications():
    for lang, strings in TRANSLATIONS.items():
        assert "macOS" not in strings["notifications_sent"], lang


def test_open_folder_failed_exists_in_every_language():
    for lang, strings in TRANSLATIONS.items():
        assert "{}" in strings["open_folder_failed"], lang