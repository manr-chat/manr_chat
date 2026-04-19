#!/usr/bin/env python3

import sys
import traceback
from websockets.sync import client
from websockets.exceptions import WebSocketException

from PySide6.QtCore import (QObject, QRunnable, QThreadPool, Signal, Slot)
from .grindr_access.generic_request import default_headers

wssUrl = "wss://grindr.mobi/v1/ws"

class ReceiverThreadSignals(QObject):
    received = Signal(str)
    error = Signal(tuple)
    closed = Signal()

class ReceiverThread(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = ReceiverThreadSignals()
        self.connection = None

    def setConnection(self, connection):
        self.connection = connection

    @Slot()
    def run(self):
        try:
            for msg in self.connection:
                self.signals.received.emit(msg)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        #else:
        #    self.signals.result.emit(result)  # Return the result of the processing
        finally:
            # HACK / TODO: figure out the lifetime issue causing errors
            try:
                self.signals.closed.emit()
            except RuntimeError:
                pass

class WebSocketConnection():
    receiver: ReceiverThread
    connection: client.ClientConnection | None

    def __init__(self):
        self.user = None
        self.connection = None
        self.receiver = ReceiverThread()
        self.receiverRunning = False

    def connect(self, user):
        self.user = user
        self.disconnect()
        self._initHeaders(self.user.deviceInfo, self.user.sessionId)
        self.connection = client.connect(wssUrl, user_agent_header=self.user_agent,
                                         additional_headers=self.additional_headers)
        self.receiver.setConnection(self.connection)

    def disconnect(self):
        if self.connection:
            self.connection.close()
        self.connection = None
        self.receiverRunning = False

    def runReceiverThread(self):
        assert self.receiver and not self.receiverRunning
        self.receiverRunning = True
        QThreadPool.globalInstance().start(self.receiver)

    def send(self, msg):
        assert self.connection
        self.connection.send(msg)

    def _initHeaders(self, deviceInfo, authToken):
        headers = default_headers(deviceInfo, authToken)
        self.additional_headers = {p[0]: p[1] for e in headers if (p := e.split(": "))}
        self.user_agent = self.additional_headers.pop("user-agent")

    @property
    def signals(self) -> ReceiverThreadSignals:
        return self.receiver.signals

    def isConnected(self) -> bool:
        return bool(self.connection)
