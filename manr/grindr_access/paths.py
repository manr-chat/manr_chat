#SESSIONS = "/v3/sessions"
#SESSIONS = "/v4/sessions"
SESSIONS = "/v5/sessions"
SESSIONS = "/v8/sessions"  # with geohash
#GET_USERS = "/v1/cascade"
GET_USERS = "/v3/cascade"
#GET_PROFILE = "/v4/profiles/"
#GET_PROFILE = "/v6/profiles/"
GET_PROFILE = "/v7/profiles/"
GET_PROFILES = "/v3/profiles"
TAPS_RECEIVED = "/v2/taps/received"
TAPS_SENT = "/v1/interactions/taps/sent" # GET
TAP = "/v2/taps/add"
STATUS = "/v4/profiles/status"
ALBUM = "/v2/albums/"
ALBUM_SHARES = "/v2/albums/shares"
FAVORITES = "/v3/me/favorites/" # POST or DELETE to set/remove favorite user
FAVORITES_LIST = "/v6/favorites" # GET for list of favorites
FAVORITES_NOTES = "/v1/favorites/notes" # GET
#VIEWS = "/v6/views/list" # GET
VIEWS = "/v7/views/list" # GET
VIEWS_EYEBALL = "/v6/views/eyeball" # GET
#VIEWED_PROFILE = "/v4/views" # POST with {"viewedProfileIds": ["id"]} ##???
VIEWED_PROFILE = "/v5/views/{profileId}" #POST

CONVERSATION  = "/v1/inbox/conversation"  # POST with ["id1:id2"], ids are mine and theirs, id1<id2, no curly braces
CONVERSATIONS = "/v4/chat/conversation/{convId}/message" # GET, optional parameter "?pageKey={last_msg_guid}""
DEL_CONVERSATION = "/v4/chat/conversation/{convId}" # DELETE
REACT_MSG = "/v4/chat/message/reaction" # POST with {"conversationId": convId, "messageId": msgId, "reactionType": 1 }
RED_DOT = "/v1/albums/red-dot"  # GET
MY_LOCATION = "/v3/me/location"  # PUT with { "geohash": "gedz62bttu1d" }
# TODO: update INBOX to v3, adds another "data" indirection
INBOX = "/v1/inbox" # POST with { "unreadOnly": true } or {}
GENDERS = "/public/v2/genders" # GET, unauthorized
TAGS = "/v1/tags" # GET
PROFILE_TAG_TRANSLATIONS = "/v5/profile-tags/translations" # GET
BLOCKING = "/v3.1/me/blocks" # GET
BLOCK = "/v3/me/blocks/{userid}" # POST, DELETE
HIDDEN = "/v1/hides/" # GET
# Why is block / unblock symmetric but hide/unhide isn't?
# What moron designed this API?
HIDE = "/v1/me/hides/{userid}" # POST
UNHIDE = "/v1/hides/{userid}" # DELETE
CHAT_STATUS = "/v4/chatstatus/typing" # POST with {"conversationId": "{convId}","status": "Cleared"} or "status": "Typing"
MEDIA_DRAWER = "/v4/chat/media/drawer/{id}" # GET with convId, PUT or DELETE with media ID
EXPIRING_PICS_STATUS = "/v4/pics/expiring/status" # GET
EXPIRING_VIDEOS_STATUS = "/v4/videos/expiring/status" # GET
SHARED_IMAGES = "/v4/chat/media/shared/images/with-me/{convId}" # GET
MESSAGE_READ = "/v4/chat/conversation/{convId}/read/{msgId}" # POST
MEDIA_UPLOAD  = "/v5/chat/media/upload?takenOnGrindr={takenOnGrindr}" # POST with image data, content-type: image/jpeg
SPOTIFY_FAVORITES = "/v4/spotify/favorites/{profileId}" # GET
SET_MY_PROFILE = "/v3.1/me/profile" # PUT with profile data
GET_MY_PROFILE = "/v4/me/profile" # GET
PROFILE_IMAGES = "/v3.1/me/profile/images?selected=false" # GET
SET_PROFILE_IMAGES = "/v3/me/profile/images" # PUT with {"primaryImageHash": "id","secondaryImageHashes": ["id"]}

RIGHTNOW_FEED = "/v3/rightnow/feed?sort=DISTANCE" # GET

# No idea what this does, telemetry or something useful
ACK_NOTIFICATION = "/public/v1/notifications/ack" # POST with {"notificationId": "idstring", "source": "WEBSOCKET"}