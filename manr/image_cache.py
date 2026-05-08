#!/usr/bin/env python3

import re
import pycurl
from enum import Enum
from pathlib import Path
from io import BytesIO
from dataclasses import dataclass

from PySide6 import QtWidgets  # not needed, only here to prevent a crash in import below, most likely due to a botched install of PySide6
from PySide6.QtCore import (QObject, QRunnable, Signal, Slot)

from .utils import *

cdn_base_url = "https://cdns.grindr.com/"
cdn_images = cdn_base_url + "images/"
cdn_gaymoji = cdn_base_url + "grindr/chat/"
cache_root = get_cache_dir()
cookie_file = str(cache_root / "cookies.txt")

MediaType = Enum("MediaType", [("profile", 1), ("thumb", 2), ("gaymoji", 3), ("url", 4)]) 

@dataclass
class MediaDescription:
    name: str
    mediaType: MediaType
    url: str | None = None
    resolution: int | None = None  # optional overwrite, otherwise pick defaults by type

    def _getResolution(self):
        if self.resolution:
            return self.resolution
        if self.mediaType == MediaType.profile:
            return 1024
        if self.mediaType == MediaType.thumb:
            return 320
        return None

    def _resolutionPath(self):
        if r := self._getResolution():
            return f"{r}x{r}/"
        return ""

    def _initialsPath(self):
        if self.mediaType == MediaType.gaymoji or len(self.name) < 8 or "/" in self.name:
            return ""
        #return f"{self.name[0].lower()}/{self.name[1].lower()}/"
        return f"{self.name[0].lower()}/{self.name[1].lower()}/{self.name[2].lower()}/"

    def _cacheRelPath(self):
        return self._resolutionPath() + self._initialsPath() + self.name

    def _relPath(self) -> str:
        return self._resolutionPath() + self.name

    def _rootPath(self) -> Path:
        if self.mediaType == MediaType.profile:
            return cache_root / "profile"
        elif self.mediaType == MediaType.thumb:
            return cache_root / "thumb"
        elif self.mediaType == MediaType.gaymoji:
            return cache_root
        else:
            return cache_root / "media"

    def cacheName(self):
        """The path under which the file is saved in cache"""
        return str(self._rootPath() / self._cacheRelPath())

    def getUrl(self):
        """The URL to download"""
        if self.mediaType == MediaType.profile:
            return cdn_images + "profile/" + self._relPath()
        elif self.mediaType == MediaType.thumb:
            return cdn_images + "thumb/" + self._relPath()
        elif self.mediaType == MediaType.gaymoji:
            return cdn_gaymoji + self.name
        else:
            return self.url

# See: https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
class DownloadWorkerSignals(QObject):
    finished = Signal(MediaDescription, str)
    #error = Signal(tuple)
    #result = Signal(object)

class DownloadWorker(QRunnable):
    def __init__(self, mediaDesc):
        super().__init__()
        self.mediaDesc = mediaDesc
        self.signals = DownloadWorkerSignals()

    @Slot()
    def run(self):
        result = None
        try:
            result = download_img(self.mediaDesc)
        #except:
        #    traceback.print_exc()
        #    exctype, value = sys.exc_info()[:2]
        #    self.signals.error.emit((exctype, value, traceback.format_exc()))
        #else:
        #    self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit(self.mediaDesc, result)

def media_description_from_hash(imgHash, mediaType: MediaType):
    # Creates a MediaDescription for the given hash and type (profile or thumb),
    # if the hash has to correct format. Otherwise, if it has the form of a URL,
    # return a URL object instead.
    # This should no longer be needed, as hashes are extracted from URLs before this
    # is called, keeping the correct media type, but is here as a failsafe.
    if imgHash.startswith("http"):
        return MediaDescription(base_hash_from_url(imgHash), MediaType.url, imgHash)
    return MediaDescription(imgHash, mediaType)

def hash_from_str(s):
    if s and s.startswith(cdn_base_url):
        return base_hash_from_url(s)
    return s

def decorated_hash_from_url(url):
    # Extract the hash from URL, i.e. the identifier after the last slash and
    # potentially before ?, including decorations such as ".cover"
    m = re.match(r"http.*\/([\w\-\.]+)", url)
    return m.group(1) if m else None

def base_hash_from_url(url):
    # Extract the hash from URL, without decorations
    m = re.match(r"http.*\/([\w\-]+)", url)
    return m.group(1) if m else None

def extension_from_headers(headers):
    extension = ".jpg"
    for h in headers.split('\r\n'):
        pre = h[:20].lower()
        if pre.startswith("content-type"):
            if pre == "content-type: image/" or pre == "content-type: video/":
                extension = "." + h[20:25].lower()
            if pre.startswith("content-type: text/"):
                extension = "." + h[19:24].lower()
    return extension

def make_parent_dir(fname):
    Path(fname).parent.mkdir(parents=True, exist_ok=True)

def write_buffer(fname, buffer_io):
    make_parent_dir(fname)
    with open(fname, "wb") as f:
        f.write(buffer_io.getvalue())

def download_url(url):
    headers_io = BytesIO()
    buffer_io = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.HEADERFUNCTION, headers_io.write)
    c.setopt(c.WRITEFUNCTION, buffer_io.write)
    c.setopt(c.COOKIEJAR, cookie_file)
    c.setopt(c.COOKIEFILE, cookie_file)
    c.setopt(c.FOLLOWLOCATION, True)
    #c.setopt(pycurl.SSL_VERIFYPEER, 0)
    #c.setopt(pycurl.SSL_VERIFYHOST, 0)
    c.perform()
    code = c.getinfo(pycurl.HTTP_CODE)
    c.close()
    return code, headers_io, buffer_io

def download_img(mediaDesc: MediaDescription) -> str | None:
    print("I: Downloading", mediaDesc.mediaType, ":", mediaDesc.name, time_str())
    url = mediaDesc.getUrl()
    code, headers_io, buffer_io = download_url(url)
    headers = headers_io.getvalue().decode()
    ext = extension_from_headers(headers)
    if code != 200 or ext == ".xml" or ext == ".html":
        return None
    fpath = Path(mediaDesc.cacheName())
    if not fpath.suffix:
        fpath = fpath.with_suffix(ext)
    elif fpath.suffix != ext:
        print("WARNING: Conflicting extenstions: suffix ", fpath.suffix, ", from mime type:", ext)
        fpath = str(fpath) + ext
    fname = str(fpath)
    write_buffer(fname, buffer_io)
    return fname

def get_cached_image_name(mediaDesc: MediaDescription) -> str | None:
    path = Path(mediaDesc.cacheName())
    files = list(path.parent.glob(path.stem + "*"))
    for f in files:
        #if path.stem == Path(f).stem or path.name == Path(f).stem:
        if path.name == Path(f).name or path.name == Path(f).stem:
            return str(f)
    return None

def get_or_download_image(mediaDesc: MediaDescription) -> str | None:
    imgName = get_cached_image_name(mediaDesc)
    if imgName:
        return imgName
    return download_img(mediaDesc)

def get_or_download_full_media(mediaDesc: MediaDescription) -> str | None:
    # If the video was expiring, we can only get the thumb or cover.
    # Check if the original video is in still cache
    mname = mediaDesc.name
    if mname.endswith(".thumb") or mname.endswith(".cover"):
        mname = mname.removesuffix(".thumb").removesuffix(".cover")
        mdesc = MediaDescription(mname, mediaDesc.mediaType, mediaDesc.url, mediaDesc.resolution)
        fname = get_cached_image_name(mdesc)
        if fname:
            return fname
    return get_or_download_image(mediaDesc)

def download_gaymoji_list():
    file = cache_root / "gaymoji.json"
    if file.exists():
        return str(file)
    url = cdn_gaymoji + "gaymoji"
    code, _, buffer_io = download_url(url)
    if code != 200:
        return None
    write_buffer(str(file), buffer_io)
    return str(file)
