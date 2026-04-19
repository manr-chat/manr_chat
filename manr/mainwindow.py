#!/usr/bin/env python3

import sys
import signal
import json
import logging
from typing import Any

#from PyQt6 import uic
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWebEngineWidgets import QWebEngineView

from .grindr_access.grindr_user import GrindrUser, GrindrUserOffline

from .albumwidget import AlbumWidget
from .albumlistwidget import AlbumListWidget
from .chatwidget import ChatWidget
from .chatlistwidget import ChatListWidget
from .detailsselectionwidget import DetailsSelectionWidget
from .filterdialog import showFilterDialog
from .locationdialog import showLocationDialog
from .logindialog import showLoginDialog
from .profiledetailswidget import ProfileDetailsWidget
from .profilelistwidget import ProfileListWidget
from .pageselectionwidget import PageSelectionWidget
from .statusbarcontrol import StatusBarControl

from .image_cache import *
from .datamodel import DataModel
from .userdb import UserDB
from .utils import profile
if sys.platform == 'win32':
    from .websocketconnection_curl import WebSocketConnection
else:
    from .websocketconnection import WebSocketConnection

class MainWindow:
    ui: Any

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.userDb = UserDB(settings)
        self.model = DataModel()
        self.websocket = WebSocketConnection()
        self.ui = QUiLoader().load("mainwindow.ui")
        self.first_log_message = True
        self.notificationPlayer = None
        self.buildWidgets()
        self.setupActionGroups()
        self.loadSettings()
        self.setupConnections()
        self.sessionTimer = None

    def init(self):
        self.tryAutoLogin()
        self.initAll()

    def setupConnections(self):
        self.profileList.ui.selectionModel().currentChanged.connect(self.on_profileList_currentChanged)
        self.favoriteList.ui.selectionModel().currentChanged.connect(self.on_favoriteList_currentChanged)
        self.viewedList.ui.selectionModel().currentChanged.connect(self.on_viewedList_currentChanged)
        self.tapsReceivedList.ui.selectionModel().currentChanged.connect(self.on_tapsReceivedList_currentChanged)
        self.tapsSentList.ui.selectionModel().currentChanged.connect(self.on_tapsSentList_currentChanged)
        self.albumList.ui.albumList.currentRowChanged.connect(self.on_albumList_currentRowChanged)
        self.chatList.ui.chatList.currentRowChanged.connect(self.on_chatList_currentRowChanged)
        self.ui.actionViewCropped.toggled.connect(self.on_actionViewCropped_toggled)
        self.ui.actionViewProfileId.triggered.connect(self.on_actionViewProfileId_triggered)
        self.ui.actionLogin.triggered.connect(self.on_actionLogin_triggered)
        self.ui.actionAutoLogin.triggered.connect(self.on_actionAutoLogin_triggered)
        self.ui.actionClearLocationOnLogin.triggered.connect(self.on_actionClearLocationOnLogin_triggered)
        self.pageSelector.ui.reloadProfiles.clicked.connect(self.on_reloadProfiles_clicked)
        self.pageSelector.ui.setFilter.clicked.connect(self.on_setFilter_clicked)
        self.pageSelector.ui.setLocation.clicked.connect(self.on_setLocation_clicked)
        self.pageSelector.ui.setExploreLocation.clicked.connect(self.on_setExploreLocation_clicked)
        self.pageSelector.ui.setRightNow.clicked.connect(self.on_setRightNow_clicked)
        self.model.signals.tapSent.connect(self.on_model_tapSent)
        self.model.signals.messageRead.connect(self.on_model_messageRead)
        # Websocket
        self.websocket.signals.received.connect(self.on_websocket_received)
        self.websocket.signals.error.connect(self.on_websocket_error)
        self.websocket.signals.closed.connect(self.on_websocket_closed)

    def buildWidgets(self):
        self.profileList = ProfileListWidget(self.model)
        self.profileList.setFilter(True)
        self.favoriteList = ProfileListWidget(self.model)
        self.viewedList = ProfileListWidget(self.model)
        self.tapsReceivedList = ProfileListWidget(self.model)
        self.tapsSentList = ProfileListWidget(self.model)
        self.albumList = AlbumListWidget(self.model)
        self.chatList = ChatListWidget(self.model)
        self.profileListWidgets = [self.profileList, self.favoriteList, self.viewedList, self.tapsReceivedList, self.tapsSentList]
        self.pageSelector = PageSelectionWidget()
        self.pageSelector.ui.tabProfiles.layout().addWidget(self.profileList.ui)
        self.pageSelector.ui.tabFavorites.layout().addWidget(self.favoriteList.ui)
        self.pageSelector.ui.tabChats.layout().addWidget(self.chatList.ui)
        self.pageSelector.ui.tabViewedBy.layout().addWidget(self.viewedList.ui)
        self.pageSelector.ui.tabTapsReceived.layout().addWidget(self.tapsReceivedList.ui)
        self.pageSelector.ui.tabTapsSent.layout().addWidget(self.tapsSentList.ui)
        self.pageSelector.ui.tabAlbums.layout().addWidget(self.albumList.ui)
        self.profileDetails = ProfileDetailsWidget(self.model)
        self.chatWidget = ChatWidget(self.model)
        self.albumWidget = AlbumWidget(self.model)
        self.detailsSelector = DetailsSelectionWidget()
        self.detailsSelector.ui.tabProfileDetails.layout().addWidget(self.profileDetails.ui)
        self.detailsSelector.ui.tabChat.layout().addWidget(self.chatWidget.ui)
        self.detailsSelector.ui.tabAlbum.layout().addWidget(self.albumWidget.ui)
        self.ui.splitter.addWidget(self.pageSelector.ui)
        self.ui.splitter.addWidget(self.detailsSelector.ui)
        self.ui.splitter.setSizes([150, 1])
        self.favoriteList.setDisplayFavIcon(False)
        self.favoriteList.setIconSize(QtCore.QSize(192, 192))
        self.statusBar = StatusBarControl(self, self.model, app)
        self.makeLoginMenu()
        self.makeLocationMenus()
        self.warmUpWebEngine()

    def warmUpWebEngine(self):
        # This prevents flickering the first time a QWebEngineView is shown
        dummy_webview = QWebEngineView(self.ui)
        dummy_webview.setHtml("")
        dummy_webview.hide()
        del dummy_webview

    def makeLoginMenu(self):
        menu = self.ui.menuLoginAs
        actions = []
        def makeLambda(n):
            return lambda: self.autoLoginAs(n)
        for name in self.userDb.getUserNames():
            actLogin = QtGui.QAction(name, menu)
            actLogin.triggered.connect(makeLambda(name))
            actions.append(actLogin)
        menu.addActions(actions)

    def makeExclusiveGroup(self, actions):
        group = QtGui.QActionGroup(self.ui)
        for action in actions:
            group.addAction(action)
        group.setExclusive(True)

    def makeLocationMenus(self):
        self.locationMenu = QtWidgets.QMenu(self.pageSelector.ui.setLocation)
        self.exploreMenu = QtWidgets.QMenu(self.pageSelector.ui.setExploreLocation)
        self.pageSelector.ui.setLocation.setMenu(self.locationMenu)
        self.pageSelector.ui.setExploreLocation.setMenu(self.exploreMenu)
        self.pageSelector.ui.setLocation.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.pageSelector.ui.setExploreLocation.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        # TODO: remove
        self.updateLocationMenus()

    def updateLocationMenus(self):
        self.locationMenu.clear()
        self.exploreMenu.clear()
        for name in self.model.getLocationList().keys():
            actLoc = QtGui.QAction(name, self.locationMenu)
            actExplore = QtGui.QAction(name, self.exploreMenu)
            actLoc.triggered.connect(lambda checked=False, name=name: self.on_changeLocation_triggered(name))
            actExplore.triggered.connect(lambda checked=False, name=name: self.on_changeExploreLocation_triggered(name))
            self.locationMenu.addAction(actLoc)
            self.exploreMenu.addAction(actExplore)
        self.locationMenu.addSeparator()
        self.exploreMenu.addSeparator()
        actEditLoc = QtGui.QAction("Edit locations...", self.locationMenu)
        actEditExplore = QtGui.QAction("Edit locations...", self.exploreMenu)
        actEditLoc.triggered.connect(self.on_editLocations_triggered)
        actEditExplore.triggered.connect(self.on_editExploreLocations_triggered)
        self.locationMenu.addAction(actEditLoc)
        self.exploreMenu.addAction(actEditExplore)

    def setupActionGroups(self):
        self.makeExclusiveGroup([self.ui.actionViewCropped, self.ui.actionViewLetterboxed])

    def setupSessionTimer(self):
        if self.sessionTimer:
            return
        self.sessionTimer = QtCore.QTimer()
        self.sessionTimer.start(2*60*1000)
        self.sessionTimer.timeout.connect(self.keepSessionAlive)

    def loadSettings(self):
        self.offlineMode = self.settings.value("offlineMode", False) == "true"
        if not self.settings.value("ui/view_cropped") == "false":
            self.ui.actionViewCropped.setChecked(True)
        else:
            self.ui.actionViewLetterboxed.setChecked(True)
        self.setViewMode(self.ui.actionViewCropped.isChecked())
        self.ui.actionAutoLogin.setChecked(self.userDb.getAutoLogin())
        self.ui.actionClearLocationOnLogin.setChecked(self.userDb.getClearLocationOnLogin())
        try:
            filename = str(get_config_dir() / "known_image_hashes.json")
            self.model.setKnownImageHashes(load_json(filename))
        except:
            pass

    def saveKnownImageHashes(self):
        filename = str(get_config_dir() / "known_image_hashes.json")
        save_json(filename, self.model.getKnownImageHashes())

    def saveUserData(self):
        if self.model.user:
            self.saveUserSettings()
            self.saveDataCache()

    def saveDataCache(self):
        profile("In saveDataCache")
        filename = str(get_config_dir() / f"profile_{self.model.user.profileId}_cache.json")
        save_json(filename, self.model.getCachedData())

    def saveUserSettings(self):
        profile("In saveUserSettings")
        filename = str(get_config_dir() / f"profile_{self.model.user.profileId}_settings.json")
        save_json(filename, self.model.getUserSettings())

    def loadDataCache(self, profileId):
        cache = None
        try:
            filename = str(get_config_dir() / f"profile_{profileId}_cache.json")
            profile("Trying to read user cache file:", filename)
            cache = load_json(filename)
        except Exception as e:
            print("Could not load user cache file:", e)
            pass
        return cache

    def loadUserSettings(self, profileId):
        userSettings = None
        try:
            filename = str(get_config_dir() / f"profile_{profileId}_settings.json")
            profile("Trying to read user settings file:", filename)
            userSettings = load_json(filename)
        except Exception as e:
            print("Could not load user settings file:", e)
            pass
        return userSettings

    def shutdown(self):
        self.saveKnownImageHashes()
        self.saveUserData()
        self.websocket.disconnect()

    def on_actionViewCropped_toggled(self, checked):
        self.setViewMode(checked)
        self.settings.setValue("ui/view_cropped", checked)

    def on_actionViewProfileId_triggered(self, checked):
        profileId, ok = QtWidgets.QInputDialog.getInt(self.ui, "Enter profile ID", "Look up a profile by ID:")
        print("profileId:", profileId)
        if ok and profileId > 0:
            self.displayProfile(profileId)

    def setViewMode(self, cropped):
        for l in self.profileListWidgets:
            l.setViewMode(cropped)

    def tryAutoLogin(self):
        if self.userDb.getAutoLogin():
            username = self.userDb.getLastUser()
            self.loginAs(username)

    def autoLoginAs(self, username):
        if self.model.user and self.model.user.email == username:
            return
        self.loginAs(username)
        self.initAll()

    def loginAs(self, username):
        pbegin = profile("loginAs begin")
        password, token = self.userDb.getCredentials(username)
        deviceInfo = self.userDb.getDeviceInfo(username)
        if self.offlineMode:
            print("Using offline mode!")
            pid = self.userDb.getProfileId(username)
            user = GrindrUserOffline(username, pid)
        else:
            user = GrindrUser(username, deviceInfo)
            if username and (password or token):
                if token:
                    user.sessions(username, token)
                if password and not user.sessionId:
                    user.login(username, password)
                    if user.sessionId and user.authToken != token:
                        self.userDb.updateCredentials(username, password, token)
        if user.sessionId:
            puser = profile("loginAs setUser", start=pbegin)
            self.setUser(user)
            profile("loginAs end", start=(puser, pbegin))
            return
        profile("loginAs showLoginDialog", start=pbegin)
        self.showLoginDialog(username)

    def showLoginDialog(self, username=None):
        # TODO: offline mode
        user = showLoginDialog(username, self.model, self.userDb, self.ui)
        if user:
            self.setUser(user)

    def setUser(self, user):
        if self.model.user:
            self.saveUserData()
        cache = self.loadDataCache(user.profileId)
        userSettings = self.loadUserSettings(user.profileId)
        self.model.setUser(user, self.offlineMode, userSettings, cache)
        if self.userDb.getClearLocationOnLogin():
            self.model.setLocation(None)
        self.userDb.setLastUser(user.email)
        self.updateLocationMenus()
        self.setupSessionTimer()

    def keepSessionAlive(self):
        if self.model.user:
            self.model.user.sessions()

    def reloadProfilesView(self):
        pbegin = profile("reloadProfilesView begin")
        if self.pageSelector.ui.setRightNow.isChecked():
            self.initRightNow()
        elif self.pageSelector.ui.setExploreLocation.isChecked():
            locname = self.model.currentExploreLocation
            locations = self.model.getLocationList()
            if locname in locations:
                self.initExploreLocation(locations[locname])
        else:
            location = self.model.getLocation()
            self.initLocation(location)
        profile("reloadProfilesView end", pbegin)

    def on_actionLogin_triggered(self):
        self.showLoginDialog(self.userDb.getLastUser())
        self.initAll()

    def on_actionAutoLogin_triggered(self, checked):
        self.userDb.setAutoLogin(checked)

    def on_actionClearLocationOnLogin_triggered(self, checked):
        self.userDb.setClearLocationOnLogin(checked)

    def on_reloadProfiles_clicked(self):
        self.reloadProfilesView()

    def on_setLocation_clicked(self):
        self.reloadProfilesView()

    def on_setExploreLocation_clicked(self):
        self.reloadProfilesView()

    def on_setRightNow_clicked(self):
        self.initRightNow()

    def on_setFilter_clicked(self):
        filter = showFilterDialog(self.model.getSearchFilter(), self.ui)
        if filter:
            self.model.setSearchFilter(filter)
            self.reloadProfilesView()

    def on_changeLocation_triggered(self, name):
        # TODO: warn if too far away!
        self.model.setCurrentLocation(name)
        self.pageSelector.ui.setLocation.setChecked(True)
        self.reloadProfilesView()

    def on_changeExploreLocation_triggered(self, name):
        self.model.setExploreLocation(name)
        self.pageSelector.ui.setExploreLocation.setChecked(True)
        self.reloadProfilesView()

    def on_editLocations_triggered(self):
        loc = showLocationDialog(self.model, self.ui)
        if loc is not None:
            self.updateLocationMenus()
            self.on_changeLocation_triggered(loc[0])

    def on_editExploreLocations_triggered(self):
        loc = showLocationDialog(self.model, self.ui)
        if loc is not None:
            self.updateLocationMenus()
            self.on_changeExploreLocation_triggered(loc[0])

    def initAll(self):
        pbegin = profile("initAll begin")
        self.statusBar.updateLoginStatus(self.offlineMode, True)
        if not self.model.user:
            return
        with override_cursor():
            self.initWebsocket()
            self.initViews()
            location = self.model.getLocation()
            print("location:", location)
            self.initLocation(location)
            self.initChats()
            self.initAlbums()
            self.setCounterLabels()
        self.statusBar.updateLoginStatus(self.offlineMode, self.websocket.isConnected())
        profile("initAll end", start=pbegin)

    def initWebsocket(self):
        if not self.offlineMode:
            pbegin = profile("initWebsocket begin")
            try:
                self.websocket.connect(self.model.user)
                self.model.setWebSocket(self.websocket)
                self.websocket.runReceiverThread()
            except Exception as e:
                print("ERROR: Could not connect to websocket:", e)
            finally:
                profile("initWebsocket end", start=pbegin)

    def toProfileList(self, l):
        return [{"data": e} for e in l]

    def initViews(self):
        pbegin = profile("initViews begin")
        # get data
        favdata = self.model.getFavorites()
        owndata = [self.model.getProfileDetails(self.model.user.profileId)]
        views = self.model.getViews()
        tapsReceived = self.model.getReceivedTaps()
        tapsSent = self.model.getSentTaps()
        tapsSent = [self.model.getExtendedProfile(e["receiverId"]) for e in tapsSent]
        pdata = profile("initViews data received", start=pbegin)
        # format lists
        favdata = self.toProfileList(favdata)
        owndata = self.toProfileList(owndata)
        views = self.toProfileList(views)
        tapsReceived = self.toProfileList(tapsReceived)
        tapsSent = self.toProfileList(tapsSent)
        profiles = owndata + favdata + tapsReceived
        if not self.offlineMode:
            self.model.setProfiles(profiles)
        pformat = profile("initViews lists formatted", start=pdata)
        # fill UI
        self.favoriteList.populateList(owndata + favdata)
        self.viewedList.populateList(views)
        self.tapsReceivedList.populateList(tapsReceived)
        self.tapsSentList.populateList(tapsSent)
        profile("initViews end", start=(pformat, pbegin))

    def initLocation(self, location):
        pbegin = profile("initLocation begin")
        filter = self.model.getEffectiveSearchFilter()
        print("Filter:", filter)
        if location:
            nearby = self.model.getNearbyProfiles(location, filter=filter, numPages=1)
        else:
            nearby = []
        pdata = profile("initLocation data received", start=pbegin)
        # fill UI
        if location and not self.model.offlineMode:
            self.model.setProfiles(nearby)
        self.profileList.populateList(nearby)
        profile("initLocation end", start=(pdata, pbegin))

    def initExploreLocation(self, location):
        pbegin = profile("initExploreLocation begin")
        filter = self.model.getEffectiveSearchFilter()
        print("Filter:", filter)
        explore = self.model.getExploreProfiles(location, filter=filter, numPages=1)
        pdata = profile("initExploreLocation data received", start=pbegin)
        self.profileList.populateList(explore)
        profile("initExploreLocation end", start=(pdata, pbegin))

    def initRightNow(self):
        pbegin = profile("initRightNow begin")
        rightnow = self.model.getRightNowProfiles(filter=None)
        pdata = profile("initRightNow data received", start=pbegin)
        self.profileList.populateList(rightnow)
        profile("initRightNow end", start=(pdata, pbegin))

    def initChats(self):
        pbegin = profile("initChats begin")
        chats = self.model.getChats()
        pdata = profile("initChats data received", start=pbegin)
        if chats:
            self.chatList.populateList(chats)
        profile("initChats end", start=(pdata, pbegin))

    def initAlbums(self):
        pbegin = profile("initAlbums begin")
        albums = self.model.getAlbums()
        pdata = profile("initAlbums data received", start=pbegin)
        if albums:
            self.albumList.populateList(albums)
        profile("initAlbums end", start=(pdata, pbegin))

    def initViewedList(self):
        views = self.model.getViews()
        views = self.toProfileList(views)
        self.viewedList.populateList(views)
        self.setCounterLabels()

    def initReceivedTaps(self):
        tapsReceived = self.model.getReceivedTaps()
        tapsReceived = self.toProfileList(tapsReceived)
        self.tapsReceivedList.populateList(tapsReceived)
        self.setCounterLabels()

    def initTapsSent(self):
        tapsSent = self.model.getSentTaps()
        tapsSent = [self.model.getExtendedProfile(e["receiverId"]) for e in tapsSent]
        tapsSent = self.toProfileList(tapsSent)
        self.tapsSentList.populateList(tapsSent)
        self.setCounterLabels()

    def setCounterLabels(self):
        pbegin = profile("setCounterLabels begin")
        tw = self.pageSelector.ui.tabWidget
        twt = self.pageSelector.ui.tabWidgetTaps
        numProfiles = self.profileList.ui.model().rowCount()
        numFavs = self.favoriteList.ui.model().rowCount()
        numUnreadChats = self.chatList.unreadCount
        numViews = self.viewedList.ui.model().rowCount()
        numTapsReceived = self.tapsReceivedList.ui.model().rowCount()
        numTapsSent = self.tapsSentList.ui.model().rowCount()
        #tw.setTabText(0, f"Profiles ({numProfiles})")
        #tw.setTabText(1, f"Favorites ({numFavs})")
        tw.setTabText(2, f"Chats ({numUnreadChats})" if numUnreadChats else "Chats")
        #tw.setTabText(3, f"Taps/Views ({numViews+numTapsReceived+numTapsSent})")
        twt.setTabText(0, f"Viewed by ({numViews})")
        twt.setTabText(1, f"Taps received ({numTapsReceived})")
        twt.setTabText(2, f"Taps sent ({numTapsSent})")
        profile("setCounterLabels end", start=pbegin)

    def onProfileListSelected(self, listWidget, curIdx):
        pbegin = profile("onProfileListSelected begin")
        profileId = listWidget.getProfileId(curIdx)
        assert profileId == listWidget.getCurrentProfileId()
        if int(profileId) <= 0:
            imgHash = listWidget.getImageHash(curIdx)
            profileId = self.model.lookupProfileFromImageHash(imgHash) or profileId
        self.displayProfile(profileId)
        profile("onProfileListSelected end", start=pbegin)

    def on_profileList_currentChanged(self, curIdx, prevIdx):
        self.onProfileListSelected(self.profileList, curIdx)

    def on_favoriteList_currentChanged(self, curIdx, prevIdx):
        self.onProfileListSelected(self.favoriteList, curIdx)

    def on_viewedList_currentChanged(self, curIdx, prevIdx):
        self.onProfileListSelected(self.viewedList, curIdx)

    def on_tapsReceivedList_currentChanged(self, curIdx, prevIdx):
        self.onProfileListSelected(self.tapsReceivedList, curIdx)

    def on_tapsSentList_currentChanged(self, curIdx, prevIdx):
        self.onProfileListSelected(self.tapsSentList, curIdx)

    def displayProfile(self, profileId, albumId=None):
        if profileId:
            self.profileDetails.displayProfile(profileId)
            self.chatWidget.displayChat(profileId)
        if albumId:
            self.albumWidget.displayAlbum(albumId)

    def on_model_tapSent(self):
        self.initTapsSent()

    def on_model_messageRead(self, convId, _msgId):
        self.chatList.conversationRead(convId)
        self.setCounterLabels()

    def on_chatList_currentRowChanged(self, curRow):
        pbegin = profile("on_chatList_currentRowChanged begin")
        profileId = self.chatList.getProfileId(curRow)
        self.displayProfile(profileId)
        profile("on_chatList_currentRowChanged end", start=pbegin)

    def on_albumList_currentRowChanged(self, curRow):
        pbegin = profile("on_albumList_currentRowChanged begin")
        profileId = self.albumList.getProfileId(curRow)
        albumId = self.albumList.getAlbumId(curRow)
        self.displayProfile(profileId, albumId)
        profile("on_albumList_currentRowChanged end", start=pbegin)

    def log_websocket_message(self, msg):
        filename = str(get_cache_dir() / "websocket_log.txt")
        with open(filename, "a", encoding="utf-8") as file:
            if self.first_log_message:
                self.first_log_message = False
                print("", file=file)
            print("Websocket message received:", msg, file=file)

    def on_websocket_received(self, msg):
        print("Websocket message received:", msg)
        self.log_websocket_message(msg)
        msg = json.loads(msg)
        if msg["type"] == "chat.v1.message_sent":
            self.chatWidget.refreshChat()
            chat = msg["payload"]
            self.chatList.newChat(chat["senderId"], chat["conversationId"],
                                  chat["type"], chat["body"], chat["timestamp"])
            if chat["type"] == "Album":
                self.initAlbums()
            self.statusBar.chatNotification(chat["senderId"], chat["type"], chat["body"])
            self.setCounterLabels()
        elif msg["type"] == "viewed_me.v1.new_view_received":
            view = msg["payload"]["mostRecent"]
            if "profileId" in view and "photoHash" in view:
                self.model.setProfileForImageHash(view["profileId"], view["photoHash"])
            self.initViewedList()
            self.statusBar.viewNotification(view["profileId"], view["photoHash"])
            self.setCounterLabels()
        elif msg["type"] == "tap.v1.tap_sent":
            tap = msg["payload"]
            self.initReceivedTaps()
            self.statusBar.tapNotification(tap["senderId"], tap["tapType"], tap["senderProfileImageHash"])
            self.setCounterLabels()

    def on_websocket_error(self, error_tuple):
        exctype, value, traceback = error_tuple
        print("Websocket error:", exctype, value, "\n", traceback)

    def on_websocket_closed(self):
        print("Websocket closed.")

def moveToLargestScreen(app, window):
    screens = app.screens()
    largest = screens[0]
    for i, s in enumerate(screens[1:]):
        if s.availableSize().height() > largest.availableSize().height():
            largest = s
    window.ui.winId() # make sure windowHandle can be called
    window.ui.windowHandle().setScreen(largest)

def initConfig():
    from .grindr_access.generic_request import set_cookie_file_location
    cookie_file = str(get_cache_dir() / "cookies.txt")
    set_cookie_file_location(cookie_file)

def createSettingsInstance():
    from pathlib import Path
    file = get_config_dir() / "settings.ini"
    return QtCore.QSettings(str(file), QtCore.QSettings.Format.IniFormat)

def installSignalHandler():
    def handleSigTerm(signum, frame):
        global quitFromSignal
        quitFromSignal = True
    signal.signal(signal.SIGTERM, handleSigTerm)

def checkForQuit():
    if quitFromSignal:
        app.quit()

app: QtWidgets.QApplication
quitFromSignal = False

def main(args=None):
    if args is None:
        args = sys.argv
    global app
    QtWidgets.QApplication.setDesktopFileName("manr")
    app = QtWidgets.QApplication(sys.argv)
    #logging.basicConfig(
    #    format="%(asctime)s %(message)s",
    #    level=logging.DEBUG
    #)
    installSignalHandler()
    initConfig()
    timer = QtCore.QTimer() # Process signals quickly
    timer.start(200)
    timer.timeout.connect(checkForQuit)
    app.setStyle("Fusion")
    app.setWindowIcon(QtGui.QIcon("resources/img/icon.ico"))
    settings = createSettingsInstance()
    if "--online" in args:
        settings.setValue("offlineMode", "false")
    elif "--offline" in args:
        settings.setValue("offlineMode", "true")
    window = MainWindow(settings)
    moveToLargestScreen(app, window)
    window.ui.showMaximized()
    window.init()
    exitCode = app.exec()
    window.shutdown()
    sys.exit(exitCode)

if __name__ == "__main__":
    main(sys.argv[1:])
