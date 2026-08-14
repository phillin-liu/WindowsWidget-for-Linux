"""天气服务：基于 Open-Meteo 的实时天气 + ip-api 自动定位城市。

Open-Meteo 与 ip-api 的免费端点均无需 API Key，可直接调用。
"""
import threading

import requests

GEO_URL = "http://ip-api.com/json/?lang=zh-CN&fields=status,country,city,lat,lon"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# WMO 天气代码 -> (中文描述, 图标 key)
WMO_CODES = {
    0: ("晴", "sun"),
    1: ("晴间多云", "sun_cloud"),
    2: ("多云", "cloud"),
    3: ("阴", "cloud"),
    45: ("雾", "fog"),
    48: ("雾凇", "fog"),
    51: ("毛毛雨", "rain"),
    53: ("毛毛雨", "rain"),
    55: ("毛毛雨", "rain"),
    56: ("冻毛毛雨", "rain"),
    57: ("冻毛毛雨", "rain"),
    61: ("小雨", "rain"),
    63: ("中雨", "rain"),
    65: ("大雨", "rain"),
    66: ("冻雨", "rain"),
    67: ("冻雨", "rain"),
    71: ("小雪", "snow"),
    73: ("中雪", "snow"),
    75: ("大雪", "snow"),
    77: ("米雪", "snow"),
    80: ("阵雨", "rain"),
    81: ("阵雨", "rain"),
    82: ("强阵雨", "rain"),
    85: ("阵雪", "snow"),
    86: ("强阵雪", "snow"),
    95: ("雷阵雨", "storm"),
    96: ("雷阵雨伴冰雹", "storm"),
    99: ("雷阵雨伴冰雹", "storm"),
}


def describe_code(code):
    return WMO_CODES.get(code, ("未知", "cloud"))


def locate_by_ip():
    """通过 ip-api 自动定位，返回 dict(city, lat, lon) 或 None。"""
    try:
        r = requests.get(GEO_URL, timeout=6)
        r.raise_for_status()
        d = r.json()
        if d.get("status") == "success":
            return {
                "city": d.get("city") or "未知",
                "lat": float(d["lat"]),
                "lon": float(d["lon"]),
            }
    except Exception:
        return None
    return None


def fetch_weather(lat, lon):
    """获取实时天气与未来 3 天预报，返回结构化 dict。"""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "is_day,weather_code,wind_speed_10m"
        ),
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": "auto",
        "forecast_days": 3,
    }
    r = requests.get(WEATHER_URL, params=params, timeout=8)
    r.raise_for_status()
    data = r.json()
    cur = data.get("current", {})
    daily = data.get("daily", {})
    code = cur.get("weather_code", 0)
    desc, icon = describe_code(code)
    forecast = []
    times = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])
    for i in range(min(len(times), 3)):
        d, _ = describe_code(codes[i] if i < len(codes) else 0)
        forecast.append(
            {
                "date": times[i],
                "max": round(tmax[i]) if i < len(tmax) else None,
                "min": round(tmin[i]) if i < len(tmin) else None,
                "desc": d,
            }
        )
    return {
        "temp": round(cur.get("temperature_2m", 0)),
        "feels": round(cur.get("apparent_temperature", 0)),
        "humidity": cur.get("relative_humidity_2m", 0),
        "wind": round(cur.get("wind_speed_10m", 0)),
        "is_day": cur.get("is_day", 1) == 1,
        "code": code,
        "desc": desc,
        "icon": icon,
        "forecast": forecast,
        "updated": cur.get("time", ""),
    }


def get_weather_async(lat, lon, callback):
    """在线程中拉取天气，完成后回调 callback(result_or_None, error)。"""

    def worker():
        try:
            res = fetch_weather(lat, lon)
            callback(res, None)
        except Exception as e:
            callback(None, str(e))

    threading.Thread(target=worker, daemon=True).start()


def locate_async(callback):
    def worker():
        callback(locate_by_ip())

    threading.Thread(target=worker, daemon=True).start()
