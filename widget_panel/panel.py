"""主面板：Win11 风格右侧滑入面板，包含所有卡片。"""
import datetime

from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QFrame,
)

from .styles import build_qss
from . import resources as R
from .cards import DateCard, WeatherCard, NewsCard
from .config import load_settings


class WidgetPanel(QWidget):
    """从屏幕右侧滑入的小组件面板。"""

    open_settings = pyqtSignal()
    load_more_news = pyqtSignal()
    request_refresh = pyqtSignal()

    def __init__(self, screen_geo):
        super().__init__()
        self._screen = screen_geo
        self._settings = load_settings()
        self._width = self._settings.get("panel_width", 460)
        self._margin = 8
        self._news_cards = []

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._build_ui()
        self.apply_style(self._settings.get("theme_mode", "dark"),
                         self._settings.get("opacity", 92))
        self._resize_and_place(hidden=True)

        self._anim = None
        self._hidden = True

    def _build_ui(self):
        root = QFrame()
        root.setObjectName("PanelRoot")
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(14, 12, 14, 12)
        root_lay.setSpacing(8)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self._title = QLabel("小组件")
        self._title.setObjectName("HeaderTitle")
        self._subtitle = QLabel(datetime.date.today().strftime("%Y-%m-%d"))
        self._subtitle.setObjectName("HeaderSub")
        title_box.addWidget(self._title)
        title_box.addWidget(self._subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("SettingsBtn")
        self._settings_btn.setFixedSize(30, 30)
        self._settings_btn.setToolTip("设置")
        self._settings_btn.clicked.connect(self.open_settings.emit)
        self._refresh_btn = QPushButton()
        self._refresh_btn.setObjectName("RefreshBtn")
        self._refresh_btn.setFixedSize(30, 30)
        self._refresh_btn.setToolTip("刷新")
        self._refresh_btn.clicked.connect(self.request_refresh.emit)
        self._close_btn = QPushButton()
        self._close_btn.setObjectName("CloseBtn")
        self._close_btn.setFixedSize(30, 30)
        self._close_btn.setToolTip("关闭")
        self._close_btn.clicked.connect(self.hide_panel)
        for b in (self._settings_btn, self._refresh_btn, self._close_btn):
            header.addWidget(b)
        root_lay.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll = scroll

        content = QWidget()
        content.setObjectName("ScrollContent")
        self._content_lay = QVBoxLayout(content)
        self._content_lay.setContentsMargins(2, 4, 2, 4)
        self._content_lay.setSpacing(10)

        self._date_card = DateCard()
        self._weather_card = WeatherCard()
        self._content_lay.addWidget(self._date_card)
        self._content_lay.addWidget(self._weather_card)

        self._news_section = QLabel("资讯 / 广告")
        self._news_section.setObjectName("SectionLabel")
        self._content_lay.addWidget(self._news_section)
        self._news_container = QVBoxLayout()
        self._news_container.setSpacing(10)
        self._content_lay.addLayout(self._news_container)

        self._more_btn = QPushButton("  换一批")
        self._more_btn.setObjectName("MoreBtn")
        self._more_btn.setCursor(Qt.PointingHandCursor)
        self._more_btn.clicked.connect(self.load_more_news.emit)
        self._content_lay.addWidget(self._more_btn)

        self._content_lay.addStretch()
        scroll.setWidget(content)
        root_lay.addWidget(scroll)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

    def apply_style(self, theme_mode, opacity):
        self.setStyleSheet(build_qss(theme_mode, opacity))
        self._apply_tool_icons(theme_mode)

    def _apply_tool_icons(self, theme_mode):
        """按主题色重绘工具按钮图标（深色用浅色图标，浅色用深色图标）。"""
        color = "#18181c" if theme_mode == "light" else "#f3f3f3"
        sz = 18
        self._settings_btn.setIcon(QIcon(R.tool_icon("settings", sz, color)))
        self._refresh_btn.setIcon(QIcon(R.tool_icon("refresh", sz, color)))
        self._close_btn.setIcon(QIcon(R.tool_icon("close", sz, color)))
        self._more_btn.setIcon(QIcon(R.tool_icon("refresh", sz, color)))
        for b in (self._settings_btn, self._refresh_btn, self._close_btn, self._more_btn):
            b.setIconSize(QSize(sz, sz))

    def _resize_and_place(self, hidden=False):
        h = self._screen.height() - 2 * self._margin - 40
        x_hidden = self._screen.right() + 4
        x_shown = self._screen.right() - self._width - self._margin
        if hidden:
            self.setGeometry(x_hidden, self._margin + 40, self._width, h)
        else:
            self.setGeometry(x_shown, self._margin + 40, self._width, h)

    # ---- public API ----
    def date_card(self):
        return self._date_card

    def weather_card(self):
        return self._weather_card

    def set_news_articles(self, articles):
        """复用已有卡片，避免每次刷新重建导致的闪烁。"""
        self.setUpdatesEnabled(False)
        try:
            while len(self._news_cards) > len(articles):
                c = self._news_cards.pop()
                c.setParent(None)
                c.deleteLater()
            for i, art in enumerate(articles):
                if i < len(self._news_cards):
                    card = self._news_cards[i]
                else:
                    card = NewsCard()
                    card.clicked.connect(self._open_link)
                    self._news_container.addWidget(card)
                    self._news_cards.append(card)
                card.set_article(art, art.get("_cover", ""))
                card.setVisible(True)
        finally:
            self.setUpdatesEnabled(True)

    def update_card_cover(self, local_index, cover_path):
        """封面后台下载完后，更新当前可见页的第 local_index 张卡片封面。"""
        if 0 <= local_index < len(self._news_cards):
            self._news_cards[local_index].update_cover(cover_path)

    def update_settings(self, settings):
        old_w = self._width
        self._settings = settings
        self._width = settings.get("panel_width", 460)
        self.apply_style(settings.get("theme_mode", "dark"),
                         settings.get("opacity", 92))
        self._resize_and_place(hidden=self._hidden)
        if old_w != self._width:
            self._date_card.redraw_cover()

    def set_screen(self, screen_geo):
        """切换面板所在屏幕（多显示器时跟随光标）。"""
        self._screen = screen_geo
        self._resize_and_place(hidden=self._hidden)

    # ---- animation ----
    def scroll_to_top(self):
        self._scroll.verticalScrollBar().setValue(0)

    def show_panel(self):
        if not self._hidden:
            return
        self._hidden = False
        self._resize_and_place(hidden=False)
        self.show()
        self.raise_()
        self.scroll_to_top()
        start = QRect(self._screen.right() + 4, self.y(), self.width(), self.height())
        end = self.geometry()
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(260)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def hide_panel(self):
        if self._hidden:
            return
        end = QRect(self._screen.right() + 4, self.y(), self.width(), self.height())
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(220)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._on_hidden)
        self._anim.start()

    def _on_hidden(self):
        self._hidden = True
        self.hide()

    def is_visible(self):
        return not self._hidden

    def _open_link(self, url):
        import webbrowser
        webbrowser.open(url)

    def tick_clock(self):
        self._date_card.tick()
        self._subtitle.setText(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
