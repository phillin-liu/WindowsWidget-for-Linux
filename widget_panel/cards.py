"""卡片组件：日期卡、天气卡、新闻广告卡。

关键防闪烁设计：
  - 日期封面只在初始化/尺寸变化时绘制，秒级 tick 只刷新文字；
  - 天气封面用固定尺寸图标，仅在天气数据变化时重绘；
  - 新闻封面用固定高度 + 水平扩展尺寸策略，宽度随卡片稳定，不随图片比例抖动。
"""
import datetime

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QSizePolicy,
)

from . import resources as R


class DateCard(QFrame):
    """日期卡片：自绘封面 + 实时日期星期。"""

    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self.setCursor(Qt.ArrowCursor)
        self._cover = QLabel()
        self._cover.setObjectName("CardCover")
        self._cover.setScaledContents(True)
        self._cover.setFixedHeight(140)
        self._cover.setMinimumWidth(200)
        self._cover.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._info = QLabel()
        self._info.setObjectName("DateText")
        self._info.setAlignment(Qt.AlignCenter)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.setSpacing(6)
        lay.addWidget(self._cover)
        lay.addWidget(self._info)
        self._last_day = None
        self._drawn_w = 0
        self.redraw_cover()
        self._update_text()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 尺寸变化后按真实宽度重绘封面，避免拉伸/错位
        w = self._cover.width()
        if w > 0 and abs(w - self._drawn_w) > 4:
            self.redraw_cover()

    def redraw_cover(self):
        now = datetime.datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四",
                    "星期五", "星期六", "星期日"]
        wd = weekdays[now.weekday()]
        w = max(self._cover.width(), 360)
        self._drawn_w = w
        self._cover.setPixmap(R.date_cover(now.year, now.month, now.day, wd, w, 140))
        self._last_day = now.day

    def _update_text(self):
        now = datetime.datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四",
                    "星期五", "星期六", "星期日"]
        wd = weekdays[now.weekday()]
        self._info.setText(
            f"{now.year}/{now.month:02d}/{now.day:02d}  {wd}  "
            f"{now.strftime('%H:%M:%S')}"
        )

    def tick(self):
        # 跨天时才重绘封面，否则只刷新文字，杜绝每秒重绘闪烁
        now = datetime.datetime.now()
        if self._last_day is not None and now.day != self._last_day:
            self.redraw_cover()
        self._update_text()


class WeatherCard(QFrame):
    """天气卡片：固定图标 + 实时数据 + 3 天预报。"""

    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self.setCursor(Qt.ArrowCursor)
        self._icon = QLabel()
        self._icon.setFixedSize(96, 96)
        self._icon.setAlignment(Qt.AlignCenter)
        self._last_sig = None

        self._city = QLabel("定位中…")
        self._city.setObjectName("HeaderSub")
        self._temp = QLabel("--°")
        self._temp.setObjectName("WeatherTemp")
        self._desc = QLabel("--")
        self._desc.setObjectName("WeatherDesc")
        self._meta = QLabel("湿度 -- · 风 -- km/h · 体感 --°")
        self._meta.setObjectName("CardMeta")
        self._forecast = QLabel("")
        self._forecast.setObjectName("ForecastRow")

        top = QHBoxLayout()
        top.setContentsMargins(12, 8, 12, 8)
        left = QVBoxLayout()
        left.addWidget(self._city)
        left.addWidget(self._temp)
        left.addWidget(self._desc)
        left.addStretch()
        top.addLayout(left)
        top.addStretch()
        top.addWidget(self._icon, alignment=Qt.AlignRight | Qt.AlignVCenter)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setSpacing(4)
        lay.addLayout(top)
        lay.addWidget(self._meta)
        lay.addWidget(self._forecast)

    def update_weather(self, weather, city=""):
        if not weather:
            self._desc.setText("天气获取失败")
            return
        self._city.setText(city or "当前位置")
        self._temp.setText(f"{weather.get('temp', '--')}°")
        self._desc.setText(weather.get("desc", "--"))
        self._meta.setText(
            f"湿度 {weather.get('humidity', '--')}% · "
            f"风 {weather.get('wind', '--')} km/h · "
            f"体感 {weather.get('feels', '--')}°"
        )
        fc = weather.get("forecast", [])
        lines = []
        for i, d in enumerate(fc):
            tag = ["今天", "明天", "后天"][i] if i < 3 else ""
            lines.append(
                f"{tag} {d.get('desc','')} {d.get('min','--')}°~{d.get('max','--')}°"
            )
        self._forecast.setText("\n".join(lines))
        # 仅在图标/日夜变化时重绘，避免每次刷新闪烁
        sig = (weather.get("icon"), weather.get("is_day", True))
        if sig != self._last_sig:
            self._icon.setPixmap(
                R.weather_icon(weather.get("icon", "cloud"), 96,
                               weather.get("is_day", True))
            )
            self._last_sig = sig


class NewsCard(QFrame):
    """新闻广告卡：MSN 原版封面 + 标题摘要，点击打开文章。"""

    clicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self._link = ""
        self._cover = QLabel()
        self._cover.setObjectName("CardCover")
        self._cover.setScaledContents(True)
        self._cover.setFixedHeight(150)
        self._cover.setMinimumWidth(200)
        self._cover.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._title = QLabel("")
        self._title.setObjectName("CardTitle")
        self._title.setWordWrap(True)
        self._title.setOpenExternalLinks(False)
        self._meta = QLabel("")
        self._meta.setObjectName("CardMeta")
        self._summary = QLabel("")
        self._summary.setObjectName("CardSummary")
        self._summary.setWordWrap(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setSpacing(5)
        lay.addWidget(self._cover)
        lay.addWidget(self._title)
        lay.addWidget(self._meta)
        lay.addWidget(self._summary)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._link:
            self.clicked.emit(self._link)
        super().mousePressEvent(e)

    def set_article(self, article, cover_path=""):
        self._link = article.get("link", "")
        self._title.setText(article.get("title", ""))
        src = article.get("source", "")
        pub = article.get("published", "")
        self._meta.setText(f"{src}  ·  {pub[:16]}")
        self._summary.setText(article.get("summary", ""))
        if cover_path:
            pm = QPixmap(cover_path)
            if not pm.isNull():
                self._cover.setPixmap(pm)
                return
        w = max(self._cover.width(), 360)
        self._cover.setPixmap(R.fallback_cover(article.get("title", ""), w, 150))

    def update_cover(self, cover_path):
        """封面后台下载完成后单独更新封面，不影响文字、不闪烁。"""
        if not cover_path:
            return
        pm = QPixmap(cover_path)
        if not pm.isNull():
            self._cover.setPixmap(pm)
