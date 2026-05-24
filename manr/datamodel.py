#!/usr/bin/env python3

import json
from typing import Any
from uuid import uuid4
from urllib.parse import quote_plus
from PySide6 import QtCore

from .grindr_access.grindr_user import GrindrUser
from .grindr_access.generic_request import generic_get, generic_post
from .grindr_access.utils import to_geohash
from .image_cache import *
from .utils import *

class DataModelSignals(QObject):
    tapSent = QtCore.Signal()
    messageRead = QtCore.Signal(str, str)

class DataModel:
    user: GrindrUser | Any

    def __init__(self):
        self.signals = DataModelSignals()
        self.clear()
        self.user = None
        self.websocket = None
        self.offlineMode = True
        self.location = None
        self.locationList = {}
        self.currentLocation = None
        self.currentExploreLocation = None
        self.searchFilter = {}

    def clear(self):
        self.profiles = []
        self.idMap = {}
        self.knownImageHashes = {}
        self.profileDetailsCache = {}
        self.nearbyCache = {}
        self.exploreCache = {}
        self.rightNowCache = {}
        self.favoritesCache = {}
        self.receivedTapsCache = {}
        self.sentTapsCache = {}
        self.viewsCache = {}
        self.chatsListCache = {"entries": []}
        self.conversationCache = {}
        self.albumListCache = {}
        self.albumsCache = {}
        self.refreshedProfiles = set()
        self.messageReadCache = set()

    def setUser(self, user, offline, userSettings, cache):
        self.clear()
        if cache:
            self._setCachedData(cache)
        self.offlineMode = offline
        self.user = user
        self._setUserSettings(userSettings if userSettings else {})

    def setWebSocket(self, websocket):
        self.websocket = websocket

    def setKnownImageHashes(self, known):
        self.knownImageHashes.update(known)

    def getKnownImageHashes(self):
        return self.knownImageHashes

    def _setCachedData(self, cache):
        self.setProfiles(cache["profiles"])
        get = lambda key: cache.get(key, {})
        self.profileDetailsCache = get("profileDetails")
        self.nearbyCache = get("nearbyProfiles")
        self.exploreCache = get("exploreProfiles")
        self.favoritesCache = get("favorites")
        self.receivedTapsCache = get("receivedTaps")
        self.sentTapsCache = get("sentTaps")
        self.viewsCache = get("views")
        self.chatsListCache = get("chatsList")
        self.conversationCache = get("conversations")
        self.albumListCache = get("albumList")
        self.albumsCache = get("albums")

    def getCachedData(self):
        return {"profiles": self.profiles,
                "profileDetails": self.profileDetailsCache,
                "nearbyProfiles": self.nearbyCache,
                "exploreProfiles": self.exploreCache,
                "favorites": self.favoritesCache,
                "receivedTaps": self.receivedTapsCache,
                "sentTaps": self.sentTapsCache,
                "views": self.viewsCache,
                "chatsList": self.chatsListCache,
                "conversations": self.conversationCache,
                "albumList": self.albumListCache,
                "albums": self.albumsCache}

    def getUserSettings(self):
        return {"location": self.location, "currentLocation": self.currentLocation,
                "locationList": self.locationList, "searchFilter": self.searchFilter}

    def _setUserSettings(self, settings):
        def updateKey(k):
            if k in settings:
                setattr(self, k, settings[k])
        for k in ["location", "currentLocation", "locationList", "searchFilter"]:
            updateKey(k)

    def _updateMaps(self):
        self.idMap = {str(p["data"]["profileId"]): idx for idx, p in enumerate(self.profiles)}
        for p in self.profiles:
            for h in self.getImageHashes(p["data"]):
                self.knownImageHashes[h] = int(p["data"]["profileId"])

    def setProfiles(self, profiles):
        self.profiles = profiles
        self._updateMaps()

    def appendProfiles(self, profiles):
        for p in profiles:
            if p["data"]["profileId"] not in self.idMap:
                self.profiles.append(p)
        self._updateMaps()

    def getProfileDetails(self, profileId):
        profileId = str(profileId)
        shouldUpdate = not self.offlineMode and profileId not in self.refreshedProfiles
        if profileId not in self.profileDetailsCache or shouldUpdate:
            response = self.user.get_profile(profileId) if int(profileId) > 0 and not self.offlineMode else None
            if response:
                if len(response["profiles"]) == 0: # blocked or server error
                    data = {"profileId": profileId, "displayName": "<Unknown/Blocked>"}
                else:
                    data = response["profiles"][0]
                    for p in response["profiles"]:
                        for h in self.getImageHashes(p):
                            self.knownImageHashes[h] = int(profileId)
            else:
                if profileId not in self.profileDetailsCache:
                    data = {"profileId": profileId}
                else:
                    data = self.profileDetailsCache[profileId]
            assert str(data["profileId"]) == profileId
            self.profileDetailsCache[profileId] = data
            self.refreshedProfiles.add(profileId)
        return self.profileDetailsCache[profileId]

    def clearProfileDetails(self, profileId):
        if not self.offlineMode:
            profileId = str(profileId)
            del self.profileDetailsCache[profileId]

    def getProfile(self, profileId):
        if profileId not in self.idMap:
            return {"profileId": profileId}
        idx = self.idMap[profileId]
        return self.profiles[idx]["data"]

    def getExtendedProfile(self, profileId):
        overview = self.getProfile(profileId)
        details = self.getProfileDetails(profileId)
        result = overview | details
        result["profileId"] = str(result["profileId"])
        #print("overview:", overview)
        #print("details:", details)
        #print("result:", result)
        return result

    def setProfileForImageHash(self, profileId, imgHash):
        profileId = int(profileId)
        if imgHash in self.knownImageHashes:
            assert self.knownImageHashes[imgHash] == profileId
        self.knownImageHashes[imgHash] = profileId

    def lookupProfileFromImageHash(self, imgHash):
        profileId = self.knownImageHashes.get(imgHash, None)
        return str(profileId) if profileId else profileId

    def getImageHashes(self, d):
        img_hashes = d.get("photoMediaHashes", [])
        if "profileImageMediaHash" in d:
            img_hashes.append(d["profileImageMediaHash"])
        if "photoHash" in d:
            img_hashes.append(d["photoHash"])
        if "mediaHash" in d:
            img_hashes.append(d["mediaHash"])
        for m in d.get("medias", []):
            img_hashes.append(m["mediaHash"])
        for m in d.get("media", []):
            if "data" in m and "thumbnailUrl" in m["data"]:
                img_hashes.append(m["data"]["thumbnailUrl"])
            if "data" in m and "fullImageUrl" in m["data"]:
                img_hashes.append(m["data"]["fullImageUrl"])
        if "rightNowFullImageUrl" in d:
            img_hashes.append(d["rightNowFullImageUrl"])
        img_hashes = [hash_from_str(s) for s in img_hashes]
        imgs = unique_list(img_hashes)
        if None in imgs:
            imgs.remove(None)
        return imgs

    def _getProfiles(self, apiFunc, cache, location, filter, numPages):
        #types = set()
        if not self.offlineMode:
            if not location:
                location = self.location
                if not location:
                    return cache
            profiles = []
            for page in range(1, numPages+1):
                print("Getting profiles page:", page)
                print("Location:", location, "geohash:", to_geohash(*location))
                p = apiFunc(*location, filter=filter, page=page)["items"]
                print("Profiles (unfiltered) on page", page, ":", len(p))
                profiles += p
            # Filter non-profile entries like Xtra and other upsell crap
            #for i, e in enumerate(profiles):
            #    print(i, e["type"], "profileId" in e["data"])
            #    types.add(e["type"])
            #    if "profileId" not in e["data"]:
            #        print(i, json.dumps(e))
            allProfiles = profiles
            profiles = [e for e in profiles if "profileId" in e["data"]]
            topPicks = []
            for e in allProfiles:
                if "profileId" not in e["data"]:
                    if e["type"].startswith("top_picks"):
                        picks = e["data"]["items"]
                        picks = [{"type": i["@type"], "data": i["profileItem"]} for i in picks]
                        topPicks += picks
            profiles += topPicks
            cache = profiles
        #print("Item types:", types)
        return cache

    def getNearbyProfiles(self, location=None, filter=None, numPages=1):
        return self._getProfiles(self.user.getProfiles, self.nearbyCache,
                                 location, filter, numPages)

    def getExploreProfiles(self, location=None, filter=None, numPages=1):
        return self._getProfiles(self.user.getExploreProfiles, self.exploreCache,
                                 location, filter, numPages)

    def getRightNowProfiles(self, filter=None):
        if not self.offlineMode:
            rightNow = self.user.get_right_now()["items"]
            # Filter non-profile entries like Xtra and other upsell crap
            rightNow = [e for e in rightNow if "profileId" in e["data"]]
            self.rightNowCache = rightNow
        return self.rightNowCache

    def getReceivedTaps(self):
        # TODO: some kind of caching, maybe timing based.
        # Official client probably checks this once and then relies on XMPP messages
        # for change notifications.
        if not self.offlineMode:
            self.receivedTapsCache = self.user.get_taps()["profiles"]
        return self.receivedTapsCache

    def getSentTaps(self):
        if not self.offlineMode:
            self.sentTapsCache = self.user.get_sent_taps()
        return self.sentTapsCache

    def getViews(self):
        if not self.offlineMode:
            self.viewsCache = self.user.get_views()
        return self.viewsCache.get("profiles", []) + self.viewsCache.get("previews", [])

    def getFavorites(self):
        if not self.offlineMode:
            self.favoritesCache = self.user.get_favorites()["favorites"]
            for fe in self.favoritesCache:
                fe["isFavorite"] = True
                self.getProfile(fe["profileId"])["isFavorite"] = True
                #if fe["profileId"] in self.idMap:
                #    idx = self.idMap[fe["profileId"]]
                #    self.profiles[idx]["data"]["isFavorite"] = True
        return self.favoritesCache

    def getConversationId(self, profileId):
        p1, p2 = int(self.user.profileId), int(profileId)
        #assert p1 != p2
        if p1 > p2:
            p1, p2 = p2, p1
        return f"{p1}:{p2}"

    def getConversationPartner(self, conversationId):
        p1, p2 = conversationId.split(":")
        assert p1 == self.user.profileId or p2 == self.user.profileId
        userId = p1 if p1 != self.user.profileId else p2
        return userId

    def getChats(self):
        if not self.offlineMode:
            def isChatInList(c, l):
                for e in l:
                    if c["conversationId"] == e["conversationId"] and \
                       c["preview"]["messageId"] == e["preview"]["messageId"]:
                       return True
                return False
            def isConversationInList(c, l):
                for e in l:
                    if c["conversationId"] == e["conversationId"]:
                       return True
                return False
            allChats = {"entries": []}
            page = 1
            disallowCache, breakEarly = False, False
            # We try to use the cache of messages to only download pages we haven't seen yet.
            # If we find a message that's already in the cache, we stop early, unless we detect an
            # inconcistency during race conditions. Note that this won't detect races where chats
            # get deleted and thus entries get shifted to a previous page.
            while True:
                pageChats = self.user.get_chats(page=page)
                for c in pageChats["entries"]:
                    if isChatInList(c, allChats["entries"]):
                        # We found an entry that already existed in the previous page.
                        # Probably a race condition between getting multiple pages. Don't use the
                        # cache to stop early.
                        disallowCache = True
                        break
                if not disallowCache:
                    for c in pageChats["entries"]:
                        if isChatInList(c, self.chatsListCache["entries"]):
                            breakEarly = True
                            break
                allChats["entries"] += pageChats["entries"]
                nextPage = pageChats["nextPage"]
                assert nextPage is None or nextPage == page+1
                page = nextPage
                if breakEarly or not page:
                    break
            # Add conversations from the cache we didn't download or which expired on the server
            for c in self.chatsListCache["entries"]:
                if not isConversationInList(c, allChats["entries"]):
                    allChats["entries"].append(c)
            self.chatsListCache = allChats
        return self.chatsListCache

    def _hasMoreDetails(self, m, cm):
        if "url" in cm["body"] and cm["body"]["url"] and not m["body"]["url"]:
            return False
        return True

    def _updateConversationCache(self, convId, conv):
        if convId not in self.conversationCache:
            self.conversationCache[convId] = conv
            return
        cconv = self.conversationCache[convId]['messages']
        for m in conv['messages']:
            for i, cm in enumerate(cconv):
                if m["messageId"] == cm["messageId"]:
                    if self._hasMoreDetails(m, cm):
                        cconv[i] = m
                        print("Updating with:\n", m)
                    else:
                        print("Keeping old message:\n", cm, "\n", m)
                    break
            else:
                print("Appending new message:\n", m)
                cconv.append(m)

    def getChat(self, profileId):
        convId = self.getConversationId(profileId)
        cachedConv = self.conversationCache.get(convId, None)
        if self.offlineMode:
            return cachedConv
        def isMsgInList(c, l):
            for e in l:
                assert c["conversationId"] == e["conversationId"]
                if c["messageId"] == e["messageId"]:
                    return True
            return False
        pageKey = None
        conv = None
        while True:
            convPage = self.user.get_conversation(convId, pageKey)
            if conv:
                conv["messages"] += convPage["messages"]
            else:
                conv = convPage
            if not convPage["messages"]:
                break
            if cachedConv and isMsgInList(convPage["messages"][-1], cachedConv['messages']):
                break
            pageKey = convPage["messages"][-1]["messageId"]
        if conv:
            self._updateConversationCache(convId, conv)
        return self.conversationCache[convId]

    def _getCachedChatMessage(self, convId, msgId):
        if convId not in self.conversationCache:
            return None
        conv = self.conversationCache[convId]
        for m in conv['messages']:
            if m["messageId"] == msgId:
                return m
        return None

    def getChatMessage(self, convId, msgId):
        #print("In getChatMessage:", convId, msgId)
        if not self.offlineMode:
            msg = self.user.get_message(convId, msgId)
            #print("In getChatMessage:\nmsg=", msg)
            if msg and "message" in msg:
                m = msg["message"]
                assert m["messageId"] == msgId
                conv = {"messages": [m]}
                self._updateConversationCache(convId, conv)
        return self._getCachedChatMessage(convId, msgId)

    def getAlbums(self):
        if not self.offlineMode:
            self.albumListCache = self.user.get_albums()
        return self.albumListCache

    def getAlbum(self, albumId):
        if albumId not in self.albumsCache:
            if self.offlineMode:
                return None
            album = self.user.get_album(albumId)
            self.albumsCache[albumId] = album
        return self.albumsCache[albumId]

    def getMediaDrawer(self, convId=""):
        if self.offlineMode:
            return None
        return self.user.get_media_drawer(convId)

    def getLocation(self):
        return self.location

    def setLocation(self, location):
        self.location = location

    def getLocationList(self):
        return self.locationList

    def setLocationList(self, locationList):
        self.locationList = locationList

    def setCurrentLocation(self, name):
        assert name in self.locationList
        self.currentLocation = name
        self.setLocation(self.locationList[name])

    def getCurrentExploreLocation(self):
        return self.currentExploreLocation

    def setExploreLocation(self, name):
        assert name in self.locationList
        self.currentExploreLocation = name

    def getSearchFilter(self):
        return self.searchFilter

    def setSearchFilter(self, filter):
        self.searchFilter = filter

    def getEffectiveSearchFilter(self):
        filter = {}
        f = self.getSearchFilter()
        isEnabled = lambda n: f.get(n + "FilterEnabled", False)
        if isEnabled("age"):
            filter["ageMin"] = f["ageMin"]
            filter["ageMax"] = f["ageMax"]
        if isEnabled("heightCm"):
            filter["heightCmMin"] = f["heightCmMin"]
            filter["heightCmMax"] = f["heightCmMax"]
        if isEnabled("weightGrams"):
            filter["weightGramsMin"] = f["weightGramsMin"]
            filter["weightGramsMax"] = f["weightGramsMax"]
        for key in ["sexualPositions", "tribes", "bodyTypes", "relationshipStatuses", "nsfwPics", "lookingFor", "meetAt", "sexualHealth"]:
            values = f.get(key, [])
            if f.get(key + "FilterEnabled", False) and values:
                filter[key] = quote_plus(",".join([str(v) for v in values]))
        for key in ["favorites", "onlineOnly", "notRecentlyChatted", "photoOnly", "faceOnly", "hasAlbum", "rightNow"]:
            if f.get(key, False):
                filter[key] = "true"
        filter = {k: str(v) for k, v in filter.items()}
        return filter

    def _sendGenericChat(self, profileId, chatType, chatBody, replyToId: str | None):
        if self.offlineMode:
            return
        refId = str(uuid4())
        wsMsg = {
          "payload": {
            "type": chatType,
            "target": {
              "type": "Direct",
              "targetId": profileId
            },
            "body": chatBody,
            "ref": refId
          },
          "ref": refId,
          "token": self.user.sessionId,
          "type": "chat.v1.message.send"
        }
        if replyToId:
            wsMsg["payload"]["replyToMessageId"] = replyToId
        jsonMsg = json.dumps(wsMsg)
        self.websocket.send(jsonMsg)

    def sendTap(self, profileId, tap_type):
        self.user.tap(profileId, tap_type)
        self.clearProfileDetails(profileId)
        self.signals.tapSent.emit()

    def sendTextChat(self, profileId, msg, replyToId=None):
        chatType = "Text"
        chatBody = {"text": msg}
        self._sendGenericChat(profileId, chatType, chatBody, replyToId)

    def sendLocationChat(self, profileId, location=None, replyToId=None):
        chatType = "Location"
        if not location:
            location = self.getLocation()
            if not location:
                return
        chatBody = {"lat": location[0], "lon": location[1]}
        self._sendGenericChat(profileId, chatType, chatBody, replyToId)

    def sendImageChat(self, profileId, imageId, replyToId=None):
        chatType = "Image"
        chatBody = {"mediaId": imageId}
        self._sendGenericChat(profileId, chatType, chatBody, replyToId)

    def sendMessageReaction(self, convId, msgId):
        self.user.react_to_message(convId, msgId)

    def markMessageRead(self, convId, msgId):
        if msgId in self.messageReadCache:
            return
        self.user.message_read(convId, msgId)
        self.signals.messageRead.emit(convId, msgId)
        self.messageReadCache.add(msgId)

    def uploadMediaFile(self, fileName, takenOnGrindr=False):
        if self.offlineMode:
            return
        mimeType = QtCore.QMimeDatabase().mimeTypeForFile(fileName)
        contentType = mimeType.name()
        if not contentType:
            print("Unknown media format")
            return
        print("In uploadMediaFile, contentType=", contentType)
        response = self.user.upload_media(fileName, contentType, takenOnGrindr, debug=True)
        mediaId = response["mediaId"]
        self.user.put_in_drawer(mediaId, debug=True)

    def deleteConversation(self, profileId):
        convId = self.getConversationId(profileId)
        self.user.delete_conversation(convId)

    def getBlockedUsers(self):
        return self.user.get_blocked_users()

    def blockUser(self, profileId):
        self.user.block_user(profileId)

    def unblockUser(self, profileId):
        self.user.unblock_user(profileId)

    def unblockAllUsers(self):
        self.user.unblock_all_users()

    def getHiddenUsers(self):
        return self.user.get_hidden_users()

    def hideUser(self, profileId):
        self.user.hide_user(profileId)

    def unhideUser(self, profileId):
        self.user.unhide_user(profileId)

    def unhideAllUsers(self):
        self.user.unhide_all_users()