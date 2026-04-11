#!/usr/bin/env python3

from typing import Any
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader

from .image_cache import DownloadWorker, MediaType, MediaDescription, get_cached_image_name
from .utils import *

class ChatListWidget(QtCore.QObject):
    ui: Any

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("chatlistwidget.ui")
        self.setupConnections()
        self.model = model
        self.unreadCount = 0
        self.blankProfileImage = QtGui.QPixmap("resources/img/blank.png")
        self.loadingProfileImage = QtGui.QPixmap("resources/img/loading_blank.png")
        self.chatCache = {}

    def setupConnections(self):
        self.ui.chatList.customContextMenuRequested.connect(self.onCustomContextMenuRequested)

    def onCustomContextMenuRequested(self, pos: QtCore.QPoint):
        """Show a context menu for the item that was right-clicked."""
        # Get item at the clicked position
        item = self.ui.chatList.itemAt(pos)
        if item is None:
            return  # click was outside of any item

        # Create a QMenu
        menu = QtWidgets.QMenu(self.ui)
        deleteChatAction = QtGui.QAction("Delete chat", self)
        blockUserAction = QtGui.QAction("Block user", self)
        hideUserAction = QtGui.QAction("Hide user ", self)
        deleteChatAction.triggered.connect(lambda: self.onDeleteChat(item))
        blockUserAction.triggered.connect(lambda: self.onBlockUser(item))
        hideUserAction.triggered.connect(lambda: self.onHideUser(item))
        menu.addAction(deleteChatAction)
        menu.addAction(blockUserAction)
        menu.addAction(hideUserAction)

        # Show the menu at the global cursor position
        menu.exec(self.ui.chatList.mapToGlobal(pos))

    def getUserFromItem(self, item: QtWidgets.QListWidgetItem):
        itemPId, itemImgHash = item.data(QtCore.Qt.ItemDataRole.UserRole)
        d = self.model.getExtendedProfile(itemPId)
        displayName = d.get("displayName", "")
        if displayName:
            return itemPId, f'"{displayName}" (profile id: {itemPId})'
        else:
            return itemPId, f'(profile id: {itemPId})'

    def onDeleteChat(self, item: QtWidgets.QListWidgetItem):
        profileId, userString = self.getUserFromItem(item)
        answer = QtWidgets.QMessageBox.question(self.ui, "", f"Do you want to delete the chat with user:\n{userString}")
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.model.deleteConversation(profileId)
        self.deleteItemFromList(item)

    def onBlockUser(self, item: QtWidgets.QListWidgetItem):
        profileId, userString = self.getUserFromItem(item)
        answer = QtWidgets.QMessageBox.question(self.ui, "", f"Do you want to block user:\n{userString}")
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.model.blockUser(profileId)
        self.deleteItemFromList(item)

    def onHideUser(self, item: QtWidgets.QListWidgetItem):
        profileId, userString = self.getUserFromItem(item)
        answer = QtWidgets.QMessageBox.question(self.ui, "", f"Do you want to hide user:\n{userString}")
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.model.hideUser(profileId)
        self.deleteItemFromList(item)

    def deleteItemFromList(self, item: QtWidgets.QListWidgetItem):
        row = self.ui.chatList.row(item)
        self.ui.chatList.takeItem(row)

    def startBackgroundDownload(self, imgHash):
        profile("I: Chat: Starting Background download of", imgHash)
        worker = DownloadWorker(MediaDescription(imgHash, MediaType.thumb))
        worker.signals.finished.connect(self.downloadComplete)
        QtCore.QThreadPool.globalInstance().start(worker)

    @QtCore.Slot()
    def downloadComplete(self, imgDesc, imgFileName):
        profile("I: Chat: Finished Background download of", imgDesc.name)
        assert imgDesc.mediaType == MediaType.thumb
        for row in range(self.ui.chatList.count()):
            item = self.ui.chatList.item(row)
            itemPId, itemImgHash = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if imgDesc.name == itemImgHash:
                item.setIcon(QtGui.QPixmap(imgFileName))

    def getProfileImage(self, imgHash):
        img = self.blankProfileImage
        if imgHash:
            imgFileName = get_cached_image_name(MediaDescription(imgHash, MediaType.thumb))
            if imgFileName:
                img = QtGui.QPixmap(imgFileName)
            else:
                img = self.loadingProfileImage
                self.startBackgroundDownload(imgHash)
        return img

    def getProfileId(self, idx):
        pId, imgHash = self.ui.chatList.item(idx).data(QtCore.Qt.ItemDataRole.UserRole)
        return pId

    def getCurrentProfileId(self):
        return self.getProfileId(self.ui.chatList.currentRow())

    def getNormalFont(self):
        return self.ui.font()

    def getBoldFont(self):
        boldFont = self.ui.font()
        boldFont.setBold(True)
        return boldFont

    def getChatLabelText(self, chat):
        preview = chat["name"]
        preview += f"\t({chat["unread"]})" if chat["unread"] else "\t"
        preview += f"\t{formatTimeStamp(chat["lastMsg"])}"
        preview += f"\n{chat["text"]}"
        return preview

    def getChatPreviewText(self, senderId, chatType, chatBody):
        text = ""
        if chatType == "Text":
            text = chatBody["text"]
        elif chatType == "Image":
            text = "image: " + chatBody["url"]
        elif chatType == "Gaymoji":
            text = "gaymoji: " + chatBody["url"]
        elif chatType == "Album":
            text = f"Album: {chatBody["albumId"]}"
        elif chatType == "Location":
            text = f"📍🗺️ Location"
        elif chatType == "ProfilePhotoReply":
            text = f"Profile photo reply: " + chatBody["imageHash"]
        else:
            text = f"Unhandled chat type: {chatType}"
        if self.model.user.profileId == senderId:
            text = "⤷ " + text
        return text

    def _newChatExistingUser(self, senderId, userId, chatType, chatBody, timestamp):
        # Message from user with existing chats
        chat = self.chatCache[userId]
        sentByMe = senderId != userId
        if sentByMe:
            if chat["unread"]:
                self.unreadCount -= 1
            chat["unread"] = 0
        else:
            if not chat["unread"]:
                self.unreadCount += 1
            chat["unread"] += 1
        chat["text"] = self.getChatPreviewText(senderId, chatType, chatBody)
        print("chat:", chat)
        for row in range(self.ui.chatList.count()):
            item = self.ui.chatList.item(row)
            itemPId, itemImgHash = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if userId == itemPId:
                print("Found user. New labelText:", self.getChatLabelText(chat))
                item.setText(self.getChatLabelText(chat))
                item.setFont(self.getBoldFont() if chat["unread"] else self.getNormalFont())
                self.ui.chatList.blockSignals(True)
                try:
                    currentItem = self.ui.chatList.currentItem()
                    takenItem = self.ui.chatList.takeItem(row)
                    assert item == takenItem
                    self.ui.chatList.insertItem(0, item)
                    self.ui.chatList.setCurrentItem(currentItem)
                finally:
                    self.ui.chatList.blockSignals(False)
                return

    def _newChatNewUser(self, senderId, userId, chatType, chatBody, timestamp):
        # Message from new user
        chat = {}
        user = self.model.getExtendedProfile(userId)
        chat["isOnline"] = True
        chat["name"] = decorateLabel(user.get("displayName", "") or "", user.get("isFavorite", False), isOnline=True)
        chat["unread"] = 1
        chat["lastMsg"] = timestamp
        chat["text"] = self.getChatPreviewText(senderId, chatType, chatBody)
        labelText = self.getChatLabelText(chat)
        print("chat:", chat)
        print("labelText:", labelText)
        imgHashes = self.model.getImageHashes(user)
        imgHash = imgHashes[0] if imgHashes else None
        item = QtWidgets.QListWidgetItem(labelText)
        item.setIcon(self.getProfileImage(imgHash))
        item.setData(QtCore.Qt.ItemDataRole.UserRole, (userId, imgHash))
        item.setFont(self.getBoldFont())
        self.chatCache[userId] = chat
        self.unreadCount += 1
        self.ui.chatList.blockSignals(True)
        try:
            self.ui.chatList.insertItem(0, item)
        finally:
            self.ui.chatList.blockSignals(False)

    def conversationRead(self, conversationId):
        userId = self.model.getConversationPartner(conversationId)
        chat = self.chatCache[userId]
        if not chat:
            return
        if chat["unread"]:
            self.unreadCount -= 1
        chat["unread"] = 0
        for row in range(self.ui.chatList.count()):
            item = self.ui.chatList.item(row)
            itemPId, itemImgHash = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if userId == itemPId:
                print("Found user. New labelText:", self.getChatLabelText(chat))
                item.setText(self.getChatLabelText(chat))
                item.setFont(self.getNormalFont())


    def newChat(self, senderId, conversationId, chatType, chatBody, timestamp):
        print("In newChat")
        userId = self.model.getConversationPartner(conversationId)
        if userId in self.chatCache:
            print("Chat from existing user")
            self._newChatExistingUser(senderId, userId, chatType, chatBody, timestamp)
        else:
            print("Chat from new user")
            self._newChatNewUser(senderId, userId, chatType, chatBody, timestamp)


    def populateList(self, chats):
        boldFont = self.getBoldFont()
        isOnlineCheck = lambda t: isRecent(t, 2*60)
        self.unreadCount = 0
        for e in chats["entries"]:
            pre = e["preview"]
            senderId = str(pre["senderId"])
            userId = str(e["participants"][0]["profileId"])
            assert e["conversationId"] == self.model.getConversationId(userId)
            chat = {}
            chat["isOnline"] = any(isOnlineCheck(p["lastOnline"]) for p in e["participants"])
            chat["name"] = decorateLabel(e["name"], e["favorite"], chat["isOnline"])
            chat["unread"] = e["unreadCount"]
            chat["lastMsg"] = e["lastActivityTimestamp"]
            chat["text"] = self.getChatPreviewText(senderId, pre["type"], pre)
            self.chatCache[userId] = chat
            labelText = self.getChatLabelText(chat)
            imgHash = e["participants"][0]["primaryMediaHash"]
            item = QtWidgets.QListWidgetItem(labelText)
            item.setIcon(self.getProfileImage(imgHash))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, (userId, imgHash))
            if chat["unread"]:
                item.setFont(boldFont)
                self.unreadCount += 1
            self.ui.chatList.addItem(item)
