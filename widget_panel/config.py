"""配置与路径管理。"""
import json
import os
from pathlib import Path

APP_NAME = "WidgetPanel"

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / APP_NAME.lower()
CACHE_DIR = HOME / ".cache" / APP_NAME.lower()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "settings.json"
CACHE_FILE = CACHE_DIR / "last_state.json"
COVER_CACHE_DIR = CACHE_DIR / "covers"
COVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "auto_locate": True,
    "city_override": "",
    "latitude": None,
    "longitude": None,
    "city_name": "",
    "weather_refresh_seconds": 600,
    "news_count": 6,
    "edge_trigger": True,
    "panel_width": 460,
    "auto_start": True,
    "news_categories": ["world", "technology", "entertainment", "sports"],
    "theme_mode": "dark",
    "opacity": 92,
}


def load_settings():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def save_settings(settings):
    CONFIG_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
