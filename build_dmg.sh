#!/bin/bash
# Focus Timer DMG 打包脚本 (优化版 - 支持 M4/M系列芯片)
# 使用方法: 在 Mac 终端中运行 ./build_dmg.sh

set -e

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     🎨 Focus Timer DMG 打包工具        ║"
echo "║        专为 M 系列芯片优化              ║"
echo "╚════════════════════════════════════════╝"
echo ""

APP_NAME="Focus Timer"
VERSION="1.0.0"
DMG_NAME="FocusTimer-${VERSION}-M4"

# 检测芯片架构
ARCH=$(uname -m)
echo "🖥️  检测到芯片架构: $ARCH"

# 检查是否安装了必要的工具
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装 Python 3"
    echo ""
    echo "安装方法:"
    echo "  方法1: 安装 Xcode 命令行工具"
    echo "         xcode-select --install"
    echo ""
    echo "  方法2: 使用 Homebrew"
    echo "         /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "         brew install python3"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"

# 安装 uv (更快的包管理器)
if ! command -v uv &> /dev/null; then
    echo "📦 安装 uv 包管理器..."
    pip3 install uv --quiet 2>/dev/null || pip install uv --quiet
fi

# 安装打包工具
echo "📦 安装打包工具..."
pip3 install pyinstaller --quiet 2>/dev/null || pip install pyinstaller --quiet

# 安装应用依赖
echo "📦 安装应用依赖 (PyQt6)..."
pip3 install PyQt6 --quiet 2>/dev/null || pip install PyQt6 --quiet

# 尝试安装 QtMultimedia (可选)
echo "📦 安装音频支持 (可选)..."
pip3 install PyQt6-QtMultimedia --quiet 2>/dev/null || echo "   ⚠️  QtMultimedia 不可用，白噪音功能将被禁用"

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
rm -rf build dist *.spec __pycache__ 2>/dev/null

# 创建打包配置
echo "📝 创建打包配置..."
cat > focus_timer.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集所有必要的模块
hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
]

# 尝试添加 QtMultimedia
try:
    import PyQt6.QtMultimedia
    hiddenimports.extend([
        'PyQt6.QtMultimedia',
    ])
except ImportError:
    pass

a = Analysis(
    ['focus_timer.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
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
    target_arch='arm64',  # 针对 M 系列芯片
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
        'LSApplicationCategoryType': 'public.app-category.productivity',
        'CFBundleDocumentTypes': [],
    },
)
EOF

# 打包应用
echo "🔨 正在打包应用 (针对 $ARCH 优化)..."
pyinstaller focus_timer.spec --clean --noconfirm

# 清理 spec 文件
rm -f focus_timer.spec

# 创建 DMG
echo "📀 正在创建 DMG 安装包..."

# 创建临时目录用于 DMG
DMG_TEMP="dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# 创建背景图片目录
mkdir -p "$DMG_TEMP/.background"

# 创建简单的背景
cat > "$DMG_TEMP/.background/background.png.inst" << 'BGEOF'
# 这是一个占位符，实际背景会在下面设置
BGEOF

# 复制应用到临时目录
cp -R "dist/Focus Timer.app" "$DMG_TEMP/"

# 创建应用程序文件夹的符号链接
ln -s /Applications "$DMG_TEMP/Applications"

# 创建 DMG
echo "📀 创建 DMG 磁盘镜像..."
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    -imagekey zlib-level=9 \
    "${DMG_NAME}.dmg"

# 清理临时文件
rm -rf "$DMG_TEMP"
rm -rf build dist

# 移动 DMG 到桌面
DESKTOP="$HOME/Desktop"
if [ -d "$DESKTOP" ]; then
    mv "${DMG_NAME}.dmg" "$DESKTOP/" 2>/dev/null || true
    FINAL_PATH="$DESKTOP/${DMG_NAME}.dmg"
else
    FINAL_PATH="${DMG_NAME}.dmg"
fi

# 获取文件大小
SIZE=$(du -h "$FINAL_PATH" 2>/dev/null | cut -f1)

echo ""
echo "╔════════════════════════════════════════╗"
echo "║            ✅ 打包完成！                ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "📀 DMG 文件: $FINAL_PATH"
echo "📦 文件大小: $SIZE"
echo "🖥️  目标架构: $ARCH (M 系列芯片)"
echo ""
echo "📋 安装说明:"
echo "   1. 双击打开 DMG 文件"
echo "   2. 将 Focus Timer 拖拽到 Applications 文件夹"
echo "   3. 从启动台打开应用"
echo ""
echo "⚠️  首次打开可能需要:"
echo "   右键点击应用 → 打开 → 点击「打开」按钮"
echo "   或在「系统偏好设置 → 安全性与隐私」中允许运行"
echo ""
echo "🎉 感谢使用 Focus Timer!"
echo ""
