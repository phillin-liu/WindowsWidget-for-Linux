"""自绘资源：托盘图标、天气图标、天气/日期卡片封面，全部用 QPainter 绘制。"""
import os
import math

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPainterPath,
    QLinearGradient,
    QFont,
    QPen,
    QRadialGradient,
)
from PyQt5.QtGui import QIcon

# 外置图标（包内 img.png），缺失时回退自绘
_IMG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img.png")


def _gradient_pixmap(w, h, c1, c2, vertical=True):
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    g = QLinearGradient(0, 0, 0 if vertical else w, h if vertical else 0)
    g.setColorAt(0, c1)
    g.setColorAt(1, c2)
    p.fillRect(0, 0, w, h, g)
    p.end()
    return pm


def tray_iconPixmap(size=64):
    """托盘/启动器图标：优先用包内 img.png，缺失时回退自绘 Win11 风格图标。"""
    if os.path.exists(_IMG_PATH):
        pm = QPixmap(_IMG_PATH)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.KeepAspectRatio,
                             Qt.SmoothTransformation)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(QRectF(2, 2, size - 4, size - 4), 14, 14)
    p.setClipPath(path)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#0a84ff"))
    g.setColorAt(1, QColor("#7c3aed"))
    p.fillRect(0, 0, size, size, g)

    card_w = (size - 18) / 2
    card_h = (size - 18) / 2
    positions = [(6, 6), (6 + card_w + 6, 6), (6, 6 + card_h + 6),
                 (6 + card_w + 6, 6 + card_h + 6)]
    palette = [QColor("#ffffff"), QColor("#7dd3fc"),
               QColor("#fde68a"), QColor("#86efac")]
    for (x, y), col in zip(positions, palette):
        p.setBrush(col)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(x, y, card_w, card_h), 6, 6)
    p.end()
    return pm


def tray_icon(size=64):
    return QIcon(tray_iconPixmap(size))


def tool_icon(kind, size=20, color="#f3f3f3"):
    """自绘工具按钮图标（设置/刷新/关闭），不依赖字体符号，任何系统都能显示。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    col = QColor(color)
    lw = max(1.4, size * 0.09)
    pen = QPen(col, lw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    if kind == "close":
        p.setPen(pen)
        m = size * 0.30
        p.drawLine(QPointF(m, m), QPointF(size - m, size - m))
        p.drawLine(QPointF(size - m, m), QPointF(m, size - m))

    elif kind == "refresh":
        p.setBrush(Qt.NoBrush)
        p.setPen(pen)
        cx = cy = size / 2
        r = size * 0.32
        # 3/4 圆弧，缺口在右下
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 0, 270 * 16)
        # 箭头三角在弧末端（6 点钟方向），指向右
        p.setBrush(col)
        p.setPen(Qt.NoPen)
        ah = size * 0.16
        tip = QPointF(cx + ah, cy + r)
        b1 = QPointF(cx, cy + r - ah * 0.7)
        b2 = QPointF(cx, cy + r + ah * 0.7)
        tri = QPainterPath()
        tri.moveTo(tip)
        tri.lineTo(b1)
        tri.lineTo(b2)
        tri.closeSubpath()
        p.drawPath(tri)

    elif kind == "settings":
        # 三条滑杆（带旋钮），表示设置
        for i, frac in enumerate((0.30, 0.52, 0.74)):
            y = size * frac
            p.setPen(pen)
            p.drawLine(QPointF(size * 0.20, y), QPointF(size * 0.80, y))
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            knob_x = size * (0.38 if i == 0 else (0.62 if i == 1 else 0.50))
            p.drawEllipse(QPointF(knob_x, y), size * 0.10, size * 0.10)

    p.end()
    return pm


def write_indicator_icons(theme_mode="dark"):
    """生成设置窗口控件指示器图标（对勾/下拉箭头/微调上下箭头）到缓存目录，
    返回 {name: file_uri}。QSS 用 image: url(...) 引用，保证图标一定显示。"""
    from .config import CACHE_DIR

    out = CACHE_DIR / "icons"
    out.mkdir(parents=True, exist_ok=True)
    text_color = "#18181c" if theme_mode == "light" else "#f3f3f3"
    uris = {}

    def save(pm, name):
        f = out / name
        pm.save(str(f), "PNG")
        uris[name] = f.as_uri()

    # 对勾（白色，画在蓝色指示器上）
    pm = QPixmap(16, 16)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#ffffff"), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(3, 8)
    path.lineTo(7, 12)
    path.lineTo(13, 4)
    p.drawPath(path)
    p.end()
    save(pm, "check.png")

    # 下拉箭头（文字色，V 形）
    pm = QPixmap(14, 14)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor(text_color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(3, 5)
    path.lineTo(7, 9)
    path.lineTo(11, 5)
    p.drawPath(path)
    p.end()
    save(pm, "arrow.png")

    # 微调框上箭头（实心三角，向上）
    pm = QPixmap(12, 8)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(text_color))
    path = QPainterPath()
    path.moveTo(2, 6)
    path.lineTo(10, 6)
    path.lineTo(6, 1)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    save(pm, "spin_up.png")

    # 微调框下箭头（实心三角，向下）
    pm = QPixmap(12, 8)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(text_color))
    path = QPainterPath()
    path.moveTo(2, 2)
    path.lineTo(10, 2)
    path.lineTo(6, 7)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    save(pm, "spin_down.png")

    return uris


def weather_icon(icon_key, size=96, is_day=True):
    """按天气 key 绘制图标。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)

    sun = QColor("#ffd166") if is_day else QColor("#cbd5e1")
    cloud = QColor("#e5e7eb")
    cloud_dark = QColor("#9ca3af")
    rain = QColor("#60a5fa")
    snow = QColor("#e0f2fe")
    storm = QColor("#a78bfa")

    def draw_sun(cx, cy, r):
        p.setBrush(sun)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(sun, 3))
        for i in range(8):
            import math
            a = i * math.pi / 4
            x1 = cx + math.cos(a) * (r + 4)
            y1 = cy + math.sin(a) * (r + 4)
            x2 = cx + math.cos(a) * (r + 10)
            y2 = cy + math.sin(a) * (r + 10)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.setPen(Qt.NoPen)

    def draw_cloud(cx, cy, r, col=cloud):
        p.setBrush(col)
        p.drawEllipse(QPointF(cx - r * 0.6, cy), r, r)
        p.drawEllipse(QPointF(cx + r * 0.6, cy), r * 0.85, r * 0.85)
        p.drawEllipse(QPointF(cx, cy - r * 0.5), r * 0.9, r * 0.9)
        p.drawRect(QRectF(cx - r * 1.2, cy, r * 2.4, r * 0.9))

    cx, cy = size / 2, size / 2
    if icon_key == "sun":
        draw_sun(cx, cy, size * 0.18)
    elif icon_key == "sun_cloud":
        draw_sun(cx - size * 0.12, cy - size * 0.14, size * 0.13)
        draw_cloud(cx + size * 0.08, cy + size * 0.08, size * 0.16)
    elif icon_key == "cloud":
        draw_cloud(cx, cy, size * 0.2)
    elif icon_key == "fog":
        draw_cloud(cx, cy - size * 0.08, size * 0.18)
        p.setBrush(cloud_dark)
        for i in range(3):
            p.drawRoundedRect(
                QRectF(size * 0.2, cy + size * 0.12 + i * size * 0.1,
                       size * 0.6, size * 0.04),
                2, 2,
            )
    elif icon_key == "rain":
        draw_cloud(cx, cy - size * 0.06, size * 0.18, cloud_dark)
        p.setBrush(rain)
        for i in range(4):
            x = size * 0.28 + i * size * 0.15
            p.drawRoundedRect(QRectF(x, cy + size * 0.16, size * 0.035, size * 0.14),
                              2, 2)
    elif icon_key == "snow":
        draw_cloud(cx, cy - size * 0.06, size * 0.18, cloud_dark)
        p.setBrush(snow)
        for i in range(4):
            x = size * 0.28 + i * size * 0.15
            p.drawEllipse(QPointF(x, cy + size * 0.22), size * 0.035, size * 0.035)
    elif icon_key == "storm":
        draw_cloud(cx, cy - size * 0.06, size * 0.18, cloud_dark)
        p.setBrush(storm)
        path = QPainterPath()
        path.moveTo(cx - size * 0.04, cy + size * 0.12)
        path.lineTo(cx + size * 0.06, cy + size * 0.12)
        path.lineTo(cx, cy + size * 0.24)
        path.lineTo(cx + size * 0.08, cy + size * 0.24)
        path.lineTo(cx - size * 0.02, cy + size * 0.4)
        path.lineTo(cx + size * 0.02, cy + size * 0.28)
        path.lineTo(cx - size * 0.06, cy + size * 0.28)
        path.closeSubpath()
        p.drawPath(path)
    else:
        draw_cloud(cx, cy, size * 0.2)

    p.end()
    return pm


def weather_cover(weather, w=400, h=180):
    """天气卡片自绘封面：渐变天空 + 天气图标 + 温度。"""
    is_day = weather.get("is_day", True)
    if is_day:
        c1, c2 = QColor("#3b82f6"), QColor("#60a5fa")
    else:
        c1, c2 = QColor("#1e293b"), QColor("#334155")
    pm = _gradient_pixmap(w, h, c1, c2, vertical=False)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    icon = weather_icon(weather.get("icon", "cloud"), 110, is_day)
    p.drawPixmap(w - 120, 20, icon)
    p.setPen(QColor("#ffffff"))
    f = QFont()
    f.setPointSize(34)
    f.setBold(True)
    p.setFont(f)
    temp = weather.get("temp", "--")
    p.drawText(QRectF(24, 30, 200, 70), Qt.AlignLeft,
               f"{temp}°" if temp != "--" else "--")
    f.setPointSize(13)
    f.setBold(False)
    p.setFont(f)
    p.drawText(QRectF(26, 100, w - 140, 30), Qt.AlignLeft,
               weather.get("desc", ""))
    p.end()
    return pm


def date_cover(year, month, day, weekday, w=400, h=140):
    """日期卡片自绘封面：渐变 + 大日期 + 星期。布局按 w/h 等比例缩放，避免错位。"""
    pm = _gradient_pixmap(w, h, QColor("#7c3aed"), QColor("#2563eb"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QColor("#ffffff"))
    f = QFont()
    # 月份（左上）
    f.setPointSizeF(h * 0.10)
    p.setFont(f)
    p.drawText(QRectF(20, h * 0.08, w - 40, h * 0.18),
               Qt.AlignLeft | Qt.AlignVCenter, f"{year} 年 {month} 月")
    # 大日期（中部）
    f.setPointSizeF(h * 0.46)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(20, h * 0.24, w - 40, h * 0.50),
               Qt.AlignLeft | Qt.AlignVCenter, str(day))
    # 星期（左下）
    f.setPointSizeF(h * 0.11)
    f.setBold(False)
    p.setFont(f)
    p.drawText(QRectF(24, h * 0.76, w - 40, h * 0.18),
               Qt.AlignLeft | Qt.AlignVCenter, weekday)
    p.end()
    return pm


def fallback_cover(text, w=400, h=180):
    """新闻封面缺失时的自绘兜底封面。"""
    pm = _gradient_pixmap(w, h, QColor("#0f172a"), QColor("#334155"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor(255, 255, 255, 30))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(16, 16, 52, 52), 12, 12)
    p.setPen(QColor("#ffffff"))
    f = QFont()
    f.setPointSize(11)
    p.setFont(f)
    p.drawText(QRectF(24, 30, 40, 30), Qt.AlignLeft, "MSN")
    f.setPointSize(12)
    p.setFont(f)
    p.drawText(QRectF(20, h - 60, w - 40, 44), Qt.AlignLeft | Qt.TextWordWrap,
               (text or "资讯")[:24])
    p.end()
    return pm
