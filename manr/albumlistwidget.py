#!/usr/bin/env python3

from typing import Any
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader

from .image_cache import DownloadWorker, MediaType, MediaDescription, get_cached_image_name, decorated_hash_from_url, base_hash_from_url
from .utils import *

class AlbumListWidget(QtCore.QObject):
    ui: Any

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("albumlistwidget.ui")
        self.setupConnections()
        self.model = model
        self.blankProfileImage = QtGui.QPixmap("resources/img/blank.png")
        self.loadingProfileImage = QtGui.QPixmap("resources/img/loading_blank.png")

    def setupConnections(self):
        pass

    def startBackgroundDownload(self, mediaDesc):
        profile("I: Albums: Starting Background download of", mediaDesc.name)
        worker = DownloadWorker(mediaDesc)
        worker.signals.finished.connect(self.downloadComplete)
        QtCore.QThreadPool.globalInstance().start(worker)

    @QtCore.Slot()
    def downloadComplete(self, imgDesc, imgFileName):
        profile("I: Albums: Finished Background download of", imgDesc.name)
        print("imgDesc.mediaType:", imgDesc.mediaType, imgFileName)
        assert imgDesc.mediaType == MediaType.url
        for row in range(self.ui.albumList.count()):
            item = self.ui.albumList.item(row)
            itemAlbumId, itemProfileId, itemImgHash = item.data(QtCore.Qt.UserRole)
            if imgDesc.name == itemImgHash:
                item.setIcon(QtGui.QPixmap(imgFileName))

    def getCoverImage(self, coverUrl, coverImgHash, baseImgHash):
        #pbegin = profile("getCoverImage begin")
        img = self.blankProfileImage
        if coverImgHash:
            # Try to get the full image first. This is unnecessarily large compared to the cover, but not blurred.
            fullMedia = MediaDescription(baseImgHash, MediaType.url, url=coverUrl)
            imgFileName = get_cached_image_name(fullMedia)
            img = None
            if imgFileName:
                img = QtGui.QPixmap(imgFileName)
            if not img:
                coverMedia = MediaDescription(coverImgHash, MediaType.url, url=coverUrl)
                imgFileName = get_cached_image_name(coverMedia)
                if imgFileName:
                    img = QtGui.QPixmap(imgFileName)
            if not img:
                img = self.loadingProfileImage
                self.startBackgroundDownload(coverMedia)
        #pbegin = profile("getCoverImage end", start=pbegin)
        return img

    def getAlbumId(self, idx):
        albumId, profileId, imgHash = self.ui.albumList.item(idx).data(QtCore.Qt.UserRole)
        return albumId

    def getProfileId(self, idx):
        albumId, profileId, imgHash = self.ui.albumList.item(idx).data(QtCore.Qt.UserRole)
        return profileId

    def getCurrentAlbumId(self):
        return self.getAlbumId(self.ui.albumList.currentRow())

    def getCurrentProfileId(self):
        return self.getProfileId(self.ui.albumList.currentRow())

    def populateList(self, albums):
        pbegin = profile("AlbumListWidget.populateList begin")
        #profile("Albums:\n", albums)
        self.ui.albumList.clear()
        for a in albums["albums"]:
            albumId = a["albumId"]
            profileId = a["profileId"]
            coverUrl = a["content"]["coverUrl"]
            coverImgHash = decorated_hash_from_url(coverUrl)
            baseImgHash = base_hash_from_url(coverUrl)
            text = ""
            profileData = None # self.model.getExtendedProfile(profileId)
            if profileData:
                text = profileData.get("displayName", "") or ""
            imageCount = a["contentCount"]["imageCount"]
            videoCount = a["contentCount"]["videoCount"]
            text += f"\nImages: {imageCount}, videos: {videoCount}"
            item = QtWidgets.QListWidgetItem(text)
            item.setIcon(self.getCoverImage(coverUrl, coverImgHash, baseImgHash))
            item.setData(QtCore.Qt.UserRole, (albumId, profileId, coverImgHash))
            self.ui.albumList.addItem(item)
        profile("AlbumListWidget.populateList end", start=pbegin)
