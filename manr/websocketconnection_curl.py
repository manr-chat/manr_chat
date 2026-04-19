#!/usr/bin/env python3
import sys
import asyncio
import traceback
from curl_cffi.requests import AsyncSession
from curl_cffi.const import CurlWsFlag
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from .grindr_access.generic_request import default_headers

wssUrl = "wss://grindr.mobi/v1/ws"

class ReceiverThreadSignals(QObject):
    received = Signal(str)
    error = Signal(tuple)
    closed = Signal()

class ReceiverWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = ReceiverThreadSignals()
        self._url = None
        self._headers = None
        self._ws = None
        self._loop = None

    def setConnection(self, url, headers):
        self._url = url
        self._headers = headers

    @Slot()
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_and_receive())
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self._loop.close()
            self._loop = None

    async def _connect_and_receive(self):
        try:
            async with AsyncSession(impersonate="chrome146") as session:
                ws = await session.ws_connect(self._url, headers=self._headers)
                self._ws = ws
                try:
                    async for msg in ws:
                        self.signals.received.emit(msg.decode() if isinstance(msg, bytes) else msg)
                except Exception:
                    traceback.print_exc()
                    exctype, value = sys.exc_info()[:2]
                    self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self._ws = None
            try:
                self.signals.closed.emit()
            except RuntimeError:
                pass

    def send(self, msg: str):
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.send(msg, CurlWsFlag.TEXT), self._loop)

    def stop(self):
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)


class WebSocketConnection():
    def __init__(self):
        self.user = None
        self._worker = ReceiverWorker()
        self.receiverRunning = False

    def connect(self, user):
        self.user = user
        self.disconnect()
        self._initHeaders(self.user.deviceInfo, self.user.sessionId)
        headers = self.additional_headers

        self._worker.setConnection(wssUrl, headers)
        self.receiverRunning = True
        QThreadPool.globalInstance().start(self._worker)

    def disconnect(self):
        self._worker.stop()
        self.receiverRunning = False

    def runReceiverThread(self):
        assert self.isConnected()
        pass

    def send(self, msg: str):
        assert self.isConnected(), "Not connected"
        self._worker.send(msg)

    def _initHeaders(self, deviceInfo, authToken):
        headers = default_headers(deviceInfo, authToken)
        self.additional_headers = {p[0]: p[1] for e in headers if (p := e.split(": "))}

    @property
    def signals(self) -> ReceiverThreadSignals:
        return self._worker.signals

    def isConnected(self) -> bool:
        return self._worker._ws is not None