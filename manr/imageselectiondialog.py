#!/usr/bin/env python3

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader

from typing import Any
from .image_cache import DownloadWorker, MediaType, MediaDescription, get_cached_image_name, decorated_hash_from_url
from .utils import formatBool, formatTimeStamp, profile

class ImageSelectionDialog(QtCore.QObject):
    ui: Any

    def __init__(self, model, chatId, parent=None):
        super().__init__()
        self.model = model
        self.chatId = chatId
        self.pixmaps = {}
        self.ui = QUiLoader().load("imageselectiondialog.ui", parent)
        self.ui.splitter.setSizes([200, 600])
        self.blankProfileImage = QtGui.QPixmap("resources/img/blank.png")
        self.loadingProfileImage = QtGui.QPixmap("resources/img/loading_blank.png")
        self._setupConnections()
        self._initImageList()

    def _setupConnections(self):
        self.ui.imageList.currentRowChanged.connect(self.on_imageList_currentRowChanged)
        self.ui.uploadImage.clicked.connect(self.on_uploadImage_clicked)

    def getImageId(self):
        row = self.ui.imageList.currentRow()
        if row < 0 or row >= len(self.images):
            return
        return self.images[row]["id"]

    def startBackgroundDownload(self, mediaDesc):
        profile("I: ImageSelectionDialog: Starting Background download of", mediaDesc.name)
        worker = DownloadWorker(mediaDesc)
        worker.signals.finished.connect(self.downloadComplete)
        QtCore.QThreadPool.globalInstance().start(worker)

    @QtCore.Slot()
    def downloadComplete(self, imgDesc, imgFileName):
        profile("I: ImageSelectionDialog: Finished Background download of", imgDesc.name)
        print("imgDesc.mediaType:", imgDesc.mediaType)
        assert imgDesc.mediaType == MediaType.url
        for row in range(self.ui.imageList.count()):
            item = self.ui.imageList.item(row)
            itemImageId, itemImgHash = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if imgDesc.name == itemImgHash:
                img = QtGui.QPixmap(imgFileName)
                self.pixmaps[itemImageId] = img
                item.setIcon(img)
                self.setImageDetails()

    def setImageDetails(self):
        row = self.ui.imageList.currentRow()
        if row < 0 or row >= len(self.images):
            return
        img = self.images[row]
        self.ui.selectedImageLabel.setPixmap(self.pixmaps[img["id"]])
        inApp = formatBool(img["takenOnGrindr"])
        ts = formatTimeStamp(img["createdTs"])
        used = formatBool(img["used"])
        text = f"Taken in app: {inApp}, created: {ts}, used: {used}"
        self.ui.imageDescription.setText(text)

    def getImage(self, imageUrl, imgHash):
        img = self.blankProfileImage
        if imgHash:
            media = MediaDescription(imgHash, MediaType.url, url=imageUrl)
            imgFileName = get_cached_image_name(media)
            if imgFileName:
                img = QtGui.QPixmap(imgFileName)
            else:
                img = self.loadingProfileImage
                self.startBackgroundDownload(media)
        return img

    def _initImageList(self):
        convId = self.model.getConversationId(self.chatId) if self.chatId else ""
        self.images = self.model.getMediaDrawer(convId)
        self._populateList()
        self.setImageDetails()

    def _populateList(self):
        self.ui.imageList.clear()
        for i in self.images:
            imageId = i["id"]
            imageUrl = i["url"]
            imgHash = decorated_hash_from_url(imageUrl)
            item = QtWidgets.QListWidgetItem()
            img = self.getImage(imageUrl, imgHash)
            self.pixmaps[imageId] = img
            item.setIcon(img)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, (imageId, imgHash))
            self.ui.imageList.addItem(item)

    def on_imageList_currentRowChanged(self, curRow):
        self.setImageDetails()

    def on_uploadImage_clicked(self):
        filterStr = "Images (*.png *.gif *.jpg *.jpeg)"
        fileName, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(self.ui, "Open image", "", filterStr)
        if not fileName:
            return
        answer = QtWidgets.QMessageBox.question(self.ui, "", 'Put "taken on Grindr" watermark on image?')
        takenOnGrindr = answer == QtWidgets.QMessageBox.StandardButton.Yes
        res = self.model.uploadMediaFile(fileName, takenOnGrindr)
        self._initImageList()

def showImageSelectionDialog(model, chatId, parent):
    dlg = ImageSelectionDialog(model, chatId, parent)
    if dlg.ui.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        return dlg.getImageId()
    return None
