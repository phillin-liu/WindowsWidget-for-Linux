"""设置：独立窗口（从面板移出），含亮暗/透明度/大小等全部选项。"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QSlider,
    QPushButton,
    QFormLayout,
    QGroupBox,
    QGridLayout,
)

from .styles import build_qss, themed_palette

ALL_CATS = ["world", "technology", "entertainment", "sports",
            "business", "science", "health", "politics"]


class SettingsWindow(QWidget):
    """独立的设置窗口，应用后发出 settings_changed(dict)。"""

    settings_changed = pyqtSignal(dict)

    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("小组件 - 设置")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setObjectName("SettingsWin")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.resize(440, 620)
        self._settings = dict(settings)
        self.setStyleSheet(build_qss(settings.get("theme_mode", "dark"),
                                     settings.get("opacity", 92)))
        # 给原生输入控件套主题调色板：原生 QLineEdit/QComboBox/QSpinBox/QCheckBox
        # 按深/浅色渲染文字、箭头、勾选，在任何 Linux 上都能稳定显示
        self.setPalette(themed_palette(settings.get("theme_mode", "dark")))
        self._build()
        self._apply_btn.clicked.connect(self._on_apply)

    def _build(self):
        s = self._settings
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 外观
        appearance = QGroupBox("外观")
        ag = QFormLayout(appearance)
        self._theme = QComboBox()
        self._theme.addItem("深色", "dark")
        self._theme.addItem("浅色", "light")
        self._theme.setCurrentIndex(0 if s.get("theme_mode", "dark") == "dark" else 1)

        self._opacity = QSlider(Qt.Horizontal)
        self._opacity.setRange(40, 100)
        self._opacity.setValue(int(s.get("opacity", 92)))
        self._opacity_lbl = QLabel(f"{self._opacity.value()}%")
        self._opacity.valueChanged.connect(
            lambda v: self._opacity_lbl.setText(f"{v}%"))
        op_row = QHBoxLayout()
        op_row.addWidget(self._opacity, 1)
        op_row.addWidget(self._opacity_lbl)

        self._width = QSlider(Qt.Horizontal)
        self._width.setRange(360, 720)
        self._width.setValue(int(s.get("panel_width", 460)))
        self._width_lbl = QLabel(f"{self._width.value()} px")
        self._width.valueChanged.connect(
            lambda v: self._width_lbl.setText(f"{v} px"))
        w_row = QHBoxLayout()
        w_row.addWidget(self._width, 1)
        w_row.addWidget(self._width_lbl)

        ag.addRow("主题", self._theme)
        ag.addRow("透明度", op_row)
        ag.addRow("面板宽度", w_row)
        root.addWidget(appearance)

        # 位置与天气
        loc = QGroupBox("位置与天气")
        lg = QGridLayout(loc)
        self._auto_locate = QCheckBox("自动定位城市")
        self._auto_locate.setChecked(s.get("auto_locate", True))
        self._city_edit = QLineEdit(s.get("city_override", ""))
        self._city_edit.setPlaceholderText("手动城市名（留空=自动定位）")
        self._weather_spin = QSpinBox()
        self._weather_spin.setRange(60, 7200)
        self._weather_spin.setValue(int(s.get("weather_refresh_seconds", 600)))
        self._weather_spin.setSuffix(" 秒")
        lg.addWidget(self._auto_locate, 0, 0, 1, 2)
        lg.addWidget(QLabel("城市"), 1, 0)
        lg.addWidget(self._city_edit, 1, 1)
        lg.addWidget(QLabel("天气刷新"), 2, 0)
        lg.addWidget(self._weather_spin, 2, 1)
        root.addWidget(loc)

        # 资讯
        news = QGroupBox("资讯 / 广告")
        ng = QFormLayout(news)
        self._news_spin = QSpinBox()
        self._news_spin.setRange(2, 20)
        self._news_spin.setValue(int(s.get("news_count", 6)))
        self._news_spin.setSuffix(" 条/页")
        self._cats = QComboBox()
        cur = s.get("news_categories", ["world"])
        for c in ALL_CATS:
            self._cats.addItem(c, c)
        if cur and cur[0] in ALL_CATS:
            self._cats.setCurrentIndex(ALL_CATS.index(cur[0]))
        ng.addRow("每页数量", self._news_spin)
        ng.addRow("资讯分类", self._cats)
        root.addWidget(news)

        # 系统
        system = QGroupBox("系统")
        sg = QVBoxLayout(system)
        self._edge = QCheckBox("鼠标移到屏幕右侧边缘自动弹出")
        self._edge.setChecked(s.get("edge_trigger", True))
        self._autostart = QCheckBox("开机自启")
        self._autostart.setChecked(s.get("auto_start", True))
        sg.addWidget(self._edge)
        sg.addWidget(self._autostart)
        root.addWidget(system)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._apply_btn = QPushButton("应用并保存")
        self._apply_btn.setObjectName("ApplyBtn")
        btn_row.addWidget(self._apply_btn)
        root.addLayout(btn_row)

    def _on_apply(self):
        new = dict(self._settings)
        new.update({
            "theme_mode": self._theme.currentData(),
            "opacity": self._opacity.value(),
            "panel_width": self._width.value(),
            "auto_locate": self._auto_locate.isChecked(),
            "city_override": self._city_edit.text().strip(),
            "weather_refresh_seconds": self._weather_spin.value(),
            "news_count": self._news_spin.value(),
            "news_categories": [self._cats.currentData()],
            "edge_trigger": self._edge.isChecked(),
            "auto_start": self._autostart.isChecked(),
        })
        self._settings = new
        self.settings_changed.emit(new)
        self.close()

    def retheme(self, settings):
        self.setStyleSheet(build_qss(settings.get("theme_mode", "dark"),
                                     settings.get("opacity", 92)))
        self.setPalette(themed_palette(settings.get("theme_mode", "dark")))
