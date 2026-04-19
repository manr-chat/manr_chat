#!/usr/bin/env python3

import keyring
from .appinfo import manr_app_name

serviceName = manr_app_name()

# Can't set multiple credentials for same service using keyring.
# Workaround: encode token in the user name. As the user name is
# an email address, this should not cause clashes.
def tokenKeyForUser(userName):
    return userName + "/__auth_token__"

# Swallow exceptions
def tryGetPassword(userName):
    try:
        return keyring.get_password(serviceName, userName)
    except:
        return None

def trySetPassword(userName, password):
    try:
        keyring.set_password(serviceName, userName, password)
        return True
    except:
        return False

def tryDeletePassword(userName):
    try:
        keyring.delete_password(serviceName, userName)
        return True
    except:
        return False

class UserDB:
    def __init__(self, settings):
        self.settings = settings
        self._loadFromSettings()

    def _loadFromSettings(self):
        numUsers = int(self.settings.value("users/number_of_users", 0))
        self.userNames = [self.settings.value(f"users/user_name_{i+1}") for i in range(numUsers)]
        self.profileIds = [self.settings.value(f"users/profile_id_{i+1}") for i in range(numUsers)]
        self.deviceInfos = [self.settings.value(f"users/device_info_{i+1}") for i in range(numUsers)]
        self.autoLogin = self.settings.value("users/auto_login") != "false"
        self.clearLocationOnLogin = self.settings.value("users/clear_location_on_login") != "false"
        self.lastUser = self.settings.value("users/last_user_name")

    def _saveUserData(self):
        self.settings.setValue("users/number_of_users", len(self.userNames))
        print("self.userNames:", self.userNames)
        print("self.profileIds:", self.profileIds)
        for i, (name, pid, di) in enumerate(zip(self.userNames, self.profileIds, self.deviceInfos)):
            self.settings.setValue(f"users/user_name_{i+1}", name)
            self.settings.setValue(f"users/profile_id_{i+1}", pid)
            self.settings.setValue(f"users/device_info_{i+1}", di)

    def getUserNames(self):
        return self.userNames

    def getAutoLogin(self):
        return self.autoLogin

    def setAutoLogin(self, autoLogin):
        self.autoLogin = autoLogin
        self.settings.setValue("users/auto_login", autoLogin)

    def getClearLocationOnLogin(self):
        return self.clearLocationOnLogin

    def setClearLocationOnLogin(self, clearLocation):
        self.clearLocationOnLogin = clearLocation
        self.settings.setValue("users/clear_location_on_login", clearLocation)

    def getLastUser(self):
        return self.lastUser

    def setLastUser(self, userName):
        self.lastUser = userName
        self.settings.setValue("users/last_user_name", userName)

    def getProfileId(self, userName):
        try:
            return self.profileIds[self.userNames.index(userName)]
        except:
            return -1

    def getDeviceInfo(self, userName):
        try:
            return self.deviceInfos[self.userNames.index(userName)]
        except:
            return None

    def getCredentials(self, userName):
        if not userName:
            return None, None
        password = tryGetPassword(userName)
        token = tryGetPassword(tokenKeyForUser(userName))
        return password, token

    def updatePassword(self, userName, password, removeIfEmpty=True):
        if password:
            return trySetPassword(userName, password)
        elif removeIfEmpty:
            return tryDeletePassword(userName)

    def updateToken(self, userName, token, removeIfEmpty=True):
        if token:
            return trySetPassword(tokenKeyForUser(userName), token)
        elif removeIfEmpty:
            return tryDeletePassword(tokenKeyForUser(userName))

    def updateCredentials(self, userName, password, token, removeIfEmpty=True):
        self.updatePassword(userName, password, removeIfEmpty)
        self.updateToken(userName, token, removeIfEmpty)

    def addUser(self, userName, profileId, password, token, deviceInfo, removeIfEmpty=True):
        # Add user name to settings
        if userName not in self.userNames:
            self.userNames.append(userName)
            self.profileIds.append(profileId)
            self.deviceInfos.append(deviceInfo)
            self._saveUserData()
        # Store/update or remove password and auth token
        self.updateCredentials(userName, password, token, removeIfEmpty)

    def removeUser(self, userName):
        tryDeletePassword(userName)
        tryDeletePassword(tokenKeyForUser(userName))
        if userName not in self.userNames:
            return
        self.settings.remove(f"users/user_name_{len(self.userNames)}")
        self.settings.remove(f"users/profile_id_{len(self.userNames)}")
        self.settings.remove(f"users/device_info_{len(self.userNames)}")
        self.userNames.remove(userName)
        self._saveUserData()
