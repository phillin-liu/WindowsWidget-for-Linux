"""缓存服务：每 5 分钟保存一次当前广告与天气状态，下次启动可立即展示。"""
import json
import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal

from .config import CACHE_FILE


class CacheService(QObject):
    """后台定时保存最新状态。"""
    saved = pyqtSignal()

    def __init__(self, interval_seconds=300):
        super().__init__()
        self._interval = interval_seconds
        self._lock = threading.Lock()
        self._state = {
            "news": [],
            "weather": None,
            "location": None,
            "news_timestamp": 0,
        }
        self._timer = None
        self._running = False

    def update(self, news=None, weather=None, location=None):
        with self._lock:
            if news is not None:
                self._state["news"] = news
                self._state["news_timestamp"] = time.time()
            if weather is not None:
                self._state["weather"] = weather
            if location is not None:
                self._state["location"] = location
        self._save_now()

    def get(self):
        with self._lock:
            return json.loads(json.dumps(self._state))

    def _save_now(self):
        try:
            with self._lock:
                data = json.dumps(self._state, ensure_ascii=False, indent=2)
            CACHE_FILE.write_text(data, encoding="utf-8")
        except Exception:
            pass

    def start(self):
        if self._running:
            return
        self._running = True

        def loop():
            while self._running:
                self._save_now()
                self.saved.emit()
                threading.Event().wait(self._interval)

        threading.Thread(target=loop, daemon=True).start()

    def stop(self):
        self._running = False
        self._save_now()


def load_cached_state():
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            data.setdefault("news", [])
            data.setdefault("weather", None)
            data.setdefault("location", None)
            data.setdefault("news_timestamp", 0)
            return data
    except Exception:
        pass
    return {"news": [], "weather": None, "location": None, "news_timestamp": 0}
