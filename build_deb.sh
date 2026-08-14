#!/usr/bin/env bash
# 打包 widget-panel 为 .deb 安装包（手动 staging 法，最稳，不依赖 debhelper）。
set -e

PKG=widget-panel
VERSION=1.0.0
ARCH=all
STAGE=/tmp/${PKG}-deb-${VERSION}

echo "[1/7] 清理旧构建目录"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"

echo "[2/7] 安装 Python 包到 staging"
python3 -m pip install --no-compile --no-warn-script-location \
    --root="$STAGE" --prefix=/usr --no-deps --no-build-isolation .

echo "[3/7] 生成图标"
python3 scripts/generate_icon.py "$STAGE/usr/share/icons/hicolor" || {
    echo "警告: 图标生成失败（需 PyQt5），跳过图标"; }

echo "[4/7] 安装 .desktop 文件"
mkdir -p "$STAGE/usr/share/applications"
cp widget_panel.desktop "$STAGE/usr/share/applications/"

echo "[5/7] 写入 DEBIAN/control"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: ${PKG}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.8), python3-pyqt5, python3-requests, python3-pil
Maintainer: WidgetPanel <2574822018@qq.com>
Description: Linux版 Windows小组件
EOF

# 修正属主（避免打包时报错）
chmod 755 "$STAGE/DEBIAN"
[ -f "$STAGE/DEBIAN/control" ] && chmod 644 "$STAGE/DEBIAN/control"

echo "[6/7] 构建目录结构"
find "$STAGE" -type d -exec chmod 755 {} \; 2>/dev/null || true

echo "[7/7] 打包 .deb"
OUT="${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT"
echo "完成: $(pwd)/$OUT"
echo "安装: sudo dpkg -i $OUT"
echo "如缺依赖: sudo apt-get install -f"
