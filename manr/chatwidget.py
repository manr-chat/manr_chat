#!/usr/bin/env python3

import os
import math
import json
from dataclasses import dataclass
from enum import Enum
from html import escape
from pathlib import Path
from typing import Any, cast, assert_type

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QObject, QSize, QRectF, QPointF, QTimer, QUrl
from PySide6.QtGui import (
    QAction, QPainter, QColor, QIcon, QTextDocument, QPolygonF, QPixmap,
    QFontMetrics, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QListView, QStyledItemDelegate, QMenu,
    QDialog, QLabel, QScrollArea
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWebEngineWidgets import QWebEngineView


from .datamodel import DataModel
from .image_cache import *
from .imageselectiondialog import showImageSelectionDialog
from .utils import formatTimeStamp

Sender = Enum("Sender", ["sent", "received"])
MsgType = Enum("MsgType", ["text", "image", "album", "location"])

ReactionType = Enum("ReactionType", ["single", "multi"])

# TODO: Change to alternative class design and use `match msg: case TextMessage():`
#
# @dataclass
# class TextMessage:
#     content: str
#     sender: Sender
#     timestamp: str
# 
# @dataclass
# class ImageMessage:
#     content: QPixmap
#     sender: Sender
#     timestamp: str
# 
# @dataclass
# class LocationMessage:
#     content: str  # or a lat/lon dataclass
#     sender: Sender
#     timestamp: str
# 
# ChatMessage = TextMessage | ImageMessage | LocationMessage

@dataclass
class ChatMessage:
    msgType: MsgType
    content: str | tuple[QPixmap, str]
    sender: Sender
    timestamp: str
    reaction: ReactionType | None
    replyMsg: ChatMessage | None
    messageId: str | None

class ChatModel(QAbstractListModel):
    MsgRole = Qt.ItemDataRole.UserRole + 1
    SenderRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3
    TypeRole = Qt.ItemDataRole.UserRole + 4
    ContentRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, messages: list[ChatMessage] | None = None):
        super().__init__()
        self._messages = messages or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._messages)

    def data(self, index, role):
        if not index.isValid():
            return None
        message = self._messages[index.row()]
        if role == ChatModel.MsgRole:
            return message
        if role == ChatModel.SenderRole:
            return message.sender
        if role == ChatModel.TimestampRole:
            return message.timestamp
        if role == ChatModel.TypeRole:
            return message.msgType
        if role == ChatModel.ContentRole:
            return message.content
        return None

    def add_message(self, message: ChatMessage):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._messages.append(message)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._messages = []
        self.endResetModel()


class ChatDelegate(QStyledItemDelegate):
    WIDTH_RATIO = 0.7
    PADDING = 8
    MARGIN = 6
    MARGIN_SMALL = 1
    RADIUS = 6
    TAIL_SIZE = 10
    TIMESTAMP_HEIGHT = 14
    TIMESTAMP_PADDING = 4
    REPLY_RADIUS = 4
    REPLY_TEXT_HEIGHT = 14
    REPLY_IMG_HEIGHT = 32
    REPLY_PADDING = PADDING - REPLY_RADIUS
    #sendColor = QColor("#DCF8C6")
    sendColor = QColor("#f0cf64")
    receiveColor = QColor("#91caf3")

    def _compute_reply_height(self, reply):
        if reply:
            if isinstance(reply.content, str):
                return self.REPLY_TEXT_HEIGHT
            else:
                return self.REPLY_IMG_HEIGHT + 2 * self.REPLY_RADIUS
        return 0

    def _compute_content_size(self, msg: ChatMessage, option, index):
        content_size = QSize(50, 50)
        max_bubble_width = option.widget.width() * self.WIDTH_RATIO
        doc = None
        if msg.msgType == MsgType.text or msg.msgType == MsgType.location:
            # timestamp width
            fm = QFontMetrics(option.font)
            timestamp_width = fm.horizontalAdvance(msg.timestamp)
            #timestamp_height = fm.height()

            doc = QTextDocument()
            if msg.msgType == MsgType.text:
                text = cast(str, msg.content)
            else:
                text = f"📍🗺️ <b>Location:</b><br>Lat {msg.content["lat"]}, Lon {msg.content["lon"]}"
            doc.setHtml(text)
            # First set the maximum width as a constraint
            doc.setTextWidth(max_bubble_width)
            # idealWidth() gives the width the content actually wants,
            # which respects the constraint set by setTextWidth()
            actual_width = max(int(math.ceil(doc.idealWidth())), timestamp_width)
            # Now re-set the actual width so the height computation is correct
            doc.setTextWidth(actual_width)
            content_size = doc.size().toSize()
        elif msg.msgType == MsgType.image or msg.msgType == MsgType.album:
            pixmap = cast(tuple[QPixmap, str], msg.content)[0]
            if pixmap and not pixmap.isNull():
                scale = min(1.0, max_bubble_width / pixmap.width())
                content_size = QSize(int(pixmap.width() * scale), int(pixmap.height() * scale))
        content_size.setHeight(content_size.height() + self._compute_reply_height(msg.replyMsg))
        return content_size, max_bubble_width, doc

    def paint(self, painter, option, index):
        painter.save()

        # Debug: fill each item with alternating background
        painter.fillRect(option.rect, QColor(230, 230, 250) if index.row() % 2 == 0 else QColor(245, 245, 255))

        msg = cast(ChatMessage, index.data(ChatModel.MsgRole))
        content_size, max_bubble_width, doc = self._compute_content_size(msg, option, index)

        # Grouping: previous/next same sender
        top_margin, _, _, next_same = self._compute_margins(index)
        bubble_width = content_size.width() + 2 * self.PADDING
        bubble_height = content_size.height() + 2 * self.PADDING + self.TIMESTAMP_HEIGHT

        rect = option.rect

        # Bubble rectangle
        if msg.sender == Sender.sent:
            bubble_rect = QRectF(
                rect.right() - bubble_width - self.MARGIN - self.TAIL_SIZE,
                rect.top() + top_margin,
                bubble_width,
                bubble_height
            )
            color = self.sendColor
        else:
            bubble_rect = QRectF(
                rect.left() + self.MARGIN + self.TAIL_SIZE,
                rect.top() + top_margin,
                bubble_width,
                bubble_height
            )
            color = self.receiveColor

        # Draw bubble
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bubble_rect, self.RADIUS, self.RADIUS)

        # Tail only on last message in group
        if not next_same:
            tail = QPolygonF()
            if msg.sender == Sender.sent:
                tail.append(QPointF(bubble_rect.right(), bubble_rect.bottom() - 20))
                tail.append(QPointF(bubble_rect.right() + self.TAIL_SIZE, bubble_rect.bottom() - 15))
                tail.append(QPointF(bubble_rect.right(), bubble_rect.bottom() - 10))
            else:
                tail.append(QPointF(bubble_rect.left(), bubble_rect.bottom() - 20))
                tail.append(QPointF(bubble_rect.left() - self.TAIL_SIZE, bubble_rect.bottom() - 15))
                tail.append(QPointF(bubble_rect.left(), bubble_rect.bottom() - 10))
            painter.drawPolygon(tail)

        # Draw content
        reply_offset = self._compute_reply_height(msg.replyMsg)
        if msg.msgType == MsgType.text or msg.msgType == MsgType.location:
            painter.translate(bubble_rect.left() + self.PADDING, bubble_rect.top() + self.PADDING + reply_offset)
            doc.drawContents(painter)
            painter.translate(-bubble_rect.left() - self.PADDING, -bubble_rect.top() - self.PADDING - reply_offset)
        elif msg.msgType == MsgType.image or msg.msgType == MsgType.album:
            pixmap = cast(tuple[QPixmap, str], msg.content)[0]
            if pixmap and not pixmap.isNull():
                scale = min(1.0, max_bubble_width / pixmap.width())
                img_width = int(pixmap.width() * scale)
                img_height = int(pixmap.height() * scale)
                target_rect = QRectF(
                    bubble_rect.left() + self.PADDING,
                    bubble_rect.top() + self.PADDING + reply_offset,
                    img_width,
                    img_height
                )
                painter.drawPixmap(target_rect.toAlignedRect(), pixmap)

        # Draw timestamp
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.darkGray)
        timestamp_rect = QRectF(
            bubble_rect.left() + self.PADDING,
            bubble_rect.bottom() - self.TIMESTAMP_HEIGHT - self.TIMESTAMP_PADDING,
            bubble_rect.width() - 2*self.PADDING,
            self.TIMESTAMP_HEIGHT
        )
        align = Qt.AlignmentFlag.AlignVCenter
        if msg.sender == Sender.sent:
            align |= Qt.AlignmentFlag.AlignRight
        painter.drawText(timestamp_rect, align, msg.timestamp + ("  🔥" if msg.reaction else ""))

        # draw response marker
        if msg.replyMsg:
            reply_bubble_rect = QRectF(
                bubble_rect.left() + self.REPLY_PADDING,
                bubble_rect.top() + self.PADDING / 2,
                bubble_rect.width() - 2*self.REPLY_PADDING,
                reply_offset
            )
            painter.save()
            painter.setBrush(color.lighter(120))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(reply_bubble_rect, self.REPLY_RADIUS, self.REPLY_RADIUS)
            stripe = QRectF(reply_bubble_rect)
            stripe.setWidth(self.REPLY_RADIUS)
            painter.setBrush(Qt.GlobalColor.white)
            painter.setClipRect(stripe)
            painter.drawRoundedRect(reply_bubble_rect, self.REPLY_RADIUS, self.REPLY_RADIUS)
            painter.restore()
            reply_rect = QRectF(
                bubble_rect.left() + self.REPLY_PADDING + self.REPLY_RADIUS,
                bubble_rect.top() + self.PADDING / 2,
                bubble_rect.width() - 2*self.REPLY_PADDING - 2*self.REPLY_RADIUS,
                self.REPLY_TEXT_HEIGHT
            )
            text = " ⤷ "
            if isinstance(msg.replyMsg.content, str):
                text += msg.replyMsg.content
            painter.drawText(reply_rect, Qt.AlignmentFlag.AlignVCenter, text)
            if msg.replyMsg.content and isinstance(msg.replyMsg.content, tuple):
                pm = msg.replyMsg.content[0]
                fm = QFontMetrics(option.font)
                marker_width = fm.horizontalAdvance(text)
                reply_rect = QRectF(
                    bubble_rect.left() + self.REPLY_PADDING + self.REPLY_RADIUS + marker_width,
                    bubble_rect.top() + self.PADDING / 2 + self.REPLY_RADIUS,
                    self.REPLY_IMG_HEIGHT,
                    self.REPLY_IMG_HEIGHT
                )
                painter.drawPixmap(reply_rect.toAlignedRect(), pm)

        # Draw reaction
        if msg.reaction:
            font = painter.font()
            font.setPointSize(16)
            painter.setFont(font)
            if msg.sender == Sender.sent:
                rpos = QPointF(bubble_rect.left() - self.PADDING, bubble_rect.top() + self.PADDING)
                rpos2 = QPointF(rpos.x() - self.PADDING, bubble_rect.top())
            else:
                rpos = QPointF(bubble_rect.right() - self.PADDING, bubble_rect.top() + self.PADDING)
                rpos2 = QPointF(rpos.x() + self.PADDING, bubble_rect.top())
            if msg.reaction == ReactionType.multi:
                painter.drawText(rpos2, "🔥")
            painter.drawText(rpos, "🔥")

        painter.restore()

    def _compute_margins(self, index):
        row = index.row()
        sender = index.data(ChatModel.SenderRole)
        prev_index = index.siblingAtRow(row - 1)
        next_index = index.siblingAtRow(row + 1)
        prev_same = prev_index.isValid() and prev_index.data(ChatModel.SenderRole) == sender
        next_same = next_index.isValid() and next_index.data(ChatModel.SenderRole) == sender

        top_margin = self.MARGIN_SMALL if prev_same else self.MARGIN
        bottom_margin = self.MARGIN_SMALL if next_same else self.MARGIN
        return top_margin, bottom_margin, prev_same, next_same

    def sizeHint(self, option, index):
        msg = index.data(ChatModel.MsgRole)
        content_size, _, _ = self._compute_content_size(msg, option, index)
        top_margin, bottom_margin, _, _ = self._compute_margins(index)
        height = content_size.height() + 2 * self.PADDING + top_margin + bottom_margin + self.TIMESTAMP_HEIGHT
        width = option.widget.width()
        return QSize(width, int(height))


class ImagePopup(QDialog):
    def __init__(self, pixmap, imgName, parent):
        super().__init__(parent)
        self.setWindowTitle("Chat image [ESC to close]")
        if imgName and imgName.endswith(".gif"):
            curDir = os.getcwd()
            file = str(Path(curDir) / imgName)
            file = QtCore.QUrl.fromLocalFile(file).toString()
            baseUrl = QUrl.fromLocalFile(curDir)
            webview = QWebEngineView()
            html = f'<img src="{file}"/><br><a href="{file}">{imgName}</a>'
            webview.setHtml(html, baseUrl=baseUrl)
            #webview.setUrl(QUrl.fromLocalFile(file))
            widget = webview
        else:
            scroll = QScrollArea()
            widget = QLabel()
            widget.setPixmap(pixmap)
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll.setWidget(widget)
            widget = scroll
        layout = QVBoxLayout()
        layout.addWidget(widget)
        self.setLayout(layout)
        screen = QApplication.primaryScreen().availableGeometry()
        max_width = min(pixmap.width() + 30, int(screen.width() * 0.8))
        max_height = min(pixmap.height() + 30, int(screen.height() * 0.8))
        self.resize(max_width, max_height)
        self.setModal(True)
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.close()
        super().mousePressEvent(event)


class ChatWidget(QObject):
    ui: Any

    def __init__(self, model: DataModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("chatwidget.ui")
        self.setupConnections()
        self.setupSpecialChatMenu()
        self.model = model
        self.chatProfileId = None
        self.refreshScheduled = False
        self.replyToMsg = None
        self.clearReply()
        #self.ui.replySenderColor.setProperty("sender", "sent")

        self.chatModel = ChatModel()
        self.ui.chatView.setItemDelegate(ChatDelegate())
        self.ui.chatView.setModel(self.chatModel)
        self.ui.chatView.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.ui.chatView.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.chatView.setSelectionMode(QListView.SelectionMode.NoSelection)
        # Resize triggers layout recalculation
        self.ui.chatView.resizeEvent = self._on_chat_view_resize
        self.ui.chatView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def setupConnections(self):
        self.ui.sendMessage.clicked.connect(self.on_sendMessage_clicked)
        self.ui.chatView.customContextMenuRequested.connect(self.on_context_menu)
        self.ui.chatView.clicked.connect(self.on_chatView_clicked)
        self.ui.closeReply.clicked.connect(self.on_closeReply_clicked)

    def _on_chat_view_resize(self, event):
        if event.size().width() != event.oldSize().width():
            scrollbar = self.ui.chatView.verticalScrollBar()
            was_at_bottom = scrollbar.value() == scrollbar.maximum()
            delegate = self.ui.chatView.itemDelegate()
            if hasattr(delegate, 'invalidate_cache'):
                delegate.invalidate_cache()
            self.ui.chatView.scheduleDelayedItemsLayout()
            # scheduleDelayedItemsLayout is async, so defer the scroll too
            if was_at_bottom:
                self.scheduleScrollToEnd()
        QListView.resizeEvent(self.ui.chatView, event)

    def on_context_menu(self, pos):
        index = self.ui.chatView.indexAt(pos)
        if not index.isValid():
            return
        msg = index.data(ChatModel.MsgRole)
        if not msg:
            return
        menu = QMenu()
        react_action = menu.addAction("React")
        reply_action = menu.addAction("Reply to")
        menu.addSeparator()
        copy_action = menu.addAction("Copy")
        action = menu.exec(self.ui.chatView.viewport().mapToGlobal(pos))
        if action == react_action:
            self.on_react_to_message(msg)
        elif action == reply_action:
            self.setReplyTo(msg)
        elif action == copy_action:
            self.on_copy_message(msg)

    def on_react_to_message(self, msg):
        convId = self.model.getConversationId(self.chatProfileId)
        msgId = msg.messageId
        if convId and msgId:
            self.model.sendMessageReaction(convId, msgId)
            self.scheduleRefresh()

    def on_reply_to_message(self, msg):
        self.setReplyTo(msg)

    def on_copy_message(self, msg):
        QApplication.clipboard().setText(str(msg.content))

    def on_chatView_clicked(self, index):
        if not index.isValid():
            return
        msg = index.data(ChatModel.MsgRole)
        if msg.msgType == MsgType.image:
            pixmap, fname = index.data(ChatModel.ContentRole)
            if pixmap and not pixmap.isNull():
                ImagePopup(pixmap, fname, self.ui)
        elif msg.msgType == MsgType.location:
            lat, lon = msg.content["lat"], msg.content["lon"]
            zoom = 17
            #gmaps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            osm_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom={zoom}"
            url = osm_url
            QDesktopServices.openUrl(url)
        # TODO: add handler for albums -> signal to show album view, location -> open map window

    def setupSpecialChatMenu(self):
        menu = QMenu(self.ui.sendSpecialChat)
        self.locationMenu = menu.addMenu(QIcon("resources/img/location.svg"), "Location")
        actImage = QAction("Image", menu)
        actGaymoji = QAction("Gaymoji", menu)
        actImage.setIcon(QIcon("resources/img/frame_with_picture.svg"))
        actGaymoji.setIcon(QIcon("resources/img/emoji.svg"))
        actImage.triggered.connect(lambda: self.on_sendImage_triggered())
        actGaymoji.triggered.connect(lambda: self.on_sendGaymoji_triggered())
        menu.addActions([actImage, actGaymoji])
        self.ui.sendSpecialChat.setMenu(menu)

    def updateLocationMenu(self):
        self.locationMenu.clear()
        for name in self.model.getLocationList().keys():
            actLoc = QAction(name, self.locationMenu)
            actLoc.triggered.connect(lambda checked=False, name=name: self.on_sendLocation_triggered(name))
            self.locationMenu.addAction(actLoc)
        self.locationMenu.addSeparator()

    def enableWidgets(self):
        enabled = bool(self.chatProfileId) and not self.model.offlineMode
        self.ui.chatLine.setEnabled(enabled)

    def _parseMessage(self, m):
        def imgMsg(*args, **kwargs):
            imgDesc = MediaDescription(*args, **kwargs)
            print("MediaDescription:", imgDesc)
            fname = get_or_download_image(imgDesc)
            print("fname:", fname)
            if fname:
                pm = QPixmap(fname)
                if not pm.isNull():
                    return (pm, fname), MsgType.image
            return 'Could not load image:<br><img src="">', MsgType.text
        def expiringImgMsg(m, convId, msgId):
            msg = self.model.getChatMessage(convId, msgId)
            if not msg or not "body" in msg:
                return f"Could not retrieve expiring image: " + escape(str(m["body"])), MsgType.text
            body = m["body"]
            if not body["url"]:
                return f"Expired image: " + escape(str(m["body"])), MsgType.text
            imgHash = base_hash_from_url(body["url"])
            return imgMsg(imgHash, MediaType.url, url=body["url"])
        # message body
        body = m["body"]
        mId = m["messageId"]
        msgType = MsgType.text
        replyTo = None
        match m["type"]:
            case "Text":
                msg = escape(body["text"]).replace("\n", "<br>")
            case "Image":
                msg, msgType = imgMsg(body["imageHash"], MediaType.url, url=body["url"])
            case "ExpiringImage":
                assert m["conversationId"] == self.model.getConversationId(self.chatProfileId)
                msg, msgType = expiringImgMsg(m, m["conversationId"], m["messageId"])
            case "Gaymoji":
                msg, msgType = imgMsg(body["imageHash"], MediaType.gaymoji)
            case "Giphy":
                msg, msgType = imgMsg(body["imageHash"], MediaType.url, url=body["urlPath"])
            case "Album":
                coverUrl = body["coverUrl"]
                imgHash = decorated_hash_from_url(coverUrl)
                msg, msgType = imgMsg(imgHash, MediaType.url, url=coverUrl)
                if msgType == MsgType.image:  # might be an error text, don't change then
                    msgType = MsgType.album
            case "Location":
                msg, msgType = body, MsgType.location
            case "ProfilePhotoReply":
                photoContentReply = escape(body["photoContentReply"]).replace("\n", "<br>")
                msg = f"<b>Profile photo reply:</b><br>{photoContentReply}"
                replyToMsg, replyToMsgType = imgMsg(body["imageHash"], MediaType.profile)
                replyTo = ChatMessage(replyToMsgType, replyToMsg, Sender.sent, "", None, None, None)
            case _:
                msg = f"Unknown chat type {m["type"]}: " + escape(str(m["body"]))
        # message meta data
        if self.model.user.profileId == str(m["senderId"]):
            sender = Sender.sent
        else:
            sender = Sender.received
        timeStamp = formatTimeStamp(m["timestamp"])
        reaction = None
        for r in m.get("reactions", []):
            if "profileId" in r and "reactionType" in r:
                rpid, rtype = r["profileId"], r["reactionType"]
                if (rpid == int(self.model.user.profileId) or rpid == int(self.chatProfileId)) and rtype == 1:
                    reaction = ReactionType.single if not reaction else ReactionType.multi
            if not reaction:
                print("Unknown reaction to message:", r)
        if m["replyToMessage"]:
            replyTo = self._parseMessage(m["replyToMessage"])
        return ChatMessage(msgType, msg, sender, timeStamp, reaction, replyTo, mId)


    def addChats(self, chat):
        sortedMessages = sorted(chat["messages"], key=lambda m: m["timestamp"])
        for m in sortedMessages:
            message = self._parseMessage(m)
            self.chatModel.add_message(message)
        # FIXME: only mark as read when chat widget is actually visible!
        self.markAsRead(chat, sortedMessages)

    def markAsRead(self, chat, messages):
        if not messages:
            return
        lastMsg = messages[-1]
        # FIXME: This doesn't work the way it should. There are both conversations
        # with no new messages that have lastRead == None and conversations with 
        # new messages that have lastRead == lastMsgTs.
        #
        #lastMsgTs = lastMsg.get("timestamp")
        #lastRead = chat.get("lastReadTimestamp", None)
        #if lastRead and lastMsgTs and lastRead >= lastMsgTs:
        #    return
        convId = lastMsg["conversationId"]
        msgId = lastMsg["messageId"]
        self.model.markMessageRead(convId=convId, msgId=msgId)

    def displayChat(self, profileId, update=False):
        self.chatModel.clear()
        if not profileId or int(profileId) <= 0 or profileId == self.model.user.profileId:
            self.chatProfileId = None
            self.enableWidgets()
            return
        self.chatProfileId = profileId
        self.enableWidgets()
        chat = self.model.getChat(profileId)
        print("Chat:\n", json.dumps(chat))
        if chat:
            self.addChats(chat)
        if not update:
            self.scheduleScrollToEnd()

    def scheduleScrollToEnd(self):
        QTimer.singleShot(0, lambda:  self.scrollToEnd())

    def scrollToEnd(self):
        vsb = self.ui.chatView.verticalScrollBar()
        max = vsb.maximum()
        vsb.setValue(max)

    def refreshChat(self):
        self.refreshScheduled = False
        vsb = self.ui.chatView.verticalScrollBar()
        old_pos_ratio = vsb.value() / (vsb.maximum() or 1)
        self.displayChat(self.chatProfileId, update=True)
        vsb.setValue(round(old_pos_ratio * vsb.maximum()))

    def scheduleRefresh(self):
        if not self.refreshScheduled:
            QTimer.singleShot(1000, self.refreshChat)
            self.refreshScheduled = True

    def clearReply(self):
        self.replyToMsg = None
        self.ui.replyLine.hide()
        self.ui.replyMsgLabel.clear()

    def setReplySenderColor(self, label, sender: Sender):
        if sender == Sender.sent:
            label.setStyleSheet("background-color: rgb(240, 207, 100);")
        else:
            label.setStyleSheet("background-color: rgb(145, 202, 243);")

    def setReplyTo(self, msg: ChatMessage):
        assert msg.messageId
        self.replyToMsg = msg.messageId
        self.ui.replyLine.show()
        self.setReplySenderColor(self.ui.replySenderColor, msg.sender)
        if msg.sender == Sender.sent:
            self.ui.replyToLabel.setText("Reply to yourself:")
        else:
            self.ui.replyToLabel.setText("Reply to:")
        if isinstance(msg.content, str):
            text = msg.content.replace("\n", " ")
            if len(text) > 53:
                text = text[:50] + "..."
            self.ui.replyMsgLabel.setText(text)
        else:
            pm = msg.content[0]
            pms = pm.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio)
            self.ui.replyMsgLabel.setPixmap(pms)

    def on_sendMessage_clicked(self):
        message = self.ui.msgText.text().strip()
        self.ui.msgText.clear()
        replyToId = self.replyToMsg
        self.clearReply()
        if message:
            self.model.sendTextChat(self.chatProfileId, message, replyToId)
            self.scheduleRefresh()

    def on_sendLocation_triggered(self, name):
        locations = self.model.getLocationList()
        if not name in locations:
            print(f"ERROR: named location '{name}' not found!")
            return
        self.model.sendLocationChat(self.chatProfileId, locations[name])
        self.scheduleRefresh()

    def on_sendImage_triggered(self):
        imageId = showImageSelectionDialog(self.model, self.chatProfileId, self.ui)
        if imageId:
            self.model.sendImageChat(self.chatProfileId, imageId)
            self.scheduleRefresh()

    def on_sendGaymoji_triggered(self):
        print("TODO: send gaymoji")
        self.scheduleRefresh()

    def on_closeReply_clicked(self):
        self.clearReply()
