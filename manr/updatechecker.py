import threading
from curl_cffi import requests
from packaging.version import Version
from PySide6.QtCore import QObject, Signal
from .appinfo import manr_user_agent, version_str

class UpdateChecker(QObject):
    update_available = Signal(str, str)  # version, url

    def check(self):
        thread = threading.Thread(target=self._check, daemon=True)
        thread.start()

    def _check(self):
        try:
            response = requests.get(
                "https://api.github.com/repos/manr-chat/manr_chat/releases/latest",
                headers={"User-Agent": manr_user_agent()},
                timeout=5
            )
            data = response.json()
            latest = data["tag_name"].lstrip("v")
            url = data["html_url"]

            if Version(latest) > Version(version_str()):
                self.update_available.emit(latest, url)
        except Exception:
            pass  # silently ignore network errors
