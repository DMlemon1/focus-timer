"""
Focus Timer - 专注计时器
版本: 1.0.1
设计风格：Telegram
支持跟随系统时间自动切换白天/夜间模式
"""

import sys
import os
import struct
import wave
import tempfile
import random
import math
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSpinBox, QMessageBox, QGridLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QObject, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QBrush

# 尝试导入音频播放库
try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class ThemeManager:
    """主题管理器 - 支持跟随系统时间"""
    DARK = {
        'name': 'dark', 'bg_main': '#17212B', 'bg_secondary': '#0E1621',
        'bg_header': '#242F3D', 'accent': '#2B5278', 'accent_light': '#4A90D9',
        'accent_green': '#4FAE4E', 'text_primary': '#FFFFFF', 'text_secondary': '#708499',
        'text_link': '#6AB2F2', 'slider': '#4A90D9', 'button_hover': '#3A6A99',
    }
    LIGHT = {
        'name': 'light', 'bg_main': '#FFFFFF', 'bg_secondary': '#F5F5F5',
        'bg_header': '#FFFFFF', 'accent': '#3390EC', 'accent_light': '#50A2F0',
        'accent_green': '#4FAE4E', 'text_primary': '#000000', 'text_secondary': '#707579',
        'text_link': '#3390EC', 'slider': '#3390EC', 'button_hover': '#50A2F0',
    }

    def __init__(self):
        self._is_dark = True
        self._auto_mode = True
        self._theme = self.DARK.copy()
        self._check_time()

    def _check_time(self):
        if self._auto_mode:
            hour = datetime.now().hour
            self._is_dark = not (6 <= hour < 18)
        self._theme = (self.DARK if self._is_dark else self.LIGHT).copy()

    def toggle_auto(self):
        self._auto_mode = not self._auto_mode
        if self._auto_mode:
            self._check_time()

    def toggle_theme(self):
        self._auto_mode = False
        self._is_dark = not self._is_dark
        self._theme = (self.DARK if self._is_dark else self.LIGHT).copy()

    def update_by_time(self):
        if self._auto_mode:
            old_dark = self._is_dark
            self._check_time()
            return self._is_dark != old_dark
        return False

    def get(self, key): return self._theme.get(key, '#000000')
    def is_dark(self): return self._is_dark
    def is_auto(self): return self._auto_mode
    def get_theme(self): return self._theme


theme_manager = ThemeManager()


class SoundPlayer(QObject):
    """轻量级音频播放器"""
    def __init__(self):
        super().__init__()
        self.volume = 50
        self.temp_file = None
        self.is_playing = False
        if HAS_AUDIO:
            self.player = QMediaPlayer()
            self.audio = QAudioOutput()
            self.player.setAudioOutput(self.audio)

    def set_volume(self, v):
        self.volume = v
        if HAS_AUDIO: self.audio.setVolume(v / 100.0)

    def play_noise(self, noise_type):
        if not HAS_AUDIO or noise_type == "静音":
            self.stop()
            return
        self.stop()

        sr, duration = 22050, 20
        n = int(duration * sr)
        if noise_type in ("雨声", "海浪", "棕色噪音"):
            samples = []
            last = 0.0
            for _ in range(n):
                last = (last + 0.02 * random.uniform(-1, 1)) / 1.02
                samples.append(int(last * 2.5 * 32767))
        elif noise_type in ("森林", "粉红噪音"):
            samples, b = [], [0.0] * 7
            for _ in range(n):
                w = random.uniform(-1, 1)
                b[0] = 0.99886 * b[0] + w * 0.0555179
                b[1] = 0.99332 * b[1] + w * 0.0750759
                b[2] = 0.96900 * b[2] + w * 0.1538520
                b[3] = 0.86650 * b[3] + w * 0.3104856
                samples.append(int((sum(b) + w * 0.5362) * 0.08 * 32767))
        else:
            samples = [int(random.uniform(-1, 1) * 25000) for _ in range(n)]

        self.temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        with wave.open(self.temp_file.name, 'w') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sr)
            f.writeframes(struct.pack(f'<{len(samples)}h', *samples))

        self.player.setSource(QUrl.fromLocalFile(self.temp_file.name))
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.audio.setVolume(self.volume / 100.0)
        self.player.play()
        self.is_playing = True

    def stop(self):
        self.is_playing = False
        if HAS_AUDIO: self.player.stop()

    def cleanup(self):
        self.stop()
        if self.temp_file:
            try: os.unlink(self.temp_file.name)
            except: pass


class ProgressRing(QWidget):
    """轻量级进度环"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self._glow = 0.3
        self.parent_window = None
        self.setMinimumSize(260, 260)
        self._anim = QPropertyAnimation(self, b"glow")
        self._anim.setDuration(1500)
        self._anim.setStartValue(0.2)
        self._anim.setEndValue(0.5)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)

    def getGlow(self): return self._glow
    def setGlow(self, v): self._glow = v; self.update()
    glow = pyqtProperty(float, getGlow, setGlow)

    def setProgress(self, v): self._progress = v; self.update()
    def start_anim(self): self._anim.start()
    def stop_anim(self): self._anim.stop(); self._glow = 0.3; self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2
        r = min(cx, cy) - 25
        focus = self.parent_window and self.parent_window.mode == 'focus'
        accent = theme_manager.get('accent_light' if focus else 'accent_green')

        gc = QColor(accent)
        gc.setAlphaF(self._glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gc)
        p.drawEllipse(cx - r - 12, cy - r - 12, (r + 12) * 2, (r + 12) * 2)

        bg = QRadialGradient(cx, cy, r)
        c1 = theme_manager.get('bg_header') if theme_manager.is_dark() else '#FFFFFF'
        c2 = theme_manager.get('bg_secondary') if theme_manager.is_dark() else '#F5F5F5'
        bg.setColorAt(0, QColor(c1))
        bg.setColorAt(1, QColor(c2))
        p.setBrush(bg)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        tr, pw = r - 18, 6
        tc = '#2A3A4A' if theme_manager.is_dark() else '#E0E0E0'
        p.setPen(QPen(QColor(tc), pw + 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - tr, cy - tr, tr * 2, tr * 2)

        ratio = self._progress / 100
        if ratio > 0:
            g = QLinearGradient(cx - tr, cy - tr, cx + tr, cy + tr)
            g.setColorAt(0, QColor(accent))
            g.setColorAt(1, QColor(theme_manager.get('accent')))
            span = int(-360 * ratio * 16)
            rect = QRectF(cx - tr, cy - tr, tr * 2, tr * 2)
            p.setPen(QPen(QBrush(g), pw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 90 * 16, span)

            if ratio > 0.02:
                angle = 90 - (360 * ratio)
                ex = cx + tr * math.cos(math.radians(angle))
                ey = cy - tr * math.sin(math.radians(angle))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor('#FFFFFF'))
                p.drawEllipse(int(ex - 4), int(ey - 4), 8, 8)
        p.end()


class ThemeBtn(QPushButton):
    """主题切换按钮 - 支持三种状态"""
    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dark = True
        self._auto = True
        self.setToolTip("点击切换主题\n双击跟随系统时间")
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

    def set_state(self, dark, auto):
        self._dark, self._auto = dark, auto
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        if self._auto:
            bg = '#7C4DFF' if theme_manager.is_dark() else '#9575CD'  # 紫色表示自动模式
        else:
            bg = theme_manager.get('accent') if self._dark else '#CCCCCC'
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(0, 0, 50, 26, 13, 13)

        # 滑块和图标
        if self._dark:
            p.setBrush(QColor('#FFFFFF'))
            p.drawEllipse(28, 3, 20, 20)
            if self._auto:
                # 自动模式 - 显示时钟图标
                p.setPen(QPen(QColor('#7C4DFF'), 2))
                p.drawLine(9, 13, 13, 13)
                p.drawLine(9, 13, 9, 9)
            else:
                # 手动夜间 - 星星
                p.setBrush(QColor('#FFFFFF'))
                p.setPen(Qt.PenStyle.NoPen)
                for pos in [(8, 7), (12, 12), (6, 14)]:
                    p.drawEllipse(pos[0], pos[1], 2, 2)
        else:
            p.setBrush(QColor('#FFD700'))
            p.drawEllipse(2, 3, 20, 20)
            if self._auto:
                # 自动模式 - 显示时钟图标
                p.setPen(QPen(QColor('#9575CD'), 2))
                p.drawLine(12, 13, 16, 13)
                p.drawLine(12, 13, 12, 9)
            else:
                # 手动白天 - 光线
                p.setPen(QPen(QColor('#FFD700'), 2))
                for a in range(0, 360, 45):
                    rad = math.radians(a)
                    p.drawLine(int(12 + 11 * math.cos(rad)), int(13 + 11 * math.sin(rad)),
                              int(12 + 15 * math.cos(rad)), int(13 + 15 * math.sin(rad)))


class NoiseTag(QPushButton):
    """白噪音标签按钮 - 彩色风格"""
    NOISE_COLORS = {
        "静音": {"bg": "#607D8B", "active": "#455A64"},
        "雨声": {"bg": "#42A5F5", "active": "#1E88E5"},
        "海浪": {"bg": "#26C6DA", "active": "#00ACC1"},
        "森林": {"bg": "#66BB6A", "active": "#43A047"},
        "咖啡厅": {"bg": "#FFA726", "active": "#FB8C00"},
        "白噪音": {"bg": "#AB47BC", "active": "#8E24AA"},
    }

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._text = text
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont(["Segoe UI", "-apple-system"], 11))
        self.setFixedHeight(32)
        self._update_style()

    def set_active(self, active):
        self._active = active
        self._update_style()

    def _update_style(self):
        colors = self.NOISE_COLORS.get(self._text, {"bg": "#607D8B", "active": "#455A64"})
        bg = colors["active"] if self._active else colors["bg"]
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 16px;
                padding: 6px 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {colors["active"]};
            }}
        """)


class VolumeSlider(QWidget):
    """音量滑块 - 带图标和数值显示"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 50
        self._hover = False
        self._anim_value = 50  # 必须在 QPropertyAnimation 之前初始化
        self.setFixedHeight(40)
        self.setMinimumWidth(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"animValue")

    def getAnimValue(self): return self._anim_value
    def setAnimValue(self, v): self._anim_value = v; self.update()
    animValue = pyqtProperty(float, getAnimValue, setAnimValue)

    def value(self): return self._value

    def setValue(self, v):
        self._value = max(0, min(100, v))
        self.update()

    def mousePressEvent(self, e):
        self._update_from_pos(e.position().x())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_pos(e.position().x())

    def _update_from_pos(self, x):
        ratio = (x - 30) / (self.width() - 60)
        self._value = max(0, min(100, int(ratio * 100)))
        self.update()
        if hasattr(self, '_callback'):
            self._callback(self._value)

    def setCallback(self, cb):
        self._callback = cb

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # 音量图标
        icon_color = theme_manager.get('text_secondary')
        p.setPen(QPen(QColor(icon_color), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # 喇叭
        p.drawLine(8, 14, 8, 26)
        p.drawLine(8, 14, 14, 14)
        p.drawLine(14, 14, 20, 8)
        p.drawLine(20, 8, 20, 32)
        p.drawLine(20, 32, 14, 26)
        p.drawLine(14, 26, 8, 26)

        # 声波
        if self._value > 0:
            for i, alpha in enumerate([100, 60, 30]):
                if self._value > (i + 1) * 25:
                    c = QColor(theme_manager.get('accent_light'))
                    c.setAlpha(alpha)
                    p.setPen(QPen(c, 2))
                    p.drawArc(22 + i * 6, 12, 8 + i * 4, 16, -45 * 16, 90 * 16)

        # 滑块轨道
        track_x, track_w = 35, w - 70
        track_color = theme_manager.get('bg_header')
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(track_color))
        p.drawRoundedRect(track_x, 17, track_w, 6, 3, 3)

        # 已填充部分
        fill_w = int(track_w * self._value / 100)
        if fill_w > 0:
            gradient = QLinearGradient(track_x, 0, track_x + track_w, 0)
            gradient.setColorAt(0, QColor(theme_manager.get('accent')))
            gradient.setColorAt(1, QColor(theme_manager.get('accent_light')))
            p.setBrush(gradient)
            p.drawRoundedRect(track_x, 17, fill_w, 6, 3, 3)

        # 滑块手柄
        handle_x = track_x + fill_w
        handle_color = QColor(theme_manager.get('accent_light'))
        if self._hover:
            handle_color = QColor(theme_manager.get('slider'))
        p.setBrush(handle_color)
        p.drawEllipse(handle_x - 8, 12, 16, 16)

        # 数值显示
        p.setPen(QColor(theme_manager.get('text_primary')))
        p.setFont(QFont(["Segoe UI"], 10, QFont.Weight.Medium))
        p.drawText(w - 28, 24, f"{self._value}%")


class Btn(QPushButton):
    """按钮组件"""
    def __init__(self, text, style='primary', parent=None):
        super().__init__(text, parent)
        self._style = style
        self.setMinimumHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont(["Segoe UI", "-apple-system"], 13))
        self._update()

    def _update(self):
        t = theme_manager.get_theme()
        if self._style == 'primary':
            self.setStyleSheet(f"QPushButton{{background:{t['accent']};color:white;border:none;border-radius:21px;padding:8px 20px;}}QPushButton:hover{{background:{t['button_hover']};}}QPushButton:disabled{{background:{t['bg_header']};color:{t['text_secondary']};}}")
        elif self._style == 'secondary':
            self.setStyleSheet(f"QPushButton{{background:transparent;color:{t['text_link']};border:none;border-radius:21px;padding:8px 20px;}}QPushButton:hover{{background:{t['bg_header']};}}")
        else:
            self.setStyleSheet(f"QPushButton{{background:{t['bg_header']};color:{t['text_primary']};border:none;border-radius:21px;padding:8px 20px;}}QPushButton:hover{{background:{t['accent']};color:white;}}")


class Spin(QSpinBox):
    """数字输入"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(["Segoe UI"], 12))
        self._update()

    def _update(self):
        t = theme_manager.get_theme()
        self.setStyleSheet(f"QSpinBox{{background:{t['bg_header']};color:{t['text_primary']};border:none;border-radius:6px;padding:6px 10px;min-width:60px;}}QSpinBox:hover{{background:{t['accent']};}}QSpinBox::up-button,QSpinBox::down-button{{width:16px;background:transparent;}}")


class FocusTimer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mode = 'focus'
        self.running = False
        self.remaining = 25 * 60
        self.total = 25 * 60
        self.cycle = 1
        self.cycles = 4
        self.focus_time = 25
        self.break_time = 5
        self.current_noise = "静音"
        self.sound = SoundPlayer()
        self._ui()
        self._timer()

    def _ui(self):
        self.setWindowTitle("Focus Timer")
        self.setMinimumSize(400, 700)
        self.resize(400, 700)
        self._style()

        cw = QWidget()
        self.setCentralWidget(cw)
        lo = QVBoxLayout(cw)
        lo.setContentsMargins(16, 16, 16, 16)
        lo.setSpacing(12)

        # 标题栏
        hdr = QFrame()
        hdr.setStyleSheet(f"background:{theme_manager.get('bg_header')};border-radius:10px;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 10, 12, 10)
        self.title = QLabel("Focus Timer")
        self.title.setFont(QFont(["Segoe UI", "-apple-system"], 18, QFont.Weight.Bold))
        self.title.setStyleSheet(f"color:{theme_manager.get('text_primary')};background:transparent;")

        # 主题切换
        self.theme_btn = ThemeBtn()
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.double_clicked.connect(self._toggle_auto)

        # 自动模式标签
        self.auto_lbl = QLabel("自动")
        self.auto_lbl.setStyleSheet(f"color:{theme_manager.get('text_secondary')};background:transparent;font-size:10px;padding:2px 6px;border-radius:4px;")
        self.auto_lbl.setVisible(theme_manager.is_auto())

        self.cycle_lbl = QLabel("1/4")
        self.cycle_lbl.setStyleSheet(f"color:{theme_manager.get('text_secondary')};background:transparent;font-size:13px;")
        hl.addWidget(self.title)
        hl.addStretch()
        hl.addWidget(self.auto_lbl)
        hl.addWidget(self.theme_btn)
        hl.addSpacing(8)
        hl.addWidget(self.cycle_lbl)
        lo.addWidget(hdr)

        # 设置卡片
        set_card = QFrame()
        set_card.setStyleSheet(f"background:{theme_manager.get('bg_header')};border-radius:10px;")
        sl = QHBoxLayout(set_card)
        sl.setContentsMargins(12, 10, 12, 10)
        sl.setSpacing(10)

        self.focus_sp = Spin()
        self.focus_sp.setRange(1, 120)
        self.focus_sp.setValue(25)
        self.focus_sp.setSuffix(" 分钟")
        self.break_sp = Spin()
        self.break_sp.setRange(1, 60)
        self.break_sp.setValue(5)
        self.break_sp.setSuffix(" 分钟")
        self.cycle_sp = Spin()
        self.cycle_sp.setRange(1, 12)
        self.cycle_sp.setValue(4)
        self.cycle_sp.setSuffix(" 次")

        for txt, sp in [("专注", self.focus_sp), ("休息", self.break_sp), ("循环", self.cycle_sp)]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color:{theme_manager.get('text_secondary')};background:transparent;font-size:12px;")
            sl.addWidget(lbl)
            sl.addWidget(sp)
        sl.addStretch()
        lo.addWidget(set_card)

        # 进度区域
        pw = QWidget()
        pl = QVBoxLayout(pw)
        pl.setSpacing(6)
        pl.setContentsMargins(0, 12, 0, 6)

        self.mode_lbl = QLabel("专注模式")
        self.mode_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_lbl.setStyleSheet(f"color:{theme_manager.get('accent_light')};font-size:13px;font-weight:500;")
        pl.addWidget(self.mode_lbl)

        self.ring = ProgressRing()
        self.ring.parent_window = self
        pl.addWidget(self.ring, alignment=Qt.AlignmentFlag.AlignCenter)

        self.time_lbl = QLabel("25:00")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_lbl.setFont(QFont(["Segoe UI", "-apple-system"], 48, QFont.Weight.Light))
        self.time_lbl.setStyleSheet(f"color:{theme_manager.get('text_primary')};")
        pl.addWidget(self.time_lbl)
        lo.addWidget(pw)

        # 控制按钮
        bl = QHBoxLayout()
        bl.setSpacing(10)
        self.skip_btn = Btn("跳过", "secondary")
        self.skip_btn.clicked.connect(self._skip)
        self.start_btn = Btn("开始专注", "primary")
        self.start_btn.clicked.connect(self._toggle)
        self.reset_btn = Btn("重置", "default")
        self.reset_btn.clicked.connect(self._reset)
        bl.addWidget(self.skip_btn)
        bl.addWidget(self.start_btn)
        bl.addWidget(self.reset_btn)
        lo.addLayout(bl)

        # 白噪音卡片
        noise_card = QFrame()
        noise_card.setStyleSheet(f"background:{theme_manager.get('bg_header')};border-radius:10px;")
        nl = QVBoxLayout(noise_card)
        nl.setContentsMargins(12, 12, 12, 12)
        nl.setSpacing(12)

        # 标题行
        nt = QLabel("背景音效")
        nt.setStyleSheet(f"color:{theme_manager.get('text_secondary')};background:transparent;font-size:12px;")
        nl.addWidget(nt)

        # 白噪音标签 - 网格布局
        noise_grid = QGridLayout()
        noise_grid.setSpacing(8)

        self.noise_tags = []
        noises = ["静音", "雨声", "海浪", "森林", "咖啡厅", "白噪音"]
        for i, noise in enumerate(noises):
            tag = NoiseTag(noise)
            tag.clicked.connect(lambda checked, n=noise: self._select_noise(n))
            if noise == "静音":
                tag.set_active(True)
            row, col = i // 3, i % 3
            noise_grid.addWidget(tag, row, col)
            self.noise_tags.append(tag)

        nl.addLayout(noise_grid)

        # 音量控制
        vol_row = QHBoxLayout()
        vol_row.setSpacing(8)

        self.vol_slider = VolumeSlider()
        self.vol_slider.setCallback(self.sound.set_volume)
        self.vol_slider.setValue(50)

        vol_row.addWidget(self.vol_slider)
        nl.addLayout(vol_row)

        lo.addWidget(noise_card)

        # 信号连接
        self.focus_sp.valueChanged.connect(self._update_settings)
        self.break_sp.valueChanged.connect(self._update_settings)
        self.cycle_sp.valueChanged.connect(self._update_settings)

    def _select_noise(self, noise):
        self.current_noise = noise
        for tag in self.noise_tags:
            tag.set_active(tag._text == noise)
        self.sound.play_noise(noise)

    def _toggle_auto(self):
        theme_manager.toggle_auto()
        self.auto_lbl.setVisible(theme_manager.is_auto())
        self.theme_btn.set_state(theme_manager.is_dark(), theme_manager.is_auto())
        self._refresh_theme()

    def _style(self):
        t = theme_manager.get_theme()
        self.setStyleSheet(f"QMainWindow,QWidget{{background:{t['bg_main']};color:{t['text_primary']};}}")

    def _timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.theme_timer = QTimer()
        self.theme_timer.timeout.connect(self._check_theme)
        self.theme_timer.start(60000)

    def _check_theme(self):
        if theme_manager.update_by_time():
            self._refresh_theme()

    def _toggle_theme(self):
        theme_manager.toggle_theme()
        self.auto_lbl.setVisible(theme_manager.is_auto())
        self._refresh_theme()

    def _refresh_theme(self):
        self._style()
        self.theme_btn.set_state(theme_manager.is_dark(), theme_manager.is_auto())
        self.title.setStyleSheet(f"color:{theme_manager.get('text_primary')};background:transparent;")
        self.cycle_lbl.setStyleSheet(f"color:{theme_manager.get('text_secondary')};background:transparent;font-size:13px;")
        self.time_lbl.setStyleSheet(f"color:{theme_manager.get('text_primary')};")
        self.auto_lbl.setStyleSheet(f"color:{theme_manager.get('text_secondary')};background:transparent;font-size:10px;padding:2px 6px;border-radius:4px;")
        self._update_mode()
        self.ring.update()

        for card in self.centralWidget().findChildren(QFrame):
            card.setStyleSheet(f"background:{theme_manager.get('bg_header')};border-radius:10px;")

        for w in [self.focus_sp, self.break_sp, self.cycle_sp]:
            w._update()
        for w in [self.skip_btn, self.start_btn, self.reset_btn]:
            w._update()
        for tag in self.noise_tags:
            tag._update_style()
        self.vol_slider.update()

    def _update_settings(self):
        self.focus_time = self.focus_sp.value()
        self.break_time = self.break_sp.value()
        self.cycles = self.cycle_sp.value()
        if not self.running:
            self.remaining = self.focus_time * 60
            self.total = self.focus_time * 60
            self.cycle = 1
            self._display()
            self.cycle_lbl.setText(f"1/{self.cycles}")

    def _toggle(self):
        if self.running:
            self._pause()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.start_btn.setText("暂停")
        self.timer.start(1000)
        self.ring.start_anim()
        self.focus_sp.setEnabled(False)
        self.break_sp.setEnabled(False)
        self.cycle_sp.setEnabled(False)

    def _pause(self):
        self.running = False
        self.start_btn.setText("继续")
        self.timer.stop()
        self.ring.stop_anim()

    def _reset(self):
        self.timer.stop()
        self.running = False
        self.mode = 'focus'
        self.cycle = 1
        self.remaining = self.focus_time * 60
        self.total = self.focus_time * 60
        self.start_btn.setText("开始专注")
        self.ring.stop_anim()
        self.focus_sp.setEnabled(True)
        self.break_sp.setEnabled(True)
        self.cycle_sp.setEnabled(True)
        self._display()
        self._update_mode()
        self.cycle_lbl.setText(f"1/{self.cycles}")

    def _skip(self):
        self._next()

    def _next(self):
        prev = self.mode
        if self.mode == 'focus':
            self.mode = 'break'
            self.remaining = self.break_time * 60
            self.total = self.break_time * 60
        else:
            self.cycle += 1
            if self.cycle > self.cycles:
                self._complete()
                return
            self.mode = 'focus'
            self.remaining = self.focus_time * 60
            self.total = self.focus_time * 60
        self._display()
        self._update_mode()
        self.cycle_lbl.setText(f"{self.cycle}/{self.cycles}")
        self._notify(prev)

    def _complete(self):
        self.timer.stop()
        self.running = False
        self.start_btn.setText("开始专注")
        self.ring.stop_anim()
        self.focus_sp.setEnabled(True)
        self.break_sp.setEnabled(True)
        self.cycle_sp.setEnabled(True)
        self.cycle = 1
        self.mode = 'focus'
        self.remaining = self.focus_time * 60
        self.total = self.focus_time * 60
        self._display()
        self._update_mode()
        self.cycle_lbl.setText(f"1/{self.cycles}")
        QMessageBox.information(self, "完成", "你已完成所有专注循环!")

    def _tick(self):
        if self.remaining > 0:
            self.remaining -= 1
            self._display()
        else:
            QApplication.beep()
            self._next()

    def _display(self):
        m, s = divmod(self.remaining, 60)
        self.time_lbl.setText(f"{m:02d}:{s:02d}")
        self.ring.setProgress(int((1 - self.remaining / self.total) * 100) if self.total > 0 else 0)

    def _update_mode(self):
        if self.mode == 'focus':
            self.mode_lbl.setText("专注模式")
            self.mode_lbl.setStyleSheet(f"color:{theme_manager.get('accent_light')};font-size:13px;font-weight:500;")
        else:
            self.mode_lbl.setText("休息时间")
            self.mode_lbl.setStyleSheet(f"color:{theme_manager.get('accent_green')};font-size:13px;font-weight:500;")

    def _notify(self, prev):
        was_run = self.running
        if self.running: self.timer.stop()

        t = theme_manager.get_theme()
        style = f"QMessageBox{{background:{t['bg_header']};}}QLabel{{color:{t['text_primary']};font-size:13px;}}QPushButton{{background:{t['accent']};color:white;border:none;border-radius:6px;padding:6px 20px;min-width:70px;}}"

        if prev == 'focus':
            msg = QMessageBox(self)
            msg.setWindowTitle("专注完成!")
            msg.setText("做得好! 你完成了一段专注时间")
            msg.setInformativeText(f"现在休息 {self.break_time} 分钟吧~")
            msg.setStyleSheet(style)
            msg.exec()
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("休息结束!")
            msg.setText("休息时间结束了")
            msg.setInformativeText(f"准备开始新的专注 ({self.cycle}/{self.cycles})")
            msg.setStyleSheet(style)
            msg.exec()

        if was_run: self.timer.start(1000)

    def closeEvent(self, e):
        self.sound.cleanup()
        e.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont(["Segoe UI", "-apple-system"], 12))
    w = FocusTimer()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
