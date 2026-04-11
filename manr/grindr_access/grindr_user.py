from .generic_request import generic_post, generic_get, generic_put, generic_delete, post_file
from .paths import (SESSIONS, TAP, GET_USERS, TAPS_RECEIVED, TAPS_SENT, GET_PROFILE,
                    GET_PROFILES, STATUS, ALBUM, ALBUM_SHARES, FAVORITES, FAVORITES_LIST,
                    VIEWS, INBOX, CONVERSATIONS, DEL_CONVERSATION, REACT_MSG, MESSAGE_READ,
                    MEDIA_DRAWER, MEDIA_UPLOAD, BLOCKING, BLOCK, HIDDEN, HIDE, UNHIDE, RIGHTNOW_FEED)
from .utils import to_geohash

class GrindrFlags:
    tap_type_hi = "0"
    tap_type_hot = "1"
    tap_type_looking = "2"

class GrindrUserBase:
    sessionId: str | None
    profileId: str | None
    authToken: str | None
    email: str | None

    def login(self, email, password, debug=False): ...
    def sessions(self, email=None, authToken=None, debug=False): ...

class GrindrUserOffline(GrindrUserBase):
    def __init__(self, email, profileId):
        self.sessionId = "42"
        self.profileId = profileId
        self.authToken = None
        self.xmppToken = ""
        self.email = email

    def login(self, email, password, debug=False):
        self.email = email

    def sessions(self, email=None, authToken=None, debug=False):
        self.email = email
        return {}

    def getProfiles(self, **kwargs): ...
    def getExploreProfiles(self, **kwargs): ...

class GrindrUser(GrindrUserBase):
    def __init__(self, email, deviceInfo):
        self.sessionId = None
        self.profileId = ""
        self.authToken = None
        self.xmppToken = ""
        self.email = email
        self.deviceInfo = deviceInfo

    def login(self, email, password, debug=False):
        print("I GrindrUser.login:", email, password)
        response = generic_post(
            SESSIONS, {"email": email, "password": password, "token": ""}, self.deviceInfo, debug=debug
        )
        print(response)
        if "code" in response:
            code = response["code"]

            if code == 30:
                print("You need to verify your account via phone number!")
        self.sessionId = response["sessionId"]
        self.profileId = response["profileId"]
        self.authToken = response["authToken"]
        self.xmppToken = response["xmppToken"]
        self.email = email

    def getProfiles(self, lat, lon, filter={}, page=1, debug=False):
        params = {
            "nearbyGeoHash": to_geohash(lat, lon),
            "onlineOnly": "false",
            #"onlineOnly": "true",
            "photoOnly": "false",
            "faceOnly": "false",
            "notRecentlyChatted": "false",
            "fresh": "false",
            "pageNumber": f"{page}",
            "rightNow": "false",
            #"ageMin": "18",
            #"ageMax": "27"
        }
        params.update(filter)

        response = generic_get(GET_USERS, params, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def getExploreProfiles(self, lat, lon, filter={}, page=1, debug=False):
        params = {
            "exploreGeoHash": to_geohash(lat, lon),
            "pageNumber": f"{page}"
        }
        params.update(filter)
        response = generic_get(GET_USERS, params, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_right_now(self, debug=False):
        response = generic_get(RIGHTNOW_FEED, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_taps(self, debug=False):
        response = generic_get(TAPS_RECEIVED, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_sent_taps(self, debug=False):
        response = generic_get(TAPS_SENT, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    # type is a number from 1 - ?
    def tap(self, profileId, tapType, debug=False):
        response = generic_post(
            TAP, {"recipientId": profileId, "tapType": tapType}, self.deviceInfo, auth_token=self.sessionId, debug=debug
        )
        return response

    def get_profile(self, profileId, debug=False):
        response = generic_get(GET_PROFILE + profileId, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    # profileIdList MUST be an array of profile ids
    def get_profile_statuses(self, profileIdList, debug=False):
        response = generic_post(
            STATUS, {"profileIdList": profileIdList}, self.deviceInfo, auth_token=self.sessionId, debug=debug
        )
        return response

    def get_profiles(self, profileIdList, debug=False):
        response = generic_post(GET_PROFILES, {"targetProfileIds": profileIdList}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_album_shares(self, profileId, debug=False):
        response = generic_post(
            ALBUM_SHARES, {"profileId": profileId}, self.deviceInfo, auth_token=self.sessionId, debug=debug
        )
        return response

    def get_albums(self, debug=False):
        response = generic_get(
            ALBUM_SHARES, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug
        )
        return response

    def get_album(self, albumId, debug=False):
        response = generic_get(
            ALBUM+str(albumId), {}, self.deviceInfo, auth_token=self.sessionId, debug=debug
        )
        return response

    def set_favorite(self, profileId, debug=False):
        response = generic_post(FAVORITES + profileId, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def remove_favorite(self, profileId, debug=False):
        response = generic_delete(FAVORITES + profileId, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_favorites(self, debug=False):
        response = generic_get(FAVORITES_LIST, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_views(self, debug=False):
        response = generic_get(VIEWS, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_chats(self, page=1, unreadOnly=False, debug=False):
        data = { "unreadOnly": True } if unreadOnly else {}
        response = generic_post(INBOX + f"?page={page}", request_body=data, dev_info=self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_conversation(self, convId, pageKey = None, debug=False):
        url = CONVERSATIONS.format(convId=convId)
        if pageKey:
            url += f"?pageKey={pageKey}"
        response = generic_get(url, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def delete_conversation(self, convId, debug=True):
        response = generic_delete(DEL_CONVERSATION.format(convId=convId), self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_message(self, convId, msgId, debug=False):
        response = generic_get(CONVERSATIONS.format(convId=convId) + "/" + msgId, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def react_to_message(self, convId, msgId, reactionType=1, debug=False):
        data = {"conversationId": convId, "messageId": msgId, "reactionType": reactionType }
        response = generic_post(REACT_MSG, request_body=data, dev_info=self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def message_read(self, convId, msgId, debug=False):
        response = generic_post(MESSAGE_READ.format(convId=convId, msgId=msgId), {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_media_drawer(self, convId, debug=False):
        response = generic_get(MEDIA_DRAWER.format(id=convId), {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def put_in_drawer(self, mediaId, debug=False):
        response = generic_put(MEDIA_DRAWER.format(id=mediaId), {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def upload_media(self, filename, content_type, takenOnGrindr, debug=False):
        ton = "true" if takenOnGrindr else "false"
        response = post_file(MEDIA_UPLOAD.format(takenOnGrindr=ton), filename, content_type,
                             dev_info=self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_blocked_users(self, debug=False):
        response = generic_get(BLOCKING, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response
    
    def block_user(self, profileId, debug=False):
        response = generic_post(BLOCK.format(userid=profileId), {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response
    
    def unblock_user(self, profileId, debug=False):
        response = generic_delete(BLOCK.format(userid=profileId), self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def unblock_all_users(self, debug=False):
        response = generic_delete(BLOCK.format(userid=""), self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    def get_hidden_users(self, debug=False):
        response = generic_get(HIDDEN, {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response
    
    def hide_user(self, profileId, debug=False):
        response = generic_post(HIDE.format(userid=profileId), {}, self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response
    
    def unhide_user(self, profileId, debug=False):
        response = generic_delete(UNHIDE.format(userid=profileId), self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response
    
    def unhide_all_users(self, debug=False):
        response = generic_delete(UNHIDE.format(userid=""), self.deviceInfo, auth_token=self.sessionId, debug=debug)
        return response

    # returns session data (might renew it)
    def sessions(self, email=None, authToken=None, debug=False):
        print("I: GrindrUser.sessions:", email, authToken)
        if not email:
            email = self.email
        if not authToken:
            authToken = self.authToken
        response = generic_post(
            SESSIONS,
            {"email": email, "token": "", "authToken": authToken},
            self.deviceInfo, auth_token=self.sessionId, debug=debug
        )

        if "sessionId" not in response:
            print("E: could not log in:", response)
        else:
            print("I: Logged in: ", response)
        self.sessionId = response["sessionId"]
        self.profileId = response["profileId"]
        self.authToken = response["authToken"]
        self.xmppToken = response["xmppToken"]
        self.email = email

        return response
