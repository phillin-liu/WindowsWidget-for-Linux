"""Win11 风格主题 QSS：支持深/浅色与透明度动态生成。"""

from PyQt5.QtGui import QColor, QPalette

from . import resources as R


def _palette(theme_mode):
    if theme_mode == "light":
        return {
            "panel": (250, 250, 252),
            "text": (24, 24, 28),
            "sub": (90, 90, 98),
            "card": (255, 255, 255),
            "card_hover": (245, 246, 250),
            "card_border": "rgba(0,0,0,40)",
            "card_hover_border": "rgba(10,132,255,180)",
            "input_bg": "rgb(255,255,255)",
            "input_border": "rgb(200,200,208)",
            "input_hover": "rgb(232,233,240)",
            "accent": "#0a84ff",
            "section": "#5a5a62",
        }
    return {
        "panel": (32, 32, 36),
        "text": (243, 243, 243),
        "sub": (207, 207, 207),
        "card": (60, 60, 68),
        "card_hover": (78, 78, 88),
        "card_border": "rgba(255,255,255,30)",
        "card_hover_border": "rgba(120,170,255,160)",
        "input_bg": "rgb(74,74,82)",
        "input_border": "rgb(120,120,130)",
        "input_hover": "rgb(96,96,106)",
        "accent": "#0a84ff",
        "section": "#bdbdbd",
    }


def build_qss(theme_mode="dark", opacity=92):
    p = _palette(theme_mode)
    alpha = int(max(0, min(100, opacity)) / 100 * 255)
    panel_bg = f"rgba({p['panel'][0]},{p['panel'][1]},{p['panel'][2]},{alpha})"
    card_bg = f"rgba({p['card'][0]},{p['card'][1]},{p['card'][2]},{min(255, alpha + 25)})"
    card_hover = f"rgba({p['card_hover'][0]},{p['card_hover'][1]},{p['card_hover'][2]},{min(255, alpha + 45)})"
    text = f"rgb({p['text'][0]},{p['text'][1]},{p['text'][2]})"
    sub = f"rgb({p['sub'][0]},{p['sub'][1]},{p['sub'][2]})"

    return f"""
    #PanelRoot {{
        background: {panel_bg};
        border-radius: 16px;
        border: 1px solid {p['card_border']};
    }}
    /* 设置窗口：使用不透明主题底色，保证文字始终可读 */
    #SettingsWin {{
        background: rgb({p['panel'][0]},{p['panel'][1]},{p['panel'][2]});
    }}
    QGroupBox {{
        border: 1px solid {p['card_border']};
        border-radius: 8px;
        margin-top: 12px;
        padding: 10px 8px 8px 8px;
        background: rgba({p['card'][0]},{p['card'][1]},{p['card'][2]},60);
        color: {text};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; subcontrol-position: top left;
        left: 10px; padding: 0 6px; color: {text};
    }}
    QScrollArea {{ background: transparent; border: none; }}
    #ScrollContent {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 6px 2px; }}
    QScrollBar::handle:vertical {{
        background: rgba(150,150,160,120); border-radius: 4px; min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    QLabel {{ color: {text}; }}
    #HeaderTitle {{ font-size: 18px; font-weight: 600; color: {text}; }}
    #HeaderSub {{ font-size: 11px; color: {sub}; }}
    #RefreshBtn, #CloseBtn, #SettingsBtn, #MoreBtn {{
        background: {p['input_bg']}; border: none; border-radius: 14px;
        color: {text}; padding: 4px; font-size: 13px;
    }}
    #RefreshBtn:hover, #CloseBtn:hover, #SettingsBtn:hover, #MoreBtn:hover {{
        background: {p['input_hover']};
    }}
    #MoreBtn {{ border-radius: 8px; padding: 6px; }}

    #Card {{
        background: {card_bg};
        border-radius: 12px;
        border: 1px solid {p['card_border']};
    }}
    #Card:hover {{
        background: {card_hover};
        border: 1px solid {p['card_hover_border']};
    }}
    #CardCover {{ border-top-left-radius: 12px; border-top-right-radius: 12px; }}
    #CardTitle {{ font-size: 13px; font-weight: 600; color: {text}; }}
    #CardMeta {{ font-size: 10px; color: {sub}; }}
    #CardSummary {{ font-size: 11px; color: {sub}; }}

    #DateText {{ color: {text}; }}
    #WeatherTemp {{ font-size: 30px; font-weight: 700; color: {text}; }}
    #WeatherDesc {{ font-size: 12px; color: {sub}; }}
    #ForecastRow {{ font-size: 11px; color: {sub}; }}
    #SectionLabel {{ font-size: 12px; font-weight: 600; color: {p['section']}; }}

    QComboBox QAbstractItemView {{
        background: rgb({p['card'][0]},{p['card'][1]},{p['card'][2]});
        color: {text}; selection-background-color: {p['accent']};
        border: 1px solid {p['input_border']};
    }}
    QPushButton#ApplyBtn {{
        background: {p['accent']}; color: white; border: none; border-radius: 6px;
        padding: 6px 14px; font-size: 12px;
    }}
    QPushButton#ApplyBtn:hover {{ background: #3b9bff; }}
    QCheckBox {{ color: {text}; spacing: 6px; }}
    QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: {p['input_bg']}; }}
    QSlider::sub-page:horizontal {{ background: {p['accent']}; border-radius: 3px; }}
    QSlider::handle:horizontal {{
        background: white; width: 14px; margin: -5px 0; border-radius: 7px;
    }}
    """


def themed_palette(theme_mode="dark"):
    """构造主题调色板，供设置窗口的原生输入控件（QLineEdit/QComboBox/QSpinBox/QCheckBox）
    使用——原生控件在任何 Linux 上都能稳定渲染文字、箭头与勾选，规避 QSS 子控件样式
    在部分 Qt 版本上导致文字消失的问题。"""
    p = _palette(theme_mode)
    pal = QPalette()
    win = QColor(p["panel"][0], p["panel"][1], p["panel"][2])
    txt = QColor(p["text"][0], p["text"][1], p["text"][2])
    base = QColor(p["card"][0], p["card"][1], p["card"][2])
    alt = QColor(max(0, p["card"][0] - 10), max(0, p["card"][1] - 10), max(0, p["card"][2] - 10))
    btn = QColor(p["card"][0], p["card"][1], p["card"][2])
    accent = QColor(p["accent"])
    pal.setColor(QPalette.Window, win)
    pal.setColor(QPalette.WindowText, txt)
    pal.setColor(QPalette.Base, base)
    pal.setColor(QPalette.AlternateBase, alt)
    pal.setColor(QPalette.Text, txt)
    pal.setColor(QPalette.Button, btn)
    pal.setColor(QPalette.ButtonText, txt)
    pal.setColor(QPalette.Highlight, accent)
    pal.setColor(QPalette.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ToolTipBase, base)
    pal.setColor(QPalette.ToolTipText, txt)
    pal.setColor(QPalette.PlaceholderText,
                QColor(min(255, txt.red() + 60), min(255, txt.green() + 60), min(255, txt.blue() + 60)))
    return pal
