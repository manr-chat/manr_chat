#!/usr/bin/env python3

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6 import QtCore

notificationPlayer = None
audioOutput = None
def playNotificationSound():
    global notificationPlayer
    global audioOutput
    if not notificationPlayer:
        filename = "resources/dialog-warning.oga"
        notificationPlayer = QMediaPlayer()
        audioOutput = QAudioOutput()
        audioOutput.setVolume(100)
        notificationPlayer.setAudioOutput(audioOutput)
        notificationPlayer.setSource(QtCore.QUrl.fromLocalFile(filename))
    notificationPlayer.play()


if __name__ == "__main__":
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication([])
    playNotificationSound()
    QtCore.QTimer.singleShot(1000, lambda: app.quit())
    app.exec()