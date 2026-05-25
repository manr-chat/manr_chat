#!/usr/bin/env python3

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader

from typing import Any
import enum
from .image_cache import DownloadWorker, MediaType, media_description_from_hash, get_cached_image_name, base_hash_from_url
from .utils import *

ProfileFlags = enum.Flag("ProfileFlags", ["top_pick"])

scaling = 1
class ItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, view, model):
        super().__init__()
        self.view = view
        self.model = model
        self.style = view.style()
        self.size = self.view.iconSize()
        self.square = True
        self.margin = 2

    def sizeHint(self, option, modelIdx):
        wOfs = 2*self.margin
        hOfs = wOfs if self.square else wOfs + 20
        return QtCore.QSize(self.size.width()/scaling+wOfs, self.size.height()/scaling+hOfs)
        #return self.size

    def _compute_baseline_from_rect(self, painter, rect, center = False):
        fm = painter.fontMetrics()
        if center:
            y_baseline = rect.top() + (rect.height() + fm.ascent() - fm.descent()) // 2
        else:
            y_baseline = rect.bottom() - fm.descent()
        return y_baseline

    def _draw_shadow_text(self, painter, rect, text):
        x = rect.left()
        y = self._compute_baseline_from_rect(painter, rect, center=False)

        path = QtGui.QPainterPath()
        path.addText(x+1, y+1, painter.font(), text)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 160))
        painter.drawPath(path)

        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(x, y, text)

    def paint(self, painter, option, modelIdx):
        #return super().paint(painter, option, modelIdx)
        opt = option;
        self.initStyleOption(opt, modelIdx)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)

        ## Draw selection marker
        profileFlags = self.model.getProfileFlags(modelIdx)
        color = None
        if opt.state & QtWidgets.QStyle.StateFlag.State_Selected:
            color = QtGui.QColor("gold").darker(150)
        elif profileFlags & ProfileFlags.top_pick:
            color = QtGui.QColor("darkred")
        if color:
            brush = opt.palette.brush(QtGui.QPalette.ColorGroup.Normal, QtGui.QPalette.ColorRole.Highlight)
            brush = QtGui.QBrush(color)
            painter.fillRect(opt.rect, brush)            
        opt.rect = opt.rect.marginsRemoved(QtCore.QMargins(self.margin,self.margin,self.margin,self.margin))

        ## Draw profile image
        profileRect = QtCore.QRect(opt.rect)
        profileRect.setBottom(profileRect.top()+self.size.height()/scaling)
        img = self.model.getImage(modelIdx)
        imgRect = img.rect()
        if self.square:
            imgRect = getCroppedSquare(imgRect)
        else:
            profileRect = scaleTargetRect(imgRect, profileRect)
        painter.drawPixmap(profileRect, img, imgRect)

        ## Draw profile text
        textRect = self.style.subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget);
        textRect = QtCore.QRect(opt.rect)
        if self.square:
            textRect.setTop(textRect.bottom()-20)
        else:
            textRect.setTop(textRect.top()+self.size.height()/scaling)
        self._draw_shadow_text(painter, textRect, opt.text)

    def setViewMode(self, square):
        self.square = square
        self.sizeHintChanged.emit(self.model.index(0,0))

    def setIconSize(self, iconSize):
        self.size = iconSize
        self.sizeHintChanged.emit(self.model.index(0,0))

class ListModel(QtCore.QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.blankProfileImage = QtGui.QPixmap("resources/img/blank.png")
        self.loadingProfileImage = QtGui.QPixmap("resources/img/loading_blank.png")
        self.profileIds = []
        self.labels = []
        self.imgHashes = []
        self.images = []
        self.profileFlags = []
        self.iconSize = QtCore.QSize(128, 128)

    def data(self, index, role):
        r, c = index.row(), index.column()
        assert c == 0 and 0 <= r < len(self.profileIds)
        if role == Qt.ItemDataRole.DisplayRole:
            return self.labels[r]
        elif role == Qt.ItemDataRole.DecorationRole:
            return self.getScaledImage(r)
        elif role == Qt.ItemDataRole.UserRole:
            return self.profileIds[r]

    def headerData(self, section, orientation, role):
        return super().headerData(section, orientation, role)

    def rowCount(self, parent=None):
        return len(self.profileIds)

    def columnCount(self, parent=None):
        assert False
        return 1

    def _rowFromIdx(self, modelIdx):
        r, c = modelIdx.row(), modelIdx.column()
        assert c == 0 and 0 <= r < len(self.profileIds)
        return r

    def getImage(self, modelIdx):
        return self.images[self._rowFromIdx(modelIdx)]

    def getImageHash(self, modelIdx):
        return self.imgHashes[self._rowFromIdx(modelIdx)]

    def getProfileFlags(self, modelIdx):
        return self.profileFlags[self._rowFromIdx(modelIdx)]

    def getScaledImage(self, idx):
        img = self.images[idx]
        s = img.size()
        if s.width() > self.iconSize.width() or s.height() > self.iconSize.height():
            img = img.scaled(self.iconSize.width()/scaling, self.iconSize.height()/scaling,
                             Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        return img

    def _mediaDescription(self, imgHash):
        return media_description_from_hash(imgHash, MediaType.thumb)

    # Qt defines setData, use a different name
    def setProfileData(self, profileIds, labels, imgHashes, profileFlags):
        pbegin = profile("setProfileData begin")
        self.beginResetModel()
        assert len(profileIds) == len(labels) == len(imgHashes)
        self.profileIds = profileIds
        self.labels = labels
        self.imgHashes = imgHashes
        self.profileFlags = profileFlags
        pload = profile("setProfileData before image load", start=pbegin)
        self._updateImagesFromHashes()
        pupdate = profile("setProfileData before endResetModel", start=pload)
        self.endResetModel()
        profile("setProfileData end", start=(pupdate, pbegin))

    def _updateImagesFromHashes(self):
        import time
        self.images = []
        loadTimes, backgroundTimes, cacheTimes = 0, 0, 0
        pbegin = profile("_updateImagesFromHashes begin")
        for imgHash in self.imgHashes:
            img = self.blankProfileImage
            if imgHash:
                t0 = time.time()
                imgFileName = get_cached_image_name(self._mediaDescription(imgHash))
                t = time.time()
                cacheTimes += t-t0
                if imgFileName:
                    img = QtGui.QPixmap(imgFileName)
                    loadTimes += time.time() - t
                else:
                    img = self.loadingProfileImage
                    self.startBackgroundDownload(imgHash)
                    backgroundTimes += time.time() - t
            self.images.append(img)
        profile("_updateImagesFromHashes end", start=pbegin)
        profile(f"Sum of file load times: {time_diff(loadTimes)},"+
                f" sum of triggering background download times: {time_diff(backgroundTimes)}"+
                f" sum of cache lookup times: {time_diff(cacheTimes)}")

    def clear(self):
        self.setProfileData([], [], [], [])

    def startBackgroundDownload(self, imgHash):
        worker = DownloadWorker(self._mediaDescription(imgHash))
        worker.signals.finished.connect(self.downloadComplete)
        QtCore.QThreadPool.globalInstance().start(worker)

    @QtCore.Slot()
    def downloadComplete(self, imgDesc, imgFileName):
        for i in range(len(self.imgHashes)):
            if imgDesc.name == self.imgHashes[i] or \
               self.imgHashes[i] and imgDesc.name == base_hash_from_url(self.imgHashes[i]):
                self.images[i] = QtGui.QPixmap(imgFileName) if imgFileName else self.blankProfileImage
                self.dataChanged.emit(self.index(0, i), self.index(0, i))

class ProfileListWidget:
    ui: Any

    def __init__(self, dataModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("profilelistwidget.ui")
        ds = QtWidgets.QGraphicsDropShadowEffect()
        self.ui.setGraphicsEffect(ds)
        self.setupConnections()
        self.model = dataModel
        self.listModel = ListModel()
        self.listModel.iconSize = self.ui.iconSize()
        self.delegate = ItemDelegate(self.ui, self.listModel)
        self.ui.setModel(self.listModel)
        self.ui.setItemDelegate(self.delegate)
        self.displayFavIcon = True
        self.doFilter = False
        # self.ui.profileList.setUniformItemSizes(False)

    def setupConnections(self):
        pass

    def setFilter(self, on):
        self.doFilter = on

    def filterProfile(self, dd, hasImage):
        return True
        #d = self.model.getExtendedProfile(dd["profileId"])
        d = dd
        #return True
        if d.get("isFavorite", False):
            return True
        #if not hasImage:
        #    return False
        #if d.get("socialNetworks", None):
        #    s = d.get("socialNetworks", None)
        #    print("socials:", s)
        #    ed = self.model.getExtendedProfile(dd["profileId"])
        #    es = ed.get("socialNetworks", None)
        #    print("Extended socials:", es)
        #    print("Profile:", d)
        #    print("Extended Profile:", ed)
        #    return True
        #return False
        #if d.get("rightNow", "") == 'NOT_ACTIVE':  # 'NOT_HOSTING', 'HOSTING'
        #    return False
        #return True
        allowNoAge = False
        maxAge = 25
        if "age" not in d:
            return allowNoAge
        return d["age"] <= maxAge

    def setViewMode(self, cropped):
        self.delegate.setViewMode(cropped)

    def setDisplayFavIcon(self, display):
        self.displayFavIcon = display

    def setIconSize(self, iconSize):
        self.ui.setIconSize(iconSize)
        self.listModel.iconSize = iconSize
        self.delegate.setIconSize(iconSize)

    def getProfileId(self, modelIdx):
        return self.listModel.data(modelIdx, Qt.ItemDataRole.UserRole)

    def getCurrentProfileId(self):
        return self.listModel.data(self.ui.currentIndex(), Qt.ItemDataRole.UserRole)

    def getImageHash(self, modelIdx):
        return self.listModel.getImageHash(modelIdx)

    def populateList(self, profiles):
        pbegin = profile("populateList begin")
        self.listModel.clear()
        maxItems, numItems, nonBlank = 2000, 0, 0
        profileIds, labels, imgHashes, flags = [], [], [], []
        if self.doFilter: print("Profiles before filter:", len(profiles))
        for pIdx, p in enumerate(profiles):
            d = p["data"]
            isForYouPick = "TopPicks" in p.get("type", "")
            pId = str(d.get("profileId", -pIdx))
            #profile("P", pId)
            img_hashes = self.model.getImageHashes(d)
            if img_hashes:
                nonBlank += 1
            if self.doFilter and not self.filterProfile(d, bool(img_hashes)):
                continue
            img_hash = img_hashes[0] if img_hashes else None
            fav = self.displayFavIcon and d.get("isFavorite", False)
            lastOnline = d.get("lastOnline", None)
            label = d.get("displayName", "") or ""
            label = decorateLabel(label, fav, isRecent(lastOnline, minutes=10))
            profileIds.append(pId)
            labels.append(label)
            imgHashes.append(img_hash)
            flags.append(ProfileFlags.top_pick if isForYouPick else ProfileFlags(0))
            numItems += 1
            if numItems >= maxItems:
                break
        if self.doFilter: print("Profiles after filter:", len(profileIds))
        pdata = profile("Before setProfileData", start=pbegin)
        self.listModel.setProfileData(profileIds, labels, imgHashes, flags)
        profile("Profiles: %d, non blank: %d, displayed: %d" % (len(profiles), nonBlank, numItems))
        profile("populateList end", start=(pdata, pbegin))
        #profile("Profiles:\n", profiles)

