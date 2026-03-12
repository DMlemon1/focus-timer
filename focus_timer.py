# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "PyQt6",
# ]
# ///

"""
Focus Timer - 专注计时器
设计风格：Telegram
支持白天/夜间模式切换
"""

import sys
import os
import struct
import wave
import tempfile
import random
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QFrame, QSpinBox,
    QMessageBox, QGraphicsColorizeEffect, QSizeGrip
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QObject, QPointF, QPropertyAnimation, QRectF, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QPainterPath, QBrush, QPalette
import math

# 尝试导入音频播放库
try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_QT_MULTIMEDIA = True
except ImportError:
    HAS_QT_MULTIMEDIA = False

try:
    import simpleaudio as sa
    HAS_SIMPLEAUDIO = True
except ImportError:
    HAS_SIMPLEAUDIO = False


class ThemeManager:
    """主题管理器"""
    # 夜间模式 - Telegram 深色
    DARK_THEME = {
        'name': 'dark',
        'bg_main': '#17212B',
        'bg_secondary': '#0E1621',
        'bg_header': '#242F3D',
        'bg_card': '#1E2C3A',
        'accent': '#2B5278',
        'accent_light': '#4A90D9',
        'accent_green': '#4FAE4E',
        'accent_orange': '#F5A623',
        'text_primary': '#FFFFFF',
        'text_secondary': '#708499',
        'text_link': '#6AB2F2',
        'divider': '#0E1621',
        'bubble_out': '#2B5278',
        'bubble_in': '#182533',
        'button_bg': '#2B5278',
        'button_hover': '#3A6A99',
        'slider': '#4A90D9',
        'progress_bg': '#1A252F',
        'progress_track': '#2B3B4A',
        'glow_color': '#4A90D9',
    }

    # 白天模式 - Telegram 浅色
    LIGHT_THEME = {
        'name': 'light',
        'bg_main': '#FFFFFF',
        'bg_secondary': '#F5F5F5',
        'bg_header': '#FFFFFF',
        'bg_card': '#FFFFFF',
        'accent': '#3390EC',
        'accent_light': '#50A2F0',
        'accent_green': '#4FAE4E',
        'accent_orange': '#F5A623',
        'text_primary': '#000000',
        'text_secondary': '#707579',
        'text_link': '#3390EC',
        'divider': '#E6E6E6',
        'bubble_out': '#EFFDDE',
        'bubble_in': '#FFFFFF',
        'button_bg': '#3390EC',
        'button_hover': '#50A2F0',
        'slider': '#3390EC',
        'progress_bg': '#F0F0F0',
        'progress_track': '#E0E0E0',
        'glow_color': '#3390EC',
    }

    def __init__(self):
        self._theme = self.DARK_THEME.copy()
        self._is_dark = True

    def toggle_theme(self):
        self._is_dark = not self._is_dark
        self._theme = self.DARK_THEME.copy() if self._is_dark else self.LIGHT_THEME.copy()
        return self._theme

    def get_theme(self):
        return self._theme

    def is_dark(self):
        return self._is_dark

    def get(self, key):
        return self._theme.get(key, '#000000')


# 全局主题管理器
theme_manager = ThemeManager()
COLORS = theme_manager.get_theme()


class WhiteNoiseGenerator:
    @staticmethod
    def generate_white_noise(duration_sec=10, sample_rate=44100):
        n_samples = int(duration_sec * sample_rate)
        samples = [int(random.uniform(-1, 1) * 32767) for _ in range(n_samples)]
        return samples, sample_rate

    @staticmethod
    def generate_pink_noise(duration_sec=10, sample_rate=44100):
        n_samples = int(duration_sec * sample_rate)
        samples = []
        b0, b1, b2, b3, b4, b5, b6 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        for _ in range(n_samples):
            white = random.uniform(-1, 1)
            b0 = 0.99886 * b0 + white * 0.0555179
            b1 = 0.99332 * b1 + white * 0.0750759
            b2 = 0.96900 * b2 + white * 0.1538520
            b3 = 0.86650 * b3 + white * 0.3104856
            b4 = 0.55000 * b4 + white * 0.5329522
            b5 = -0.7616 * b5 - white * 0.0168980
            pink = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11
            samples.append(int(pink * 32767))
            b6 = white * 0.115926
        return samples, sample_rate

    @staticmethod
    def generate_brown_noise(duration_sec=10, sample_rate=44100):
        n_samples = int(duration_sec * sample_rate)
        samples = []
        last_out = 0.0
        for _ in range(n_samples):
            white = random.uniform(-1, 1)
            output = (last_out + 0.02 * white) / 1.02
            last_out = output
            samples.append(int(output * 3.5 * 32767))
        return samples, sample_rate

    @staticmethod
    def save_wav(samples, sample_rate, filename):
        with wave.open(filename, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for sample in samples:
                wav_file.writeframes(struct.pack('<h', sample))


class SoundPlayer(QObject):
    def __init__(self):
        super().__init__()
        self.volume = 50
        self.temp_files = []
        self.is_playing = False

        if HAS_QT_MULTIMEDIA:
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            self.use_qt = True
        else:
            self.use_qt = False
            self.play_obj = None

    def set_volume(self, volume):
        self.volume = volume
        if self.use_qt:
            self.audio_output.setVolume(volume / 100.0)

    def play_noise(self, noise_type):
        self.stop()
        if noise_type == "静音":
            return
        if not HAS_QT_MULTIMEDIA:
            return

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        self.temp_files.append(temp_file.name)

        generators = {
            "白噪音": self.generate_white_noise,
            "粉红噪音": self.generate_pink_noise,
            "棕色噪音": self.generate_brown_noise,
            "雨声": self.generate_brown_noise,
            "海浪": self.generate_brown_noise,
            "森林": self.generate_pink_noise,
            "咖啡厅": self.generate_white_noise,
        }

        gen_func = generators.get(noise_type, self.generate_white_noise)
        samples, sr = gen_func(30)
        WhiteNoiseGenerator.save_wav(samples, sr, temp_file.name)

        self.player.setSource(QUrl.fromLocalFile(temp_file.name))
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.audio_output.setVolume(self.volume / 100.0)
        self.player.play()
        self.is_playing = True

    def stop(self):
        self.is_playing = False
        if self.use_qt:
            self.player.stop()

    def cleanup(self):
        self.stop()
        for f in self.temp_files:
            try:
                os.unlink(f)
            except:
                pass
        self.temp_files = []

    @staticmethod
    def generate_white_noise(duration_sec=10, sample_rate=44100):
        return WhiteNoiseGenerator.generate_white_noise(duration_sec, sample_rate)

    @staticmethod
    def generate_pink_noise(duration_sec=10, sample_rate=44100):
        return WhiteNoiseGenerator.generate_pink_noise(duration_sec, sample_rate)

    @staticmethod
    def generate_brown_noise(duration_sec=10, sample_rate=44100):
        return WhiteNoiseGenerator.generate_brown_noise(duration_sec, sample_rate)


class CircularProgress(QWidget):
    """美化版圆形进度条 - 支持渐变和发光效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self._max_progress = 100
        self._glow_opacity = 0.3
        self._animation_progress = 0
        self.setMinimumSize(280, 280)
        self.parent_window = None

        # 动画
        self._glow_animation = QPropertyAnimation(self, b"glowOpacity")
        self._glow_animation.setDuration(1500)
        self._glow_animation.setStartValue(0.2)
        self._glow_animation.setEndValue(0.5)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._glow_animation.setLoopCount(-1)

    def getGlowOpacity(self):
        return self._glow_opacity

    def setGlowOpacity(self, value):
        self._glow_opacity = value
        self.update()

    glowOpacity = pyqtProperty(float, getGlowOpacity, setGlowOpacity)

    def start_glow_animation(self):
        self._glow_animation.start()

    def stop_glow_animation(self):
        self._glow_animation.stop()
        self._glow_opacity = 0.3
        self.update()

    def setProgress(self, value):
        self._progress = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 30

        theme = theme_manager.get_theme()
        is_focus = self.parent_window and self.parent_window.current_mode == 'focus'

        # 外发光效果
        glow_color = QColor(theme['accent_light'] if is_focus else theme['accent_green'])
        glow_color.setAlphaF(self._glow_opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow_color)
        painter.drawEllipse(center_x - radius - 15, center_y - radius - 15,
                           (radius + 15) * 2, (radius + 15) * 2)

        # 内部背景圆 - 渐变
        bg_gradient = QRadialGradient(center_x, center_y, radius)
        if theme_manager.is_dark():
            bg_gradient.setColorAt(0, QColor(theme['bg_card']))
            bg_gradient.setColorAt(1, QColor(theme['bg_secondary']))
        else:
            bg_gradient.setColorAt(0, QColor('#FFFFFF'))
            bg_gradient.setColorAt(1, QColor('#F8F8F8'))
        painter.setBrush(bg_gradient)
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # 进度计算
        progress_ratio = self._progress / self._max_progress if self._max_progress > 0 else 0
        pen_width = 8
        track_radius = radius - 20

        # 背景轨道
        track_gradient = QLinearGradient(center_x - track_radius, center_y,
                                         center_x + track_radius, center_y)
        if theme_manager.is_dark():
            track_gradient.setColorAt(0, QColor('#2A3A4A'))
            track_gradient.setColorAt(1, QColor('#1A2A3A'))
        else:
            track_gradient.setColorAt(0, QColor('#E8E8E8'))
            track_gradient.setColorAt(1, QColor('#D8D8D8'))

        painter.setPen(QPen(QBrush(track_gradient), pen_width + 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_x - track_radius, center_y - track_radius,
                           track_radius * 2, track_radius * 2)

        # 进度弧 - 带渐变
        if progress_ratio > 0:
            # 创建渐变色
            progress_gradient = QLinearGradient(center_x - track_radius, center_y - track_radius,
                                                center_x + track_radius, center_y + track_radius)
            if is_focus:
                progress_gradient.setColorAt(0, QColor(theme['accent_light']))
                progress_gradient.setColorAt(0.5, QColor(theme['accent']))
                progress_gradient.setColorAt(1, QColor(theme['accent_light']))
            else:
                progress_gradient.setColorAt(0, QColor(theme['accent_green']))
                progress_gradient.setColorAt(0.5, QColor('#8BC34A'))
                progress_gradient.setColorAt(1, QColor(theme['accent_green']))

            span_angle = int(-360 * progress_ratio * 16)
            rect = QRectF(center_x - track_radius, center_y - track_radius,
                         track_radius * 2, track_radius * 2)

            # 发光边框
            glow_pen = QPen(QColor(theme['accent_light'] if is_focus else theme['accent_green']))
            glow_pen.setWidth(pen_width + 6)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow_color = QColor(theme['accent_light'] if is_focus else theme['accent_green'])
            glow_color.setAlphaF(0.3)
            glow_pen.setColor(glow_color)
            painter.setPen(glow_pen)
            painter.drawArc(rect, 90 * 16, span_angle)

            # 主进度弧
            painter.setPen(QPen(QBrush(progress_gradient), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(rect, 90 * 16, span_angle)

            # 进度点
            if progress_ratio > 0.02:
                angle = 90 - (360 * progress_ratio)
                end_x = center_x + track_radius * math.cos(math.radians(angle))
                end_y = center_y - track_radius * math.sin(math.radians(angle))

                # 发光点
                dot_glow = QRadialGradient(end_x, end_y, 12)
                dot_color = QColor(theme['accent_light'] if is_focus else theme['accent_green'])
                dot_glow.setColorAt(0, dot_color)
                dot_glow.setColorAt(0.5, QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 100))
                dot_glow.setColorAt(1, QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 0))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(dot_glow)
                painter.drawEllipse(int(end_x - 12), int(end_y - 12), 24, 24)

                # 实心点
                painter.setBrush(QColor('#FFFFFF'))
                painter.drawEllipse(int(end_x - 5), int(end_y - 5), 10, 10)

        painter.end()


class ThemeToggle(QPushButton):
    """主题切换按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_dark = True
        self.update_style()

    def toggle(self):
        self._is_dark = not self._is_dark
        self.update_style()

    def set_dark(self, is_dark):
        self._is_dark = is_dark
        self.update_style()

    def update_style(self):
        theme = theme_manager.get_theme()
        if self._is_dark:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['accent']};
                    border: none;
                    border-radius: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #E0E0E0;
                    border: none;
                    border-radius: 13px;
                }}
            """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆形滑块
        if self._is_dark:
            # 月亮图标位置
            painter.setBrush(QColor('#FFFFFF'))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(28, 3, 20, 20)

            # 绘制星星
            painter.setBrush(QColor('#FFFFFF'))
            star_size = 2
            painter.drawEllipse(8, 7, star_size, star_size)
            painter.drawEllipse(12, 12, star_size, star_size)
            painter.drawEllipse(6, 14, star_size, star_size)
        else:
            # 太阳图标位置
            painter.setBrush(QColor('#FFD700'))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 3, 20, 20)

            # 绘制光线
            painter.setPen(QPen(QColor('#FFD700'), 2))
            center_x, center_y = 12, 13
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = center_x + 12 * math.cos(rad)
                y1 = center_y + 12 * math.sin(rad)
                x2 = center_x + 16 * math.cos(rad)
                y2 = center_y + 16 * math.sin(rad)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))


class TGButton(QPushButton):
    """Telegram 风格按钮"""
    def __init__(self, text, parent=None, style_type='primary'):
        super().__init__(text, parent)
        self.style_type = style_type
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        font = QFont(["Segoe UI", "-apple-system"], 14)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        self.update_style()

    def update_style(self):
        theme = theme_manager.get_theme()

        if self.style_type == 'primary':
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['accent']};
                    color: white;
                    border: none;
                    border-radius: 22px;
                    padding: 10px 24px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {theme['button_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {theme['accent_light']};
                }}
                QPushButton:disabled {{
                    background-color: {theme['bg_header']};
                    color: {theme['text_secondary']};
                }}
            """)
        elif self.style_type == 'secondary':
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme['text_link']};
                    border: none;
                    border-radius: 22px;
                    padding: 10px 24px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {theme['bg_header']};
                }}
                QPushButton:pressed {{
                    background-color: {theme['accent']};
                    color: white;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['bg_header']};
                    color: {theme['text_primary']};
                    border: none;
                    border-radius: 22px;
                    padding: 10px 24px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {theme['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {theme['button_hover']};
                }}
            """)


class TGSpinBox(QSpinBox):
    """Telegram 风格数字输入"""
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont(["Segoe UI", "-apple-system"], 13)
        self.setFont(font)
        self.update_style()

    def update_style(self):
        theme = theme_manager.get_theme()
        self.setStyleSheet(f"""
            QSpinBox {{
                background-color: {theme['bg_header']};
                color: {theme['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                min-width: 70px;
            }}
            QSpinBox:hover {{
                background-color: {theme['accent']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
                background: transparent;
            }}
            QSpinBox::up-arrow {{
                border: none;
                width: 0;
                height: 0;
            }}
            QSpinBox::down-arrow {{
                border: none;
                width: 0;
                height: 0;
            }}
        """)


class TGComboBox(QComboBox):
    """Telegram 风格下拉框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont(["Segoe UI", "-apple-system"], 13)
        self.setFont(font)
        self.update_style()

    def update_style(self):
        theme = theme_manager.get_theme()
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme['bg_header']};
                color: {theme['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                min-width: 80px;
            }}
            QComboBox:hover {{
                background-color: {theme['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['bg_header']};
                color: {theme['text_primary']};
                selection-background-color: {theme['accent']};
                border: none;
                border-radius: 8px;
            }}
        """)


class TGSlider(QSlider):
    """Telegram 风格滑块"""
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.update_style()

    def update_style(self):
        theme = theme_manager.get_theme()
        self.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {theme['bg_header']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {theme['slider']};
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {theme['accent_light']};
            }}
        """)


class FocusTimer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_mode = 'focus'
        self.is_running = False
        self.time_remaining = 25 * 60
        self.total_time = 25 * 60
        self.current_cycle = 1
        self.total_cycles = 4
        self.focus_time = 25
        self.break_time = 5

        self.sound_player = SoundPlayer()
        self.init_ui()
        self.init_timer()

    def init_ui(self):
        self.setWindowTitle("Focus Timer")
        self.setMinimumSize(420, 680)
        self.resize(420, 680)

        self.update_main_style()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题栏
        self.header = QFrame()
        self.header.setStyleSheet(self.get_header_style())
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title_font = QFont(["Segoe UI", "-apple-system"], 20)
        title_font.setWeight(QFont.Weight.Bold)
        self.title = QLabel("Focus Timer")
        self.title.setFont(title_font)
        self.title.setStyleSheet(f"color: {theme_manager.get('text_primary')}; background: transparent;")

        # 主题切换按钮
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.clicked.connect(self.toggle_theme)

        self.cycle_label = QLabel("1/4")
        self.cycle_label.setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent; font-size: 14px;")

        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_toggle)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.cycle_label)
        main_layout.addWidget(self.header)

        # 设置卡片
        self.settings_card = QFrame()
        self.settings_card.setStyleSheet(self.get_card_style())
        settings_layout = QHBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(16, 12, 16, 12)
        settings_layout.setSpacing(12)

        label_style = f"color: {theme_manager.get('text_secondary')}; background: transparent; font-size: 13px;"

        self.focus_spin = TGSpinBox()
        self.focus_spin.setRange(1, 120)
        self.focus_spin.setValue(25)
        self.focus_spin.setSuffix(" 分钟")

        self.break_spin = TGSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(5)
        self.break_spin.setSuffix(" 分钟")

        self.cycles_spin = TGSpinBox()
        self.cycles_spin.setRange(1, 12)
        self.cycles_spin.setValue(4)
        self.cycles_spin.setSuffix(" 次")

        for label_text, spin in [("专注", self.focus_spin), ("休息", self.break_spin), ("循环", self.cycles_spin)]:
            label = QLabel(label_text)
            label.setStyleSheet(label_style)
            settings_layout.addWidget(label)
            settings_layout.addWidget(spin)

        settings_layout.addStretch()
        main_layout.addWidget(self.settings_card)

        # 进度区域
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setSpacing(8)
        progress_layout.setContentsMargins(0, 16, 0, 8)

        # 模式标签
        self.mode_label = QLabel("专注模式")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_label.setStyleSheet(f"color: {theme_manager.get('accent_light')}; font-size: 14px; font-weight: 500;")
        progress_layout.addWidget(self.mode_label)

        # 进度圆环
        self.progress_circle = CircularProgress()
        self.progress_circle.parent_window = self
        progress_layout.addWidget(self.progress_circle, alignment=Qt.AlignmentFlag.AlignCenter)

        # 时间显示
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_font = QFont(["Segoe UI", "-apple-system"], 52)
        time_font.setWeight(QFont.Weight.Light)
        self.time_label.setFont(time_font)
        self.time_label.setStyleSheet(f"color: {theme_manager.get('text_primary')};")
        progress_layout.addWidget(self.time_label)

        main_layout.addWidget(progress_container)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.skip_btn = TGButton("跳过", style_type='secondary')
        self.skip_btn.clicked.connect(self.skip_phase)

        self.start_btn = TGButton("开始专注", style_type='primary')
        self.start_btn.clicked.connect(self.toggle_timer)

        self.reset_btn = TGButton("重置", style_type='default')
        self.reset_btn.clicked.connect(self.reset_timer)

        btn_layout.addWidget(self.skip_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)
        main_layout.addLayout(btn_layout)

        # 白噪音卡片
        self.noise_card = QFrame()
        self.noise_card.setStyleSheet(self.get_card_style())
        noise_layout = QVBoxLayout(self.noise_card)
        noise_layout.setContentsMargins(16, 12, 16, 12)
        noise_layout.setSpacing(10)

        noise_header = QHBoxLayout()
        noise_title = QLabel("背景音效")
        noise_title.setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent; font-size: 13px;")
        noise_header.addWidget(noise_title)
        noise_header.addStretch()
        noise_layout.addLayout(noise_header)

        noise_controls = QHBoxLayout()
        noise_controls.setSpacing(12)

        self.noise_combo = TGComboBox()
        self.noise_combo.addItems(["静音", "雨声", "海浪", "森林", "咖啡厅", "白噪音"])
        self.noise_combo.currentTextChanged.connect(self.on_noise_changed)

        vol_label = QLabel("音量")
        vol_label.setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent;")

        self.volume_slider = TGSlider()
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)

        self.vol_value = QLabel("50%")
        self.vol_value.setStyleSheet(f"color: {theme_manager.get('text_link')}; background: transparent; min-width: 35px;")

        noise_controls.addWidget(self.noise_combo)
        noise_controls.addStretch()
        noise_controls.addWidget(vol_label)
        noise_controls.addWidget(self.volume_slider)
        noise_controls.addWidget(self.vol_value)
        noise_layout.addLayout(noise_controls)

        main_layout.addWidget(self.noise_card)

        # 连接设置变化
        self.focus_spin.valueChanged.connect(self.update_settings)
        self.break_spin.valueChanged.connect(self.update_settings)
        self.cycles_spin.valueChanged.connect(self.update_settings)

    def get_header_style(self):
        theme = theme_manager.get_theme()
        return f"background-color: {theme['bg_header']}; border-radius: 12px;"

    def get_card_style(self):
        theme = theme_manager.get_theme()
        return f"background-color: {theme['bg_header']}; border-radius: 12px;"

    def update_main_style(self):
        theme = theme_manager.get_theme()
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {theme['bg_main']};
                color: {theme['text_primary']};
            }}
        """)

    def toggle_theme(self):
        global COLORS
        COLORS = theme_manager.toggle_theme()
        self.theme_toggle.set_dark(theme_manager.is_dark())

        # 更新所有样式
        self.update_main_style()
        self.header.setStyleSheet(self.get_header_style())
        self.title.setStyleSheet(f"color: {theme_manager.get('text_primary')}; background: transparent;")
        self.cycle_label.setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent; font-size: 14px;")
        self.settings_card.setStyleSheet(self.get_card_style())
        self.noise_card.setStyleSheet(self.get_card_style())

        # 更新按钮
        self.skip_btn.update_style()
        self.start_btn.update_style()
        self.reset_btn.update_style()

        # 更新输入框
        self.focus_spin.update_style()
        self.break_spin.update_style()
        self.cycles_spin.update_style()
        self.noise_combo.update_style()
        self.volume_slider.update_style()

        # 更新模式标签
        self.update_mode()

        # 更新时间标签
        self.time_label.setStyleSheet(f"color: {theme_manager.get('text_primary')};")

        # 更新进度环
        self.progress_circle.update()

        # 更新设置卡片内的标签
        for i in range(self.settings_card.layout().count()):
            item = self.settings_card.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel):
                item.widget().setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent; font-size: 13px;")

        # 更新噪音卡片内的标签
        noise_title = self.noise_card.findChild(QLabel, "")
        for child in self.noise_card.children():
            if isinstance(child, QLabel):
                if child.text() == "背景音效":
                    child.setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent; font-size: 13px;")
                elif child.text() == "音量":
                    child.setStyleSheet(f"color: {theme_manager.get('text_secondary')}; background: transparent;")
                elif '%' in child.text():
                    child.setStyleSheet(f"color: {theme_manager.get('text_link')}; background: transparent; min-width: 35px;")

    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

    def on_noise_changed(self, noise_type):
        self.sound_player.play_noise(noise_type)

    def on_volume_changed(self, volume):
        self.vol_value.setText(f"{volume}%")
        self.sound_player.set_volume(volume)

    def update_settings(self):
        self.focus_time = self.focus_spin.value()
        self.break_time = self.break_spin.value()
        self.total_cycles = self.cycles_spin.value()
        if not self.is_running:
            self.time_remaining = self.focus_time * 60
            self.total_time = self.focus_time * 60
            self.current_cycle = 1
            self.update_display()
            self.cycle_label.setText(f"1/{self.total_cycles}")

    def toggle_timer(self):
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        self.is_running = True
        self.start_btn.setText("暂停")
        self.timer.start(1000)
        self.progress_circle.start_glow_animation()
        self.focus_spin.setEnabled(False)
        self.break_spin.setEnabled(False)
        self.cycles_spin.setEnabled(False)

    def pause_timer(self):
        self.is_running = False
        self.start_btn.setText("继续")
        self.timer.stop()
        self.progress_circle.stop_glow_animation()

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.current_mode = 'focus'
        self.current_cycle = 1
        self.time_remaining = self.focus_time * 60
        self.total_time = self.focus_time * 60
        self.start_btn.setText("开始专注")
        self.progress_circle.stop_glow_animation()
        self.focus_spin.setEnabled(True)
        self.break_spin.setEnabled(True)
        self.cycles_spin.setEnabled(True)
        self.update_display()
        self.update_mode()
        self.cycle_label.setText(f"1/{self.total_cycles}")

    def skip_phase(self):
        self.next_phase()

    def next_phase(self):
        previous_mode = self.current_mode

        if self.current_mode == 'focus':
            self.current_mode = 'break'
            self.time_remaining = self.break_time * 60
            self.total_time = self.break_time * 60
        else:
            self.current_cycle += 1
            if self.current_cycle > self.total_cycles:
                self.complete_all()
                return
            self.current_mode = 'focus'
            self.time_remaining = self.focus_time * 60
            self.total_time = self.focus_time * 60

        self.update_display()
        self.update_mode()
        self.cycle_label.setText(f"{self.current_cycle}/{self.total_cycles}")

        # 弹窗提醒
        self.show_phase_notification(previous_mode)

    def complete_all(self):
        self.timer.stop()
        self.is_running = False
        self.start_btn.setText("开始专注")
        self.progress_circle.stop_glow_animation()
        self.focus_spin.setEnabled(True)
        self.break_spin.setEnabled(True)
        self.cycles_spin.setEnabled(True)
        self.current_cycle = 1
        self.current_mode = 'focus'
        self.time_remaining = self.focus_time * 60
        self.total_time = self.focus_time * 60
        self.update_display()
        self.update_mode()
        self.cycle_label.setText(f"1/{self.total_cycles}")
        QMessageBox.information(self, "完成", "你已完成所有专注循环!")

    def update_timer(self):
        if self.time_remaining > 0:
            self.time_remaining -= 1
            self.update_display()
        else:
            QApplication.beep()
            self.next_phase()

    def update_display(self):
        mins, secs = divmod(self.time_remaining, 60)
        self.time_label.setText(f"{mins:02d}:{secs:02d}")
        progress = int((1 - self.time_remaining / self.total_time) * 100) if self.total_time > 0 else 0
        self.progress_circle.setProgress(progress)

    def update_mode(self):
        theme = theme_manager.get_theme()
        if self.current_mode == 'focus':
            self.mode_label.setText("专注模式")
            self.mode_label.setStyleSheet(f"color: {theme['accent_light']}; font-size: 14px; font-weight: 500;")
        else:
            self.mode_label.setText("休息时间")
            self.mode_label.setStyleSheet(f"color: {theme['accent_green']}; font-size: 14px; font-weight: 500;")

    def show_phase_notification(self, previous_mode):
        """显示阶段切换提醒弹窗"""
        was_running = self.is_running
        if self.is_running:
            self.timer.stop()

        if previous_mode == 'focus':
            msg = QMessageBox(self)
            msg.setWindowTitle("专注完成!")
            msg.setText("做得好! 你完成了一段专注时间")
            msg.setInformativeText(f"现在休息 {self.break_time} 分钟吧~")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {theme_manager.get('bg_header')};
                }}
                QMessageBox QLabel {{
                    color: {theme_manager.get('text_primary')};
                    font-size: 14px;
                }}
                QPushButton {{
                    background-color: {theme_manager.get('accent')};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 24px;
                    font-size: 13px;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.get('button_hover')};
                }}
            """)
            msg.exec()
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("休息结束!")
            msg.setText("休息时间结束了")
            msg.setInformativeText(f"准备开始新的专注 ({self.current_cycle}/{self.total_cycles})")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {theme_manager.get('bg_header')};
                }}
                QMessageBox QLabel {{
                    color: {theme_manager.get('text_primary')};
                    font-size: 14px;
                }}
                QPushButton {{
                    background-color: {theme_manager.get('accent')};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 24px;
                    font-size: 13px;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.get('button_hover')};
                }}
            """)
            msg.exec()

        if was_running:
            self.timer.start(1000)

    def closeEvent(self, event):
        self.sound_player.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont(["Segoe UI", "-apple-system", "Roboto"], 13)
    app.setFont(font)
    window = FocusTimer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
