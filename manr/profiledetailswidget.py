#!/usr/bin/env python3

from html import escape
from typing import Any

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader

from .grindr_access.grindr_user import GrindrFlags
from .utils import *
from .image_cache import DownloadWorker, MediaType, media_description_from_hash, get_cached_image_name, base_hash_from_url

class ProfileDetailsWidget(QtCore.QObject):
    ui: Any

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("profiledetailswidget.ui")
        self.ui.splitter.setSizes([600, 400])
        self.setupConnections()
        self.setupTapMenu()
        self.model = model
        self.ui.imageLabels = []
        self.imageHashes = []
        self.imageResourceCache = {}
        self.currentProfile, self.currentProfileIdx = None, None
        self.loadingProfileImage = QtGui.QPixmap("resources/img/loading_blank.png")
        self.loadMappings()
        self.loadImageResources()
        self.loadLogo()

    def setupConnections(self):
        self.ui.setFavorite.clicked.connect(self.on_setFavorite_clicked)
        self.ui.sendTap.clicked.connect(self.on_sendTap_clicked)

    def setupTapMenu(self):
        menu = QtWidgets.QMenu(self.ui.sendTap)
        actTapHi = QtGui.QAction("Send HI tap", menu)
        actTapHot = QtGui.QAction("Send HOT tap", menu)
        actTapLooking = QtGui.QAction("Send LOOKING tap", menu)
        actTapHi.setIcon(QtGui.QIcon("resources/img/friendly.svg"))
        actTapHot.setIcon(QtGui.QIcon("resources/img/hot.svg"))
        actTapLooking.setIcon(QtGui.QIcon("resources/img/looking.svg"))
        actTapHi.triggered.connect(lambda: self.sendTap(GrindrFlags.tap_type_hi))
        actTapHot.triggered.connect(lambda: self.sendTap(GrindrFlags.tap_type_hot))
        actTapLooking.triggered.connect(lambda: self.sendTap(GrindrFlags.tap_type_looking))
        menu.addActions([actTapHi, actTapHot, actTapLooking])
        self.ui.sendTap.setMenu(menu)
        self.ui.sendTap.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    def loadMappings(self):
        self.mappings = load_json("resources/data/mapping.json")
        genders = load_json("resources/data/genders.json")
        pronouns = load_json("resources/data/pronouns.json")
        for g in genders:
            self.mappings["genders"][str(g["genderId"])] = g["gender"]
        for p in pronouns:
            self.mappings["pronouns"][str(p["pronounId"])] = p["pronoun"]

    def initImageLabels(self, count):
        for i in range(count - len(self.ui.imageLabels)):
            label = QtWidgets.QLabel()
            self.ui.imageScroll.layout().addWidget(label)
            self.ui.imageLabels.append(label)
        assert len(self.ui.imageLabels) >= count

    def showImageLabels(self, count):
        self.ui.logo.hide()
        self.initImageLabels(count)
        N = len(self.ui.imageLabels)
        for i in range(min(count, N)):
            self.ui.imageLabels[i].show()
        for i in range(count, N):
            self.ui.imageLabels[i].hide()
            self.ui.imageLabels[i].clear()

    def sendTap(self, tap_type):
        #profile("Sending tap to", self.currentProfile["profileId"], ", type: ", tap_type)
        profileId = str(self.currentProfile["profileId"])
        self.model.sendTap(profileId, tap_type)
        # Give the server some time to process the tap before asking about the profile again
        QtCore.QTimer.singleShot(1000, self.refreshProfileView)

    def on_sendTap_clicked(self):
        self.sendTap(GrindrFlags.tap_type_hot)

    def on_setFavorite_clicked(self, checked):
        if not self.currentProfile:
            return
        if checked:
            self.model.user.set_favorite(str(self.currentProfile["profileId"]))
        else:
            self.model.user.remove_favorite(str(self.currentProfile["profileId"]))
        self.currentProfile["isFavorite"] = checked
        self.checkFavorite(self.currentProfile)

    def _getSocialNetworks(self, socialNetworks):
        # Data from Cascade is in the form [{'site': 'instagram', 'userId': 'foobar'}]
        # Data from extended profile is in the form  {'instagram': {'userId': 'foobar'}}
        socialsLabels = []
        def linkLabel(name, baseUrl, icon, userId):
            return f"<a href='{baseUrl}{userId}'><img src='mydata://{icon}' height=14/> {name}: {userId}</a>"
        def instaLabel(userId):
            return linkLabel("Instagram", "https://www.instagram.com/", "ic_instagram.svg", userId)
        def twitterLabel(userId):
            return linkLabel("Twitter", "https://www.twitter.com/", "ic_twitter.svg", userId)
        def genericLabel(site, userId):
            match site:
                case "instagram": return instaLabel(userId)
                case "twitter": return twitterLabel(userId)
                case _: return f"{site}: {userId}"
        if type(socialNetworks) == dict:
            for site, data in socialNetworks.items():
                socialsLabels.append(genericLabel(site, data["userId"]))
        elif type(socialNetworks) == list:
            for e in socialNetworks:
                socialsLabels.append(genericLabel(e["site"], e["userId"]))
        return socialsLabels

    def getProfileStatsText(self, d):
        print("Profile details:", d)
        fields = []
        knownFields = {"@type", "photoMediaHashes", "profileImageMediaHash", "photoHash", "medias",
                       "approximateDistance", "isFavorite", "showAge", "showDistance",
                       "showTribes", "showPosition", "tapped", "tapType", "upsellItemType"}
        # These are "known" but not specifically handled. Only show when not an uninteresting default.
        hideDefaults = {"isBoosting": False,
                        "hasChattedInLast24Hrs": False,
                        "hasUnviewedSpark": False,
                        "isTeleporting": False,
                        "isRoaming": False,
                        "isRightNow": False,
                        "unreadCount": 0,
                        "rightNow": "NOT_ACTIVE",
                        "isPopular": False,
                        "hasUnreadThrob": False,
                        "isVisiting": False,
                        "isBoostingSomewhereElse": False,
                        "isNew": False,
                        "isInAList": False,
                        "showVipBadge": False}
        def get(fieldNames, defVal=None):
            if type(fieldNames) is not list:
                fieldNames = [fieldNames]
            nonlocal knownFields
            knownFields |= set(fieldNames)
            for f in fieldNames:
                # field can be missing or None
                res = d.get(f, None)
                if res:
                    return res
            return defVal
        def mapField(text, field):
            if type(field) is list:
                field = field[0]
            if text and field in self.mappings:
                text = self.mappings[field].get(str(text), text)
            return text
        def getMapped(field, mappingField=None):
            return mapField(get(field, None), mappingField or field)
        def getMappedList(field, mappingField=None):
            l = get(field, []) or []
            return [mapField(el, mappingField or field) for el in l]
        def add(text, img):
            if img:
                text = f'<img src="mydata://{img}" height=14/>&nbsp;{text}'
            fields.append(text)
        def addIf(cond, text, img=None):
            if cond:
                add(text, img)
        def addList(l, desc, img=None):
            if l:
                add(desc + ", ".join(l), img)
        displayName = escape(get("displayName", ""))
        if displayName:
            displayName += "\n"
        aboutText = escape(get("aboutMe", ""))
        distance = get(["distanceMeters", "distance"], -1)
        lastOnline = get("lastOnline", None)
        age = get("age", None)
        height = get(["height", "heightCm"], None)
        weight = get(["weight", "weightGrams"], None)
        lastTested = get("lastTestedDate", None)
        ethnicity = getMapped("ethnicity")
        bodyType = getMapped("bodyType")
        sexualPosition = getMapped("sexualPosition")
        sexualPositionIcon =  mapField(get("sexualPosition", None), "sexualPositionIcon")
        acceptsNsfwPics = getMapped(["acceptsNsfwPics", "acceptsNSFWPics", "nsfw"])
        relationshipStatus = getMapped("relationshipStatus")
        hivStatus = getMapped("hivStatus")
        sexualHealth = getMappedList("sexualHealth")
        genders = getMappedList("genders")
        tribes = getMappedList(["tribes", "grindrTribes"])
        tribesImInto = getMappedList("tribesImInto", "tribes")
        pronouns = getMappedList("pronouns")
        lookingFor = getMappedList("lookingFor")
        meetAt = getMappedList("meetAt")
        vaccines = getMappedList("vaccines")
        socialNetworks = get("socialNetworks", [])
        tags = get(["profileTags", "tags"])
        # About
        addIf(age, f"Age: {age}")
        addIf(distance > 0, "Distance: " + (f"{distance}m" if distance < 2000 else f"{distance/1000:.1f}km"), "profile_ic_location.svg")
        addIf(lastOnline, "Last online: " + formatTimeStamp(lastOnline))

        # Stats
        addIf(height, height and f"{height/100:.2f}m", "profile_stats.svg")
        addIf(weight, weight and f"{weight/1000:.0f}kg")
        addIf(bodyType, f"{bodyType}")
        addIf(sexualPosition, f"{sexualPosition}", sexualPositionIcon)
        addList(genders, "Gender: ", "profile_identity.svg")
        addList(pronouns, "Pronouns: ")
        addIf(ethnicity, f"{ethnicity}", "profile_ethnicity.svg")
        addIf(relationshipStatus, f"{relationshipStatus}", "profile_relationship_status.svg")
        addList(tribes, "", "profile_tribes.svg")
        addList(tribesImInto, "Tribes I'm into:", "profile_tribes.svg")

        # Expectations
        addList(lookingFor, "Looking for: ", "profile_looking_for.svg")
        addList(meetAt, "Meet at: ", "profile_meet_at.svg")
        addIf(acceptsNsfwPics, f"Accepts NSWF pics: {acceptsNsfwPics}", "profile_nsfw_pics.svg")

        # Health
        addIf(hivStatus, f"HIV status: {hivStatus}", "profile_sexual_health.svg")
        addIf(lastTested, f"Last tested: {formatTimeStampMonth(lastTested)}", "profile_last_tested.svg")
        addList(vaccines, "Vaccinated for: ")
        addList(sexualHealth, "Sexual health: ")

        # Socials
        socialsLabels = self._getSocialNetworks(socialNetworks)
        addIf(socialsLabels, "\n".join(socialsLabels))
        addList(tags, "Tags: ")

        result = displayName + "Details:\n" + aboutText + "\n\n" +  "\n".join(fields)
        unknown = []
        for k, v in d.items():
            if k not in knownFields and v is not None and (v or (type(v) != list and type(v) != dict)):
                if mightBeTimeStamp(v):
                    v = f"{formatTimeStamp(v)} ({v})"
                if k in hideDefaults:
                    if v != hideDefaults[k]:
                        unknown.append(f'<b style="color:#f44a48;">{k}:</b><b> {v}</b>')
                else:
                    unknown.append(f"{k}: {v}")
        if unknown:
            result += "\n\nOther fields:\n" + "\n".join(unknown)
        return result

    def loadSvgForSize(self, imgFileName, w, h):
        from PySide6 import QtSvg
        from .profilelistwidget import scaleTargetRect
        renderer = QtSvg.QSvgRenderer(imgFileName)
        qi = QtGui.QImage(w, h, QtGui.QImage.Format.Format_ARGB32)
        qi.fill(QtGui.QColor(0, 0, 0, 0))
        srcSize = renderer.defaultSize()
        srcRect = QtCore.QRect(0, 0, srcSize.width(), srcSize.height())        
        targetRect = QtCore.QRect(0, 0, w, h)
        targetRect = scaleTargetRect(srcRect, targetRect, noUpscale=False)
        p = QtGui.QPainter(qi)
        renderer.render(p, targetRect)
        p.end()
        return QtGui.QPixmap.fromImage(qi)

    def loadImageResources(self):
        import pathlib
        for img in pathlib.Path("resources/img/").glob("*.svg"):
            img = pathlib.Path(img).name
            pm = self.loadSvgForSize(f"resources/img/{img}", 28, 28)
            pm.setDevicePixelRatio(2)
            self.imageResourceCache[img] = pm
        self.addImageResources()

    def loadLogo(self):
        pixmap = QtGui.QPixmap("resources/img/logo.png")
        dpr = self.ui.logo.devicePixelRatio()
        pixmap.setDevicePixelRatio(dpr)
        self.ui.logo.setPixmap(pixmap)

    def addImageResources(self):
        doc = self.ui.profileText.document()
        for img, pm in self.imageResourceCache.items():
            doc.addResource(QtGui.QTextDocument.ResourceType.ImageResource,
                QtCore.QUrl(f"mydata://{img}"), pm)

    def displayProfileDetails(self, d):
        text = self.getProfileStatsText(d)
        text = f'<html><body>{text}</body</html>'
        text = text.replace("\n", "<br/>")
        #text = text.replace("mydata://", "resources/")
        self.ui.profileText.document().setHtml(text)

    def displayFavorite(self, isFavorite):
        icon = QtGui.QIcon("resources/img/favorite.png" if isFavorite else "resources/img/no_favorite.png")
        self.ui.setFavorite.setIcon(icon)
        self.ui.setFavorite.setText("Favorite" if isFavorite else "No Favorite")
        self.ui.setFavorite.setChecked(isFavorite)

    def checkFavorite(self, d):
        isFavorite = d.get("isFavorite", False)
        self.displayFavorite(isFavorite)

    def mapTapTypeToImage(self, tapType):
        if tapType == GrindrFlags.tap_type_hi:
            imgFile = "resources/img/friendly.svg"
        elif tapType == GrindrFlags.tap_type_hot:
            imgFile = "resources/img/hot.svg"
        elif tapType == GrindrFlags.tap_type_looking:
            imgFile = "resources/img/looking.svg"
        else:
            imgFile = ""
        return imgFile

    def displayTaps(self, tapTypeSent, tapTypeReceived):
        if tapTypeSent is not None:
            imgFile = self.mapTapTypeToImage(str(tapTypeSent))
            self.ui.labelTapSent.setText("Sent:")
            self.ui.tapSentIcon.setPixmap(QtGui.QPixmap(imgFile))
        else:
            self.ui.labelTapSent.clear()
            self.ui.tapSentIcon.clear()
        if tapTypeReceived is not None:
            imgFile = self.mapTapTypeToImage(str(tapTypeReceived))
            self.ui.labelTapReceived.setText("Received:")
            self.ui.tapReceivedIcon.setPixmap(QtGui.QPixmap(imgFile))
        else:
            self.ui.labelTapReceived.clear()
            self.ui.tapReceivedIcon.clear()

    def checkTaps(self, d):
        tapTypeSent, tapTypeReceived = None, None
        if d.get("tapped", False):
            tapTypeSent = str(d.get("tapType", GrindrFlags.tap_type_hot))
        receivedTaps = self.model.getReceivedTaps()
        for p in receivedTaps:
            if str(p["profileId"]) == d["profileId"]:
                tapTypeReceived = p.get("tapType", None)
                break
        self.displayTaps(tapTypeSent, tapTypeReceived)

    def _mediaDescription(self, imgHash):
        return media_description_from_hash(imgHash, MediaType.profile)

    def showProfileImages(self, d, isRefresh):
        self.imageHashes = self.model.getImageHashes(d)
        self.showImageLabels(len(self.imageHashes))
        for i, imgHash in enumerate(self.imageHashes):
            imgFileName = get_cached_image_name(self._mediaDescription(imgHash))
            if imgFileName:
                self.ui.imageLabels[i].setPixmap(QtGui.QPixmap(imgFileName))
            else:
                self.ui.imageLabels[i].setPixmap(self.loadingProfileImage)
                self.startBackgroundDownload(imgHash)
        if not isRefresh:
            self.ui.imageScrollArea.ensureVisible(0, 0)

    def startBackgroundDownload(self, imgHash):
        profile("I: Starting Background download of", imgHash)
        worker = DownloadWorker(self._mediaDescription(imgHash))
        worker.signals.finished.connect(self.downloadComplete)
        QtCore.QThreadPool.globalInstance().start(worker)

    @QtCore.Slot()
    def downloadComplete(self, imgDesc, imgFileName):
        profile("I: Finished Background download of", imgDesc.name)
        for hash, label in zip(self.imageHashes, self.ui.imageLabels):
            if imgDesc.name == hash or hash and imgDesc.name == base_hash_from_url(hash):
                label.setPixmap(QtGui.QPixmap(imgFileName))

    def refreshProfileView(self):
        self.displayProfile(self.currentProfileIdx)

    def clear(self):
        self.currentProfile, self.currentProfileIdx = None, None
        self.ui.profileText.document().clear()
        self.addImageResources()
        self.showImageLabels(0)
        self.displayFavorite(False)
        self.displayTaps(None, None)

    def displayProfile(self, profileId):
        if int(profileId) <= 0:
            self.clear()
            return
        profile("displayProfile begin", time_str())
        isRefresh = profileId == self.currentProfileIdx
        profile("displayProfile before getExtendedProfile")
        d = self.model.getExtendedProfile(profileId)
        profile("displayProfile before assignment")
        self.currentProfile, self.currentProfileIdx = d, profileId
        profile("displayProfile before displayProfileDetails")
        self.displayProfileDetails(d)
        profile("displayProfile before showProfileImages")
        self.showProfileImages(d, isRefresh)
        profile("displayProfile before checkFavorite")
        self.checkFavorite(d)
        profile("displayProfile before checkTaps")
        self.checkTaps(d)
        profile("displayProfile begin")
