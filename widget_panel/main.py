"""入口：系统托盘 + 屏幕右侧边缘触发 + 控制器（刷新/缓存/设置）。

所有来自网络线程的 UI 更新都通过 Qt 信号投递到主线程，保证线程安全。
"""
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def _bootstrap_qt():
    """Linux 下固定使用 xcb(X11)：本程序依赖自由窗口定位与全局坐标
    （右侧滑入、边缘触发、点击外部关闭），Wayland 下这些能力受限。
    同时帮 pip 安装的 PyQt5 定位 Qt 平台插件目录。"""
    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
        try:
            import PyQt5

            base = os.path.dirname(PyQt5.__file__)
            for cand in (
                os.path.join(base, "Qt5", "plugins"),
                os.path.join(base, "Qt", "plugins"),
            ):
                if os.path.isdir(os.path.join(cand, "platforms")):
                    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", cand)
                    break
        except Exception:
            pass


_bootstrap_qt()

from PyQt5.QtCore import Qt, QObject, QEvent, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QWidget,
)

from . import resources as R
from .config import load_settings, save_settings
from .panel import WidgetPanel
from . import weather_service
from . import news_service
from .cache_service import CacheService, load_cached_state


class EdgeStrip(QWidget):
    """贴在屏幕右侧边缘的隐形窗口（XWayland 真实表面），
    光标移上去触发 enterEvent，比轮询全局坐标可靠。"""

    def __init__(self, screen_geo, on_enter):
        super().__init__()
        self._on_enter = on_enter
        self._geo = screen_geo
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_Hover, True)
        self.reposition(screen_geo)
        self.show()

    def reposition(self, geo):
        self._geo = geo
        w = 6
        self.setGeometry(geo.right() - w + 1, geo.y(), w, geo.height())

    def enterEvent(self, e):
        if self._on_enter:
            self._on_enter(self._geo)
        super().enterEvent(e)


class App(QObject):
    # 跨线程信号（worker -> 主线程 UI）
    weather_ready = pyqtSignal(object, str)   # weather dict|None, city
    located = pyqtSignal(object)              # location dict|None
    news_ready = pyqtSignal(list, bool)       # enriched articles, reset_seen_flag
    cover_ready = pyqtSignal(int, str, int)   # pool_index, cover_path, gen

    def __init__(self):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.settings = load_settings()

        screen = self.app.primaryScreen().geometry()
        self.panel = WidgetPanel(screen)
        self.panel.request_refresh.connect(self.refresh_all)
        self.panel.open_settings.connect(self._open_settings)
        self.panel.load_more_news.connect(self.next_news_page)

        self.settings_win = None
        self._news_pool = []
        self._news_page = 0
        self._page_size = self.settings.get("news_count", 6)
        self._news_gen = 0  # 资讯刷新代次，用于丢弃过期的封面回调
        # 已展示过的资讯链接，跨刷新去重，确保每次刷到的是新的
        self._seen_links = set()

        self.cache = CacheService(interval_seconds=300)
        self._cached_state = load_cached_state()
        self._apply_cached_state()

        # 右侧边缘触发：用屏幕边缘 X 窗口（enterEvent），比轮询全局坐标可靠
        self._screen = screen
        self._edge_strips = []
        self._last_edge_open = 0.0
        self._build_edge_strips()
        self.app.screenAdded.connect(lambda _s: self._build_edge_strips())

        self._build_tray()
        self.app.installEventFilter(self)

        # 信号 -> UI 更新
        self.weather_ready.connect(self._apply_weather)
        self.located.connect(self._apply_located)
        self.news_ready.connect(self._apply_news)
        self.cover_ready.connect(self._apply_cover)

        # 时钟
        self._clock = QTimer(self)
        self._clock.timeout.connect(self.panel.tick_clock)
        self._clock.start(1000)

        # 天气定时刷新
        self._weather_timer = QTimer(self)
        self._weather_timer.timeout.connect(self.refresh_weather)
        self._weather_timer.start(
            self.settings.get("weather_refresh_seconds", 600) * 1000
        )

        self.cache.start()
        self._locate_and_refresh_weather()
        QTimer.singleShot(400, self.refresh_news)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(R.tray_icon(48), self.app)
        self.tray.setToolTip("小组件 - 点击打开")
        self.tray.activated.connect(self._on_tray_activated)
        menu = QMenu()
        act_show = QAction("显示/隐藏", menu)
        act_show.triggered.connect(self.toggle_panel)
        act_refresh = QAction("立即刷新", menu)
        act_refresh.triggered.connect(self.refresh_all)
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_show)
        menu.addAction(act_refresh)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_panel()

    # ---- 缓存即时展示 ----
    def _apply_cached_state(self):
        st = self._cached_state
        if st.get("weather"):
            city = (st.get("location") or {}).get("city", "")
            self.panel.weather_card().update_weather(st["weather"], city)
        # 启动时总是先展示缓存资讯（秒开），后台刷新会替换为新内容
        if st.get("news"):
            self._news_pool = st["news"]
            self._news_page = 0
            self._show_news_page()

    # ---- 面板显隐 ----
    def open_panel(self):
        """仅打开（热区用），不会因鼠标移动而收起。"""
        if not self.panel.is_visible():
            self.panel.show_panel()
            self.refresh_news()
            self.refresh_weather()

    def toggle_panel(self):
        if self.panel.is_visible():
            self.panel.hide_panel()
        else:
            self.panel.show_panel()
            self.refresh_news()
            self.refresh_weather()

    def _build_edge_strips(self):
        """为每个屏幕创建右侧边缘触发条；设置关闭时清除。"""
        for s in self._edge_strips:
            s.close()
            s.deleteLater()
        self._edge_strips = []
        if not self.settings.get("edge_trigger", True):
            return
        for sc in self.app.screens():
            try:
                strip = EdgeStrip(sc.geometry(), self._on_edge_enter)
                self._edge_strips.append(strip)
            except Exception:
                continue

    def _on_edge_enter(self, screen_geo):
        """光标进入边缘条 -> 在该屏弹出面板（仅打开，0.4s 冷却防抖）。"""
        now = time.time()
        if now - self._last_edge_open < 0.4:
            return
        self._last_edge_open = now
        self.panel.set_screen(screen_geo)
        self.open_panel()

    def eventFilter(self, obj, ev):
        # 点击面板外收起；但热区与设置窗口内的点击不收起
        if ev.type() == QEvent.MouseButtonPress and self.panel.is_visible():
            gp = ev.globalPos()
            on_hotzone = any(
                sc.geometry().right() - gp.x() < 8
                and sc.geometry().y() <= gp.y() <= sc.geometry().bottom()
                for sc in self.app.screens()
            )
            on_settings = (
                self.settings_win is not None
                and self.settings_win.isVisible()
                and self.settings_win.geometry().contains(gp)
            )
            if (not self.panel.geometry().contains(gp)
                    and not on_hotzone and not on_settings):
                self.panel.hide_panel()
        if ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Escape:
            if self.panel.is_visible():
                self.panel.hide_panel()
        return super().eventFilter(obj, ev)

    # ---- 天气 ----
    def _locate_and_refresh_weather(self):
        if self.settings.get("auto_locate", True):
            weather_service.locate_async(lambda loc: self.located.emit(loc))
        else:
            lat = self.settings.get("latitude")
            lon = self.settings.get("longitude")
            city = self.settings.get("city_name") or self.settings.get(
                "city_override", "")
            if lat is not None and lon is not None:
                weather_service.get_weather_async(
                    lat, lon,
                    lambda w, e: self.weather_ready.emit(w, city),
                )

    def _apply_located(self, loc):
        if loc:
            self.settings["latitude"] = loc["lat"]
            self.settings["longitude"] = loc["lon"]
            self.settings["city_name"] = loc["city"]
            self.cache.update(location=loc)
            weather_service.get_weather_async(
                loc["lat"], loc["lon"],
                lambda w, e: self.weather_ready.emit(w, loc["city"]),
            )
        else:
            self.panel.weather_card().update_weather(
                None, "定位失败，请在设置中手动填城市")

    def refresh_weather(self):
        lat = self.settings.get("latitude")
        lon = self.settings.get("longitude")
        city = self.settings.get("city_name") or self.settings.get(
            "city_override", "")
        if lat is None or lon is None:
            self._locate_and_refresh_weather()
            return
        weather_service.get_weather_async(
            lat, lon, lambda w, e: self.weather_ready.emit(w, city))

    def _apply_weather(self, weather, city):
        if weather:
            self.panel.weather_card().update_weather(weather, city)
            self.cache.update(weather=weather)

    # ---- 新闻广告 ----
    def refresh_news(self):
        cats = self.settings.get("news_categories", ["world"])
        page = self.settings.get("news_count", 6)
        self._page_size = page
        self._news_gen += 1
        gen = self._news_gen
        # 主线程快照已看链接，供 worker 只读过滤（线程安全）
        seen_snap = set(self._seen_links)
        # 抓取足够多的内容，保证多次刷新都有 fresh
        total = max(page * 14, 80)
        news_service.fetch_news_async(
            cats, total,
            lambda arts, err: self._on_news_fetched(arts, err, seen_snap, gen))

    def _on_news_fetched(self, articles, err, seen_snap, gen):
        # 过期的抓取结果直接丢弃
        if gen != self._news_gen:
            return
        if not articles:
            return

        fresh = [a for a in articles
                 if a.get("link") and a.get("link") not in seen_snap]
        seen_articles = [a for a in articles
                         if a.get("link") and a.get("link") in seen_snap]
        if fresh:
            # 有新鲜内容：新鲜排前，已看补足，保证首页能看到新资讯
            random.shuffle(fresh)
            random.shuffle(seen_articles)
            pool = (fresh + seen_articles)[: max(self._page_size * 4, 24)]
            for a in pool:
                a["_cover"] = news_service.cached_cover(a.get("image", ""))
            # 不 reset seen_links，持续累积去重，避免"冒出原来有的"
            self.news_ready.emit(pool, False)
            self._download_covers_async(pool, gen)
        else:
            # 完全没有新鲜内容：不更新（避免重复），仅滚动到顶部
            self.panel.scroll_to_top()

    def _download_covers_async(self, pool, gen):
        size = self._page_size
        # 需要下载的条目（有图且尚无缓存），首页优先
        todo = [i for i, a in enumerate(pool)
                if a.get("image") and not a.get("_cover")]
        todo.sort(key=lambda i: 0 if i < size else 1)
        if not todo:
            return

        def worker():
            with ThreadPoolExecutor(max_workers=6) as ex:
                futs = {ex.submit(news_service.download_cover,
                                  pool[i]["image"]): i for i in todo}
                for fut in as_completed(futs):
                    i = futs[fut]
                    try:
                        path = fut.result()
                    except Exception:
                        path = ""
                    if path and gen == self._news_gen:
                        self.cover_ready.emit(i, path, gen)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_cover(self, pool_index, path, gen):
        if gen != self._news_gen:
            return
        if not (0 <= pool_index < len(self._news_pool)):
            return
        self._news_pool[pool_index]["_cover"] = path
        # 若该条目当前正显示，更新可见卡片的封面
        start = self._news_page * self._page_size
        local = pool_index - start
        if 0 <= local < self._page_size:
            self.panel.update_card_cover(local, path)

    def _apply_news(self, articles, reset):
        if reset:
            self._seen_links.clear()
        self._news_pool = articles
        self._news_page = 0
        self._show_news_page()
        self.panel.scroll_to_top()
        # 标记本页已看，下次刷新不再出现
        for a in articles[: self._page_size]:
            if a.get("link"):
                self._seen_links.add(a["link"])
        self.cache.update(news=articles)

    def _show_news_page(self):
        size = self._page_size
        start = self._news_page * size
        slice_ = self._news_pool[start:start + size]
        self.panel.set_news_articles(slice_)

    def next_news_page(self):
        """“换一批”：翻到下一页；池子用尽则重新抓取（自动去重，出新内容）。"""
        size = self._page_size
        if (self._news_page + 1) * size >= len(self._news_pool):
            self.refresh_news()
            return
        self._news_page += 1
        start = self._news_page * size
        for a in self._news_pool[start:start + size]:
            if a.get("link"):
                self._seen_links.add(a["link"])
        self._show_news_page()
        self.panel.scroll_to_top()

    def refresh_all(self):
        self.refresh_weather()
        self.refresh_news()
        self.panel.scroll_to_top()

    # ---- 设置 ----
    def _open_settings(self):
        from .settings_window import SettingsWindow
        if self.settings_win is not None:
            self.settings_win.show()
            self.settings_win.raise_()
            self.settings_win.activateWindow()
            return
        self.settings_win = SettingsWindow(self.settings)
        self.settings_win.settings_changed.connect(self._on_settings)
        self.settings_win.destroyed.connect(lambda *_: setattr(self, "settings_win", None))
        self.settings_win.show()

    def _on_settings(self, new_settings):
        self.settings.update(new_settings)
        save_settings(self.settings)
        self.panel.update_settings(self.settings)
        if self.settings_win is not None:
            self.settings_win.retheme(self.settings)
            self.settings_win._settings = self.settings
        self._page_size = self.settings.get("news_count", 6)
        self._build_edge_strips()
        self._weather_timer.setInterval(
            self.settings.get("weather_refresh_seconds", 600) * 1000)
        self._handle_autostart(self.settings.get("auto_start", True))
        self.refresh_all()

    def _handle_autostart(self, enable):
        import shutil
        from pathlib import Path
        desktop = Path.home() / ".config" / "autostart"
        desktop.mkdir(parents=True, exist_ok=True)
        f = desktop / "widget-panel.desktop"
        if enable:
            if shutil.which("widget-panel"):
                exec_line = "widget-panel"
            else:
                # 从源码运行：用当前解释器 + 模块，PYTHONPATH 指向包父目录
                pkg_parent = str(Path(__file__).resolve().parent.parent)
                exec_line = (
                    f"env PYTHONPATH={pkg_parent} "
                    f"{sys.executable} -m widget_panel.main"
                )
            f.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=WidgetPanel\n"
                f"Exec={exec_line}\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            if f.exists():
                f.unlink()

    def run(self):
        return self.app.exec_()

    def quit(self):
        self.cache.stop()
        self.tray.hide()
        self.app.quit()


def main():
    app = App()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
