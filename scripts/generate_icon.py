"""生成应用图标 PNG（多尺寸），用于 .desktop 与 deb 安装。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)
from widget_panel import resources as R  # noqa: E402

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "icons"
os.makedirs(OUT_DIR, exist_ok=True)

for size in (16, 22, 32, 48, 64, 128, 256):
    pm = R.tray_iconPixmap(size)
    sub = os.path.join(OUT_DIR, f"{size}x{size}", "apps")
    os.makedirs(sub, exist_ok=True)
    pm.save(os.path.join(sub, "widget-panel.png"), "PNG")

print(f"icons generated under {OUT_DIR}")
