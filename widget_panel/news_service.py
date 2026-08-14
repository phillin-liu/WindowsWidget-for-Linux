"""资讯/广告卡片服务。

数据源策略（保证“以能用为准”，全部真实抓取，无模拟）：
  1. 首选 MSN/Microsoft Start 官方信息流 (assets.msn.com)，返回 MSN 原版卡片
     封面 + 文章链接。该接口在数据中心 IP 上可能被 WAF 拦截 (503)，但在
     用户家宽/桌面环境通常可用。
  2. 若 MSN 不可用，回退到已验证可连通且自带封面的 RSS 源（IT之家 / Engadget /
     Ars Technica），同样提供封面 + 点击打开文章。

封面下载并缓存到本地，缺失时由自绘封面兜底。
"""
import hashlib
import html
import os
import re
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import requests

from .config import COVER_CACHE_DIR

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 已验证可连通且自带封面的回退 RSS（多源，保证池子足够大）
# 混合中英文源，覆盖科技/综合新闻，确保每次刷新都有新内容
FALLBACK_FEEDS = [
    ("IT之家", "https://www.ithome.com/rss/"),
    ("Engadget", "https://www.engadget.com/rss.xml"),
    ("ArsTechnica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("cnBeta", "https://rss.cnbeta.com/rss"),
    ("少数派", "https://sspai.com/feed"),
    ("TheVerge", "https://www.theverge.com/rss/index.xml"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("BBC", "http://feeds.bbci.co.uk/news/rss.xml"),
    ("Guardian", "https://www.theguardian.com/world/rss"),
    ("36氪", "https://36kr.com/feed"),
    ("GitHub", "https://github.blog/feed/"),
]

# 分类 -> 偏好源（额外加入基础池，提升相关性）
CATEGORY_FEEDS = {
    "technology": [
        ("IT之家", "https://www.ithome.com/rss/"),
        ("少数派", "https://sspai.com/feed"),
        ("TheVerge", "https://www.theverge.com/rss/index.xml"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("Wired", "https://www.wired.com/feed/rss"),
        ("ArsTechnica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("GitHub", "https://github.blog/feed/"),
    ],
    "world": [
        ("BBC", "http://feeds.bbci.co.uk/news/rss.xml"),
        ("Guardian", "https://www.theguardian.com/world/rss"),
        ("cnBeta", "https://rss.cnbeta.com/rss"),
    ],
    "sports": [
        ("BBC Sport", "http://feeds.bbci.co.uk/sport/rss.xml"),
    ],
    "entertainment": [
        ("BBC Entertainment", "http://feeds.bbci.co.uk/entertainment/rss.xml"),
    ],
    "business": [
        ("36氪", "https://36kr.com/feed"),
        ("Guardian Business", "https://www.theguardian.com/business/rss"),
    ],
    "science": [
        ("ArsTechnica Science", "https://feeds.arstechnica.com/arstechnica/science"),
        ("Guardian Science", "https://www.theguardian.com/science/rss"),
    ],
    "health": [
        ("Guardian Health", "https://www.theguardian.com/society/health/rss"),
    ],
}

# MSN 分类 -> channelId 映射
MSN_CHANNEL_MAP = {
    "world": "channel_news",
    "technology": "channel_news_tech",
    "entertainment": "channel_entertainment",
    "sports": "channel_sports",
    "business": "channel_finance",
    "science": "channel_news_sci",
    "health": "channel_health",
    "politics": "channel_news",
}

IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)


def _norm(text):
    return html.unescape(text or "").strip() if text else ""


# ---------------- MSN 信息流 ----------------
def _msn_headers():
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.msn.com",
        "Referer": "https://www.msn.com/",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "ActivityId": str(uuid.uuid4()),
        "ClientId": uuid.uuid4().hex.upper(),
        "SdkVersion": "MsfCom-18.333.1023.0",
    }


def _extract_cards(data):
    out = []

    def walk(node):
        if isinstance(node, dict):
            ct = node.get("cardType", "") or node.get("type", "")
            if ct and ct.lower() in (
                "contentcard", "newscard", "article", "content", "defaultcard"
            ):
                title = node.get("title") or node.get("headline")
                link = node.get("url") or node.get("destinationUrl")
                img = ""
                if isinstance(node.get("image"), dict):
                    img = (
                        node["image"].get("url")
                        or node["image"].get("thumbnail")
                        or node["image"].get("uri")
                        or ""
                    )
                elif isinstance(node.get("image"), str):
                    img = node["image"]
                if not img and isinstance(node.get("thumbnail"), dict):
                    img = node["thumbnail"].get("url", "")
                pub = node.get("publishedDateTime") or node.get("date", "")
                src = ""
                if isinstance(node.get("publisher"), dict):
                    src = node["publisher"].get("name", "")
                if not src and isinstance(node.get("attribution"), dict):
                    src = node["attribution"].get("source", "")
                if title and link:
                    out.append(
                        {
                            "title": _norm(title),
                            "link": _norm(link),
                            "summary": _norm(node.get("abstract") or node.get("summary")),
                            "image": _norm(img),
                            "source": _norm(src) or "MSN",
                            "published": _norm(pub),
                            "fetched_at": time.time(),
                        }
                    )
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    walk(data)
    return out


def fetch_msn_feed(categories, count):
    headers = _msn_headers()
    items = []
    seen = set()
    # 快速失败：最多 2 个分类，每个 3s 超时，避免 MSN 不可用时长时间阻塞
    for cat in categories[:2]:
        ch = MSN_CHANNEL_MAP.get(cat, "channel_news")
        url = f"https://assets.msn.com/service/Contents/Feed?cm=zh-cn&channelId={ch}"
        try:
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code != 200 or "json" not in r.headers.get(
                "content-type", ""
            ):
                continue
            for c in _extract_cards(r.json()):
                if not c["title"] or c["title"] in seen:
                    continue
                seen.add(c["title"])
                items.append(c)
                if len(items) >= count:
                    break
        except Exception:
            continue
        if len(items) >= count:
            break
    return items[:count]


# ---------------- RSS 回退 ----------------
def _parse_rss_item(item):
    title_el = item.find("title")
    link_el = item.find("link")
    desc_el = item.find("description")
    pub_el = item.find("pubDate")
    source_el = item.find("source")

    title = _norm(title_el.text if title_el is not None and title_el.text else "")
    link = _norm(link_el.text if link_el is not None and link_el.text else "")
    if not link:
        link_el2 = item.find("{http://www.w3.org/2005/Atom}link")
        if link_el2 is not None:
            link = link_el2.attrib.get("href", "")
    desc_html = desc_el.text if desc_el is not None and desc_el.text else ""
    summary = re.sub(r"<[^>]+>", "", desc_html).strip()
    summary = (summary[:140] + "...") if len(summary) > 140 else summary

    image = ""
    thumb = item.find("{http://search.yahoo.com/mrss/}thumbnail")
    if thumb is not None:
        image = thumb.attrib.get("url", "")
    if not image:
        content = item.find("{http://search.yahoo.com/mrss/}content")
        if content is not None:
            image = content.attrib.get("url", "")
    enc = item.find("enclosure")
    if not image and enc is not None and "image" in (
        enc.attrib.get("type", "") + " " + enc.attrib.get("url", "")
    ).lower():
        image = enc.attrib.get("url", "")
    if not image:
        m = IMG_RE.search(desc_html)
        if m:
            image = m.group(1)
    if image and image.startswith("//"):
        image = "https:" + image

    source = ""
    if source_el is not None and source_el.text:
        source = source_el.text.strip()
    elif " - " in title:
        source = title.rsplit(" - ", 1)[-1]
        title = title.rsplit(" - ", 1)[0]

    pub = _norm(pub_el.text if pub_el is not None and pub_el.text else "")
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "image": image,
        "source": source,
        "published": pub,
        "fetched_at": time.time(),
    }


def _fetch_one_feed(name_url):
    name, url = name_url
    lst = []
    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA,
                     "Accept": "application/rss+xml, application/xml, text/xml"},
            timeout=4,
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
        channel = root.find("channel")
        els = (channel.findall("item") if channel is not None
               else root.findall("{http://www.w3.org/2005/Atom}entry"))
        for it in els:
            parsed = _parse_rss_item(it)
            if not parsed["title"]:
                continue
            if not parsed["source"]:
                parsed["source"] = name
            lst.append(parsed)
    except Exception:
        pass
    return lst


def fetch_rss_feeds(feeds, count):
    """并行抓取所有源（线程池），再按源轮询交错，保证每页都是多源混合。"""
    per_feed = []
    workers = max(2, min(len(feeds), 8))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for lst in ex.map(_fetch_one_feed, feeds):
            if lst:
                per_feed.append(lst)

    # 轮询交错：第0轮取每个源的第0条，第1轮取每个源的第1条……
    items = []
    seen = set()
    i = 0
    while True:
        progressed = False
        for lst in per_feed:
            if i < len(lst):
                progressed = True
                it = lst[i]
                key = it["title"]
                if key in seen:
                    continue
                seen.add(key)
                items.append(it)
                if len(items) >= count:
                    return items
        if not progressed:
            break
        i += 1
    return items


def _merge_feeds_for_categories(categories):
    """合并基础池 + 分类偏好源（按 URL 去重），保证源足够多。"""
    merged = list(FALLBACK_FEEDS)
    seen_urls = {url for _, url in merged}
    for cat in (categories or []):
        for name, url in CATEGORY_FEEDS.get(cat, []):
            if url not in seen_urls:
                seen_urls.add(url)
                merged.append((name, url))
    return merged


# ---------------- 统一入口 ----------------
def fetch_news(categories, count=8):
    """先 MSN，失败回退 RSS（按分类合并源），全部真实抓取。"""
    try:
        msn = fetch_msn_feed(categories, count)
        if msn:
            return msn
    except Exception:
        pass
    feeds = _merge_feeds_for_categories(categories)
    return fetch_rss_feeds(feeds, count)


def cover_path(url):
    if not url:
        return ""
    h = hashlib.md5(url.encode("utf-8")).hexdigest()
    ext = ".jpg"
    low = url.lower().split("?")[0]
    for e in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        if low.endswith(e):
            ext = e
            break
    return str(COVER_CACHE_DIR / (h + ext))


def download_cover(url):
    if not url:
        return ""
    path = cover_path(url)
    if os.path.exists(path):
        return path
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=6)
        r.raise_for_status()
        if len(r.content) < 200:
            return ""
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return ""


def cached_cover(url):
    """仅返回已缓存的封面路径，没有则空串（不发起网络请求）。"""
    if not url:
        return ""
    path = cover_path(url)
    return path if os.path.exists(path) else ""


def fetch_news_async(categories, count, callback):
    def worker():
        try:
            items = fetch_news(categories, count)
            callback(items, None)
        except Exception as e:
            callback(None, str(e))

    threading.Thread(target=worker, daemon=True).start()
