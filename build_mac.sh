#!/bin/bash
# Focus Timer Mac M4 打包脚本
# 使用方法: 在 Mac 终端中运行 ./build_mac.sh

set -e

echo "==================================="
echo "Focus Timer - Mac M4 打包工具"
echo "==================================="

# 检查是否安装了必要的工具
if ! command -v python3 &> /dev/null; then
    echo "请先安装 Python 3"
    echo "运行: xcode-select --install && brew install python"
    exit 1
fi

# 安装打包工具
echo "正在安装打包工具..."
pip3 install pyinstaller --quiet --break-system-packages 2>/dev/null || pip3 install pyinstaller --quiet

# 安装应用依赖
echo "正在安装应用依赖..."
pip3 install PyQt6 PyQt6-Qt6 --quiet --break-system-packages 2>/dev/null || pip3 install PyQt6 PyQt6-Qt6 --quiet

# 创建打包配置 (针对 Apple Silicon M4 优化)
cat > focus_timer.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['focus_timer.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Focus Timer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Focus Timer',
)

app = BUNDLE(
    coll,
    name='Focus Timer.app',
    icon=None,
    bundle_identifier='com.focustimer.app',
    info_plist={
        'CFBundleName': 'Focus Timer',
        'CFBundleDisplayName': 'Focus Timer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'LSArchitecturePriority': ['arm64', 'x86_64'],
    },
)
EOF

# 打包应用 (指定 arm64 架构)
echo "正在打包应用 (Apple Silicon M4)..."
pyinstaller focus_timer.spec --clean --noconfirm --target-arch arm64

# 清理临时文件
rm -f focus_timer.spec
rm -rf __pycache__
rm -rf build

# 创建 DMG 安装包
echo "正在创建 DMG 安装包..."
hdiutil create -volname "Focus Timer" \
    -srcfolder "dist/Focus Timer.app" \
    -ov -format UDZO \
    "Focus Timer-M4.dmg" 2>/dev/null || true

# 移动到桌面
DESKTOP="$HOME/Desktop"
if [ -d "$DESKTOP" ]; then
    mv "dist/Focus Timer.app" "$DESKTOP/" 2>/dev/null || true
    if [ -f "Focus Timer-M4.dmg" ]; then
        mv "Focus Timer-M4.dmg" "$DESKTOP/" 2>/dev/null || true
        echo ""
        echo "==================================="
        echo "打包完成!"
        echo "==================================="
        echo ""
        echo "应用位置: $DESKTOP/Focus Timer.app"
        echo "DMG安装包: $DESKTOP/Focus Timer-M4.dmg"
    else
        echo ""
        echo "==================================="
        echo "打包完成!"
        echo "==================================="
        echo ""
        echo "应用位置: $DESKTOP/Focus Timer.app"
    fi
    rm -rf dist
else
    echo ""
    echo "==================================="
    echo "打包完成!"
    echo "==================================="
    echo ""
    echo "应用位置: dist/Focus Timer.app"
    if [ -f "Focus Timer-M4.dmg" ]; then
        echo "DMG安装包: Focus Timer-M4.dmg"
    fi
fi

echo ""
echo "使用方法:"
echo "1. 双击 Focus Timer.app 直接运行"
echo "2. 或将 DMG 文件拷贝到其他 Mac 使用"
echo ""
echo "注意: 首次打开可能需要在"
echo "系统偏好设置 -> 安全性与隐私中允许运行"
echo ""
