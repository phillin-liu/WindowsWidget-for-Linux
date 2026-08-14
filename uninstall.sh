#!/usr/bin/env bash
# 卸载小组件。用法：sudo ./uninstall.sh
set -e
[ "$(id -u)" -ne 0 ] && exec sudo -E bash "$0" "$@"

PKG=widget-panel
echo "卸载 $PKG ..."
rm -rf /opt/$PKG
rm -f /usr/bin/$PKG
rm -f /usr/share/applications/$PKG.desktop
for s in 16 22 32 48 64 128 256; do
    rm -f /usr/share/icons/hicolor/${s}x${s}/apps/$PKG.png
done
which update-desktop-database >/dev/null 2>&1 && update-desktop-database -q || true
which gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
echo "已卸载（用户配置保留在 ~/.config/widgetpanel 与 ~/.cache/widgetpanel）"
