#!/usr/bin/env python3
import sys
import asyncio
import traceback
from curl_cffi.requests import AsyncSession
from curl_cffi.const import CurlWsFlag
from PySide6.QtCore import QObject, QThread, Signal, Slot
from .grindr_access.generic_request import default_headers

wssUrl = "wss://grindr.mobi/v1/ws"


class ReceiverWorker(QObject):
    received = Signal(str)
    error = Signal(tuple)
    closed = Signal()

    def __init__(self, url, headers):
        super().__init__()
        self._url = url
        self._headers = headers
        self._ws = None
        self._loop = None

    @Slot()
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_and_receive())
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.error.emit((exctype, value, traceback.format_exc()))
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
                        self.received.emit(msg.decode() if isinstance(msg, bytes) else msg)
                except Exception:
                    traceback.print_exc()
                    exctype, value = sys.exc_info()[:2]
                    self.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self._ws = None
            try:
                self.closed.emit()
            except RuntimeError:
                pass

    def send(self, msg: str):
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.send(msg, CurlWsFlag.TEXT), self._loop)

    def stop(self):
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)


class WebSocketConnection(QObject):
    def __init__(self):
        super().__init__()
        self.user = None
        self._worker = None
        self._thread = None

    def connect(self, user):
        self.user = user
        self.disconnect()
        self._initHeaders(self.user.deviceInfo, self.user.sessionId)
        headers = self.additional_headers

        self._thread = QThread()
        self._worker = ReceiverWorker(wssUrl, headers)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.closed.connect(self._thread.quit)

        self._thread.start()

    def disconnect(self):
        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
        self._worker = None
        self._thread = None

    def runReceiverThread(self):
        assert self.isConnected()
        pass

    def send(self, msg: str):
        assert self._worker is not None, "Not connected"
        self._worker.send(msg)

    def _initHeaders(self, deviceInfo, authToken):
        headers = default_headers(deviceInfo, authToken)
        self.additional_headers = {p[0]: p[1] for e in headers if (p := e.split(": "))}

    @property
    def signals(self) -> ReceiverWorker | None:
        return self._worker

    def isConnected(self) -> bool:
        return (
            self._thread is not None
            and self._thread.isRunning()
            and self._worker is not None
            and self._worker._ws is not None
        )