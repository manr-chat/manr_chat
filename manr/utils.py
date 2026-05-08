#!/usr/bin/env python3

from contextlib import contextmanager
import os
import sys
import time
import math
from pathlib import Path
from typing import Generator

from PySide6 import QtCore
from PySide6.QtWidgets import QApplication

def flatten(xss):
    return [x for xs in xss for x in xs]

def unique_list(l):
    from collections import OrderedDict
    return list(OrderedDict.fromkeys(l))

def load_json(filename):
    import json
    with open(filename, encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data, indent=2):
    import json
    contents = json.dumps(data, indent=indent)
    file = QtCore.QSaveFile(filename)
    file.setDirectWriteFallback(True)
    file.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    file.write(contents.encode())
    file.commit()

def profile(*args, start=None):
    #return
    t = time.time()
    diff_str = ""
    if start:
        if type(start) == float:
            diff_str = time_diff(t-start)
        else:
            diff_str = ", ".join([time_diff(t-x) for x in start])
        diff_str = "(" + diff_str + ")"
    print(*args, time_str(t), diff_str)
    return t

def time_str(t=None):
    if not t:
        t = time.time()
    lt = time.localtime(t)
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}.{int(t%1*1000):03d}"

def time_diff(d):
    return f"{d:.3f}s"

def mightBeTimeStamp(v):
    return type(v) is int and v > 1_700_000_000_000 and v < 2_000_000_000_000

def formatBool(b):
    return "yes" if b else "no"

def decorateLabel(label, isFavorite, isOnline):
    if isFavorite:
        label = "⭐️ " + label
    if isOnline:
        label = "🟢 " + label
    return label

def isRecent(t, minutes=10):
    if t is None:
        return False
    if t > 2_000_000_000: # convert from ms to s
        t /= 1000
    now = time.time()
    diff = int(now - t)
    return diff < minutes*60

def formatTimeStampMonth(t):
    if t is None:
        return ""
    if t > 2_000_000_000: # convert from ms to s
        t /= 1000
    lt = time.localtime(t)
    return time.strftime("%B %Y", lt)

def formatTimeStamp(t):
    if t is None:
        return ""
    if t > 2_000_000_000: # convert from ms to s
        t /= 1000
    now = time.time()
    diff = abs(int(now - t))
    future = now < t
    difftext = ""
    date = time.ctime(t)
    if diff < 24*3600:
        h = math.floor(diff / 3600)
        min = math.floor(diff / 60) % 60
        difftext = f"{h}h{min}min" if h > 0 else f"{min}min"
        if future:
            return f"in {difftext} ({date})"
        return f"{difftext} ago ({date})"
    return date


@contextmanager
def override_cursor(process_events = True,
                    cursor: QtCore.Qt.CursorShape = QtCore.Qt.CursorShape.WaitCursor) -> Generator[None, None, None]:
    guard = QApplication.setOverrideCursor(cursor)
    if process_events:
        QApplication.processEvents()
    try:
        yield
    finally:
        guard.restoreOverrideCursor() # type: ignore

def get_app_dirs():
    appname = "manr_chat"
    if sys.platform == "win32":
        appdata    = Path(os.environ["APPDATA"])
        localappdata = Path(os.environ.get("LOCALAPPDATA") or os.environ["APPDATA"])
        config_dir = appdata / appname
        #data_dir   = appdata / appname
        cache_dir  = localappdata / appname / "cache"
    else:
        # Follow XDG spec with correct fallbacks
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        #xdg_data   = os.environ.get("XDG_DATA_HOME")
        xdg_cache  = os.environ.get("XDG_CACHE_HOME")
        home = Path.home()
        config_dir = Path(xdg_config) / appname if xdg_config else home / ".config" / appname
        #data_dir   = Path(xdg_data)   / appname if xdg_data   else home / ".local" / "share" / appname
        cache_dir  = Path(xdg_cache)  / appname if xdg_cache  else home / ".cache" / appname
    for d in (config_dir, cache_dir):
        d.mkdir(parents=True, exist_ok=True)
    return config_dir, cache_dir


def get_config_dir() -> Path:
    config_dir, cache_dir = get_app_dirs()
    return config_dir

def get_cache_dir() -> Path:
    config_dir, cache_dir = get_app_dirs()
    return cache_dir
