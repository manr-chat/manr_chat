#!/usr/bin/env python3

from enum import Enum
from PySide6 import QtWidgets, QtGui, QtCore

from .grindr_access.grindr_user import GrindrFlags
from .datamodel import DataModel
from .image_cache import get_cached_image_name, MediaDescription, MediaType
from .notificationbadge import NotificationBadge
from .sound import playNotificationSound
from .utils import profile

maxNotificationLabels = 5

class StatusBarControl:
    def __init__(self, mainwindow, model: DataModel, app):
        self.mainwindow = mainwindow
        self.model = model
        self.statusBar = mainwindow.ui.statusBar()
        self.statusLabel = QtWidgets.QLabel()
        #self.iconLabel = QtWidgets.QLabel()
        #icon = app.windowIcon()
        #self.iconLabel.setPixmap(icon.pixmap(icon.actualSize(QtCore.QSize(32, 32))))
        self.statusBar.addWidget(self.statusLabel)
        self._addSeparatorLine()
        #self.statusBar.addWidget(self.iconLabel)
        self.notificationLabels = []
        self.chatIcon = self._loadPixmap("resources/img/incoming_envelope.svg")
        self.albumIcon = self._loadPixmap("resources/img/frame_with_picture.svg")
        self.viewIcon = "👀"
        self.tapHiIcon = self._loadPixmap("resources/img/friendly.svg")
        self.tapHotIcon = self._loadPixmap("resources/img/hot.svg")
        self.tapLookingIcon = self._loadPixmap("resources/img/looking.svg")
        self.blankProfileIcon = self._loadPixmap("resources/img/blank.png")
        #badge1 = NotificationBadge()
        #badge2 = NotificationBadge()
        #badge2.text = "3"
        #self.statusBar.addWidget(badge1)
        #self.statusBar.addWidget(badge2)

    def _loadPixmap(self, fileName):
        icon = QtGui.QIcon(fileName)
        pixmap = icon.pixmap(icon.actualSize(QtCore.QSize(16, 16)))
        return pixmap
    
    def _addSeparatorLine(self):
        line = QtWidgets.QFrame(self.statusBar)
        line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.statusBar.addWidget(line)

    def updateLoginStatus(self, offlineMode, websocketConnected):
        if not self.model.user:
            status = "Not logged in."
        else:
            status = f"User {self.model.user.email} (ID: {self.model.user.profileId}) " + \
                     ("offline." if offlineMode else "logged in.")
            if not offlineMode and not websocketConnected:
                status += " ERROR: failed Websocket connection!"
        profile("Status:", status)
        self.statusLabel.setText(status)

    def _alert(self, duration=0):
        app = QtWidgets.QApplication.instance()
        playNotificationSound()
        app.alert(self.mainwindow.ui, duration=duration)

    def chatNotification(self, senderId, chatType, body):
        self._alert()
        if not self.model.user or int(senderId) != int(self.model.user.profileId):
            icon = self.chatIcon if chatType != "Album" else self.albumIcon
            profile = self.model.getProfileDetails(senderId)
            imgHashes = self.model.getImageHashes(profile)
            imgHash = imgHashes[0] if imgHashes else None
            text = body["text"] if chatType == "Text" else None
            self._addNotificationIcon(icon, imgHash, text)

    def viewNotification(self, profileId, imgHash):
        self._alert(duration=30)
        self._addNotificationIcon(self.viewIcon, imgHash)

    def tapNotification(self, senderId, tapType, imgHash):
        self._alert()
        if self.model.user and int(senderId) == int(self.model.user.profileId):
            return
        if int(tapType) == int(GrindrFlags.tap_type_hi):
            icon = self.tapHiIcon
        elif int(tapType) == int(GrindrFlags.tap_type_hot):
            icon = self.tapHotIcon
        elif int(tapType) == int(GrindrFlags.tap_type_looking):
            icon = self.tapLookingIcon
        else :
            icon = self.tapHotIcon
        self._addNotificationIcon(icon, imgHash)

    def _getNextLabels(self):
        if len(self.notificationLabels) >= maxNotificationLabels:
            nLabel, niLabel = self.notificationLabels.pop(0)
            nLabel.deleteLater()
            niLabel.deleteLater()
        nLabel = QtWidgets.QLabel()
        niLabel = QtWidgets.QLabel()
        self.statusBar.addWidget(nLabel)
        self.statusBar.addWidget(niLabel)
        self.notificationLabels.append((nLabel, niLabel))
        return nLabel, niLabel

    def _addNotificationIcon(self, notificationIcon, imgHash, text=None):
        nLabel, niLabel = self._getNextLabels()
        if type(notificationIcon) == str:
            nLabel.setText(notificationIcon)
        else:
            nLabel.setPixmap(notificationIcon)
        imgFileName = None
        if imgHash:
            imgFileName = get_cached_image_name(MediaDescription(imgHash, MediaType.thumb))
            if not imgFileName:
                imgFileName = get_cached_image_name(MediaDescription(imgHash, MediaType.profile))
        text = text + "<br>" if text is not None else ""
        if imgFileName:
            niLabel.setPixmap(self._loadPixmap(imgFileName))
            niLabel.setToolTip(f'{text}<img src="{imgFileName}">');
        else:
            niLabel.setPixmap(self.blankProfileIcon)
            niLabel.setToolTip(text);