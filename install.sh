#!/usr/bin/env bash
# 通用安装脚本：自动识别 Linux 发行版，安装系统依赖并把小组件装到 /opt。
# 支持 Debian/Ubuntu/Mint、Fedora/RHEL/Rocky、Arch/Manjaro、openSUSE 等。
# 用法：在项目根目录执行  sudo ./install.sh   （或  ./install.sh  脚本会自动提权）
set -e

PKG=widget-panel
DEST=/opt/$PKG

# ---- 提权 ----
if [ "$(id -u)" -ne 0 ]; then
    exec sudo -E bash "$0" "$@"
fi

# ---- 识别发行版与包管理器 ----
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
    fi
    ID="${ID:-}"
    ID_LIKE="${ID_LIKE:-}"
    case "$ID $ID_LIKE" in
        *debian*|*ubuntu*|*mint*|*pop*|*kali*|*raspbian*)
            echo apt ;;
        *fedora*|*rhel*|*centos*|*rocky*|*alma*|*amzn*)
            echo dnf ;;
        *arch*|*manjaro*|*endeavouros*|*cachyos*|*garuda*)
            echo pacman ;;
        *suse*|*sles*|*opensuse*)
            echo zypper ;;
        *) echo unknown ;;
    esac
}

install_deps() {
    local pm; pm="$(detect_distro)"
    echo "[2/7] 包管理器: $pm  安装系统依赖"
    case "$pm" in
        apt)
            apt-get update -y
            apt-get install -y python3 python3-pyqt5 python3-requests python3-pil \
                              libxcb-cursor0 libxcb-xinerama0
            ;;
        dnf)
            dnf install -y python3 python3-qt5 python3-requests python3-pillow
            ;;
        pacman)
            pacman -Sy --noconfirm python python-pyqt5 python-requests python-pillow
            ;;
        zypper)
            zypper --non-interactive install python3 python3-Qt5 python3-requests \
                                              python3-Pillow
            ;;
        *)
            echo "警告: 未识别的发行版，尝试用 pip 安装依赖（需要 python3-pip）"
            python3 -m pip install --break-system-packages PyQt5 requests Pillow || {
                echo "请手动安装: PyQt5 requests Pillow"; exit 1; }
            ;;
    esac
}

# ---- 主流程 ----
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "[1/7] 识别发行版并准备"
if [ ! -d widget_panel ]; then
    echo "错误: 请在项目根目录运行（需包含 widget_panel/ 目录）"; exit 1
fi

install_deps

echo "[3/7] 安装程序文件到 $DEST"
mkdir -p "$DEST"
cp -r widget_panel "$DEST/"

echo "[4/7] 生成并安装图标"
python3 scripts/generate_icon.py /usr/share/icons/hicolor || \
    echo "警告: 图标生成失败，跳过"

echo "[5/7] 安装启动器 /usr/bin/$PKG"
cat > /usr/bin/$PKG <<'EOF'
#!/bin/sh
export PYTHONPATH=/opt/widget-panel${PYTHONPATH:+:$PYTHONPATH}
exec python3 -m widget_panel.main "$@"
EOF
chmod 755 /usr/bin/$PKG

echo "[6/7] 安装 .desktop 菜单项"
mkdir -p /usr/share/applications
cp -f widget_panel.desktop /usr/share/applications/

echo "[7/7] 刷新桌面与图标缓存"
which update-desktop-database >/dev/null 2>&1 && update-desktop-database -q || true
which gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true

echo ""
echo "安装完成。启动方式："
echo "  命令行:  widget-panel"
echo "  菜单:    应用菜单中搜索 \"小组件\" / Widget Panel"
echo "卸载:      sudo ./uninstall.sh"
