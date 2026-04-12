#!/usr/bin/env python3

import os
from html import escape
from typing import Any

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWebEngineWidgets import QWebEngineView

from pathlib import Path
from .image_cache import *

docTemplate = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head></head><body style="background-color:powderblue;">
<table width="100%" style="color: #000000">
{rows}
</table>
</body>"""
rowTemplate = """<tr><td width="100%"><p>{num}: {element}</p></td></tr>"""
urlText = """<a href="{url}">{url}</a>"""

class AlbumWidget(QtCore.QObject):
    ui: Any

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("albumwidget.ui")
        self.webview = QWebEngineView()
        self.ui.layout().addWidget(self.webview)
        self.setupConnections()
        self.model = model

    def setupConnections(self):
        pass

    def getAlbumHtml(self, album):
        curDir = os.getcwd()
        def mediaFileName(mediaDesc):
            fname = get_or_download_full_media(mediaDesc)
            if not fname:
                return ""
            file = str(Path(curDir) / fname)
            file = QtCore.QUrl.fromLocalFile(file).toString()
            return file
        def imgElement(mediaDesc):
            file = mediaFileName(mediaDesc)
            return f'<img src="{file}"/><br><a href="{file}">{file}</a>'
        def videoElement(mediaDesc):
            file = mediaFileName(mediaDesc)
            return f'<video controls src="{file}"></video><br><a href="{file}">{file}</a>'
        rows = []
        #print("Album size:", len(album["content"]))
        for i, media in enumerate(album["content"]):
            contentType = media["contentType"]
            url = media["url"] or media["thumbUrl"] or media["coverUrl"]
            imgHash = decorated_hash_from_url(url)
            if not imgHash:
                continue
            mediaDesc = MediaDescription(imgHash, MediaType.url, url=url)
            if contentType.startswith("image"):
                element = imgElement(mediaDesc)
            elif contentType.startswith("video"):
                element = videoElement(mediaDesc)
            else:
                element = f"Unknown contentType type {contentType}: " + urlText.format(url=url)
            row = rowTemplate.format(num=i, element=element)
            #print(i, contentType, url, imgHash)
            #print(row)
            rows.append(row)
        text = docTemplate.format(rows="".join(rows))
        return text

    def displayAlbum(self, albumId):
        if not albumId or int(albumId) <= 0:
            self.webview.setHtml("")
            return
        album = self.model.getAlbum(albumId)
        #print("Album", albumId, ":", album)
        text = self.getAlbumHtml(album) if album else ""
        #print("rendered html as:\n", text)
        curDir = os.getcwd()+os.path.sep
        baseUrl = QtCore.QUrl.fromLocalFile(curDir)
        print(curDir, baseUrl)
        self.webview.setHtml(text, baseUrl=baseUrl)
        # Write HTML to temp file for debugging purposes
        with open(get_cache_dir() / "album_temp.html", "w") as f:
            f.write(text)