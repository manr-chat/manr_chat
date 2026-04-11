#!/usr/bin/env python3

from typing import Any

from PySide6 import QtCore
from PySide6.QtUiTools import QUiLoader

from .grindr_access.grindr_user import GrindrUser
from .grindr_access.utils import gen_l_dev_info

class LoginDialog(QtCore.QObject):
    ui: Any

    def __init__(self, defUserName, model, userDb, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("logindialog.ui", parent)
        self.userDb = userDb
        self.user = None
        self.token = None
        self.fillUserNames()
        self.setupConnections()
        self.ui.userEmail.setCurrentText(defUserName)
        self.fillPassword(defUserName)

    def setupConnections(self):
        self.ui.userEmail.currentTextChanged.connect(self.on_userEmail_currentTextChanged)
        self.ui.buttonBox.accepted.connect(self.onLoginClicked)
        #self.ui.loginWithPassword.toggled.connect(self.ui.passwordGroup.setEnabled)

    def getUser(self):
        return self.user

    def fillUserNames(self):
        for name in self.userDb.getUserNames():
            self.ui.userEmail.addItem(name)

    def fillPassword(self, user):
        password, self.token = self.userDb.getCredentials(user)
        if password:
            self.ui.password.setText(password)
        if self.token:
            self.ui.loginWithToken.setEnabled(True)
            self.ui.loginWithToken.setChecked(True)
        else:
            self.ui.loginWithPassword.setChecked(True)
            self.ui.loginWithToken.setEnabled(False)

    def onLoginClicked(self):
        username = self.ui.userEmail.currentText()
        password = self.ui.password.text()
        device_info = self.userDb.getDeviceInfo(username)
        if not device_info:
            device_info = gen_l_dev_info()
        user = GrindrUser(username, device_info)
        # Try to log in
        if self.ui.loginWithToken.isChecked():
            assert self.token
            user.sessions(username, self.token)
            if not user.sessionId:
                self.userDb.updateToken(username, None)
                self.ui.loginWithPassword.setChecked(True)
                self.ui.loginWithToken.setEnabled(False)
                print("Error: could not log in with token")
        else:
            user.login(username, password)
            if not user.sessionId:
                print("Error: could not log in with password")
        if not user.sessionId:
            self.token = None
            return
        # Login successful
        pwd = password if self.ui.storePassword.isChecked() else None
        token = user.authToken if self.ui.storeSessionToken.isChecked() else None
        self.userDb.addUser(username, user.profileId, pwd, token, device_info)
        self.userDb.setLastUser(username)
        self.user = user
        print("Success:", self.user)
        self.ui.accept()

    def on_userEmail_currentTextChanged(self, user):
        self.fillPassword(user)


def showLoginDialog(defUserName, model, userDb, parent):
    dlg = LoginDialog(defUserName, model, userDb, parent)
    dlg.ui.exec()
    print("Result:", dlg.getUser())
    return dlg.getUser()
