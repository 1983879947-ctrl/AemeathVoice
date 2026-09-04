"""爱弥斯语音 GUI - 消息气泡组件

微信风格：
- 用户消息：右侧，绿色气泡 (#95EC69)
- 爱弥斯消息：左侧，白色气泡，带语音消息卡片（播放按钮 + 时长 + 进度条）
- 加载中：左侧，灰色气泡 + 加载动画
"""
from typing import Optional

from PySide6.QtCore import (
    Qt, QSize, QTimer, QRectF, QPointF, Signal, QPropertyAnimation,
    QEasingCurve, Property,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics,
    QLinearGradient, QRadialGradient,
)
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy, QProgressBar, QFrame,
    QSpacerItem,
)

from . import styles


class AvatarWidget(QWidget):
    """圆形头像（用 QPainter 画，简单可靠）"""

    def __init__(self, text: str, bg_color: str, parent=None):
        super().__init__(parent)
        self.text = text
        self.bg_color = QColor(bg_color)
        self.setFixedSize(styles.AVATAR_SIZE, styles.AVATAR_SIZE)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 圆形背景渐变
        gradient = QRadialGradient(
            QPointF(self.width() / 2 - 4, self.height() / 2 - 4),
            self.width() / 1.5,
        )
        gradient.setColorAt(0, self.bg_color.lighter(110))
        gradient.setColorAt(1, self.bg_color)

        p.setBrush(QBrush(gradient))
        p.setPen(QPen(self.bg_color.darker(115), 1.5))
        p.drawEllipse(1, 1, self.width() - 2, self.height() - 2)

        # 文字
        font = QFont()
        font.setFamily(styles.FONT_FAMILY.split(",")[0].strip())
        font.setPixelSize(18)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)


class VoiceMessageCard(QWidget):
    """语音消息卡片：播放按钮 + 时长 + 进度条

    signal play_clicked(str)  点击播放时发出（参数：音频路径）
    """

    play_clicked = Signal(str)

    def __init__(self, audio_path: str, duration: float = 0.0, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.duration = duration  # 秒

        self._is_playing = False
        self._progress = 0.0  # 0.0 - 1.0
        self._anim_timer: Optional[QTimer] = None

        self.setFixedHeight(48)
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)

        self.setStyleSheet("background: transparent;")

    def set_duration(self, seconds: float):
        self.duration = seconds
        self.update()

    def set_progress(self, pct: float):
        """0.0 - 1.0"""
        self._progress = max(0.0, min(1.0, pct))
        self.update()

    def set_playing(self, playing: bool):
        self._is_playing = playing
        if not playing:
            self._progress = 0.0
            if self._anim_timer:
                self._anim_timer.stop()
                self._anim_timer = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_clicked.emit(self.audio_path)

    def enterEvent(self, event):
        if not self._is_playing:
            self.update()

    def leaveEvent(self, event):
        if not self._is_playing:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        # 播放按钮圆形（左侧）
        btn_size = 36
        btn_x = 6
        btn_y = (h - btn_size) // 2

        # 按钮背景（hover 时略亮）
        btn_color = QColor(styles.COLOR_SEND_BUTTON)
        if self.underMouse() and not self._is_playing:
            btn_color = btn_color.lighter(110)
        p.setBrush(QBrush(btn_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(btn_x, btn_y, btn_size, btn_size)

        # 播放图标（三角）或 暂停图标（两条竖线）
        if self._is_playing:
            # 暂停图标
            p.setPen(QPen(QColor("#FFFFFF"), 3, Qt.PenStyle.SolidLine, Qt.PenStyle.RoundCap))
            cx = btn_x + btn_size // 2
            cy = btn_y + btn_size // 2
            p.drawLine(int(cx - 4), int(cy - 6), int(cx - 4), int(cy + 6))
            p.drawLine(int(cx + 4), int(cy - 6), int(cx + 4), int(cy + 6))
        else:
            # 播放图标（圆角三角）
            triangle = QPainterPath()
            tri_x = btn_x + 12
            tri_y = btn_y + 10
            triangle.moveTo(tri_x, tri_y)
            triangle.lineTo(tri_x + 14, btn_y + btn_size // 2)
            triangle.lineTo(tri_x, btn_y + btn_size - 10)
            triangle.closeSubpath()
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawPath(triangle)

        # 时长文字（按钮右侧）
        if self._is_playing and self.duration > 0:
            current = self._progress * self.duration
            text = f"{int(current)}''"
        else:
            text = f"{int(self.duration)}''" if self.duration > 0 else "--''"
        font = QFont()
        font.setFamily(styles.FONT_FAMILY.split(",")[0].strip())
        font.setPixelSize(13)
        p.setFont(font)
        p.setPen(QColor(styles.COLOR_TEXT_PRIMARY))
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(text)
        text_x = btn_x + btn_size + 10
        text_y = btn_y + btn_size // 2 + fm.ascent() // 2
        p.drawText(int(text_x), int(text_y), text)

        # 进度条（最下方一条）
        bar_x = btn_x + btn_size + 10
        bar_y = btn_y + btn_size - 4
        bar_w = w - bar_x - 8
        bar_h = 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(styles.COLOR_PROGRESS_BAR_BG)))
        p.drawRoundedRect(int(bar_x), int(bar_y), int(bar_w), bar_h, 1, 1)
        if self._progress > 0:
            p.setBrush(QBrush(QColor(styles.COLOR_PROGRESS_BAR_FG)))
            p.drawRoundedRect(
                int(bar_x), int(bar_y),
                int(bar_w * self._progress), bar_h, 1, 1,
            )


class BotTypingIndicator(QWidget):
    """爱弥斯"正在说话..."动画（三个跳动的小圆点）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setMinimumWidth(80)
        self._phase = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(120)
        self.setStyleSheet("background: transparent;")

    def _tick(self):
        self._phase = (self._phase + 1) % 9
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx = w // 2 - 8
        cy = h // 2

        for i in range(3):
            # 每个圆点错相位
            offset = (self._phase + i * 3) % 9
            # 0-3 上升，3-6 下降，6-9 平
            if offset < 3:
                dy = -2 - offset
            elif offset < 6:
                dy = -5 + (offset - 3)
            else:
                dy = -2
            x = cx + i * 10
            y = cy + dy
            color = QColor("#888888")
            color.setAlpha(180 + (offset % 3) * 20)
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(x, y, 6, 6)


class MessageBubble(QWidget):
    """单条消息气泡（基类）"""

    play_requested = Signal(str)  # 请求播放某个音频路径

    def __init__(self, side: str, parent=None):
        """side: 'left' = 爱弥斯，'right' = 用户"""
        super().__init__(parent)
        self.side = side
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(6)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)


class UserTextBubble(MessageBubble):
    """用户文本气泡（右侧、绿色）"""

    def __init__(self, text: str, parent=None):
        super().__init__("right", parent)
        self.text = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 左侧 spacer（推到右边）
        layout.addItem(QSpacerItem(40, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # 文本气泡
        self._bubble = QLabel(self._format_text(text))
        self._bubble.setWordWrap(True)
        self._bubble.setMaximumWidth(420)
        self._bubble.setMinimumHeight(36)
        self._bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bubble.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._set_bubble_style()
        self.add_shadow_to(self._bubble)
        layout.addWidget(self._bubble, 0, Qt.AlignmentFlag.AlignVCenter)

        # 头像
        avatar = AvatarWidget("我", styles.COLOR_USER_AVATAR_BG)
        layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

    def _format_text(self, text: str) -> str:
        return text.replace("\n", "\n")

    def _set_bubble_style(self):
        self._bubble.setStyleSheet(f"""
            QLabel {{
                background-color: {styles.COLOR_USER_BUBBLE};
                color: {styles.COLOR_TEXT_PRIMARY};
                border-radius: {styles.BUBBLE_RADIUS}px;
                padding: 10px 14px;
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_NORMAL}px;
            }}
        """)

    def add_shadow_to(self, widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(4)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 25))
        widget.setGraphicsEffect(shadow)


class BotVoiceBubble(MessageBubble):
    """爱弥斯语音消息气泡（左侧、白色 + 语音卡片）"""

    def __init__(self, audio_path: str, duration: float, status: str = "ready", parent=None):
        """status: 'generating' | 'ready' | 'failed'"""
        super().__init__("left", parent)
        self.audio_path = audio_path
        self.duration = duration
        self.status = status

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 头像
        avatar = AvatarWidget("爱", styles.COLOR_AEMEATH_AVATAR_BG)
        layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

        # 内容容器（语音卡片 + 状态标签）
        content = QVBoxLayout()
        content.setSpacing(2)
        content.setContentsMargins(0, 0, 0, 0)

        # 气泡
        self._bubble = QFrame()
        self._bubble.setMinimumHeight(48)
        self._set_bubble_style()
        bubble_layout = QHBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(8, 6, 12, 6)
        bubble_layout.setSpacing(0)

        if status == "generating":
            # 加载中：显示进度条
            self._progress_label = QLabel("爱弥斯正在说话...")
            self._progress_label.setStyleSheet(f"""
                color: {styles.COLOR_TEXT_SECONDARY};
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_SMALL}px;
                background: transparent;
            """)
            self._progress_label.setMinimumWidth(180)
            bubble_layout.addWidget(self._progress_label)

            self._progress_bar = QProgressBar()
            self._progress_bar.setMaximum(100)
            self._progress_bar.setValue(0)
            self._progress_bar.setTextVisible(False)
            self._progress_bar.setFixedHeight(4)
            self._progress_bar.setMaximumWidth(180)
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {styles.COLOR_PROGRESS_BAR_BG};
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {styles.COLOR_PROGRESS_BAR_FG};
                    border-radius: 2px;
                }}
            """)
            bubble_layout.addWidget(self._progress_bar)
            bubble_layout.addItem(QSpacerItem(8, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        elif status == "failed":
            err_label = QLabel("⚠️ 合成失败")
            err_label.setStyleSheet(f"""
                color: #FF4444;
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_SMALL}px;
                background: transparent;
            """)
            bubble_layout.addWidget(err_label)
        else:
            # ready: 显示语音卡片
            self._voice_card = VoiceMessageCard(audio_path, duration)
            self._voice_card.play_clicked.connect(self._on_play_clicked)
            bubble_layout.addWidget(self._voice_card)

        content.addWidget(self._bubble)
        content.addItem(QSpacerItem(1, 4, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addLayout(content)

        # 右侧 spacer（推到左边）
        layout.addItem(QSpacerItem(40, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.add_shadow_to(self._bubble)

    def _set_bubble_style(self):
        self._bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_BOT_BUBBLE};
                border: 1px solid {styles.COLOR_BOT_BUBBLE_BORDER};
                border-radius: {styles.BUBBLE_RADIUS}px;
            }}
        """)

    def add_shadow_to(self, widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(4)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 25))
        widget.setGraphicsEffect(shadow)

    def update_progress(self, percent: float, message: str = ""):
        """更新进度（仅在 status == 'generating' 时有效）"""
        if self.status != "generating":
            return
        if hasattr(self, "_progress_bar"):
            self._progress_bar.setValue(int(percent))
        if message and hasattr(self, "_progress_label"):
            self._progress_label.setText(message)

    def mark_ready(self, audio_path: str, duration: float):
        """标记为完成状态"""
        self.audio_path = audio_path
        self.duration = duration
        self.status = "ready"

        # 清空当前 bubble_layout
        old_layout = self._bubble.layout()
        while old_layout.count():
            item = old_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 移除旧的 progress 控件引用
        if hasattr(self, "_progress_label"):
            del self._progress_label
        if hasattr(self, "_progress_bar"):
            del self._progress_bar

        # 添加语音卡片
        self._voice_card = VoiceMessageCard(audio_path, duration)
        self._voice_card.play_clicked.connect(self._on_play_clicked)
        old_layout.addWidget(self._voice_card)

    def mark_failed(self, error: str):
        """标记为失败"""
        self.status = "failed"

        old_layout = self._bubble.layout()
        while old_layout.count():
            item = old_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if hasattr(self, "_progress_label"):
            del self._progress_label
        if hasattr(self, "_progress_bar"):
            del self._progress_bar

        err_label = QLabel(f"⚠️ {error[:50]}")
        err_label.setStyleSheet(f"""
            color: #FF4444;
            font-family: {styles.FONT_FAMILY};
            font-size: {styles.FONT_SIZE_SMALL}px;
            background: transparent;
        """)
        err_label.setWordWrap(True)
        err_label.setMaximumWidth(280)
        old_layout.addWidget(err_label)

    def update_play_progress(self, pct: float):
        if hasattr(self, "_voice_card"):
            self._voice_card.set_progress(pct)

    def update_play_state(self, playing: bool):
        if hasattr(self, "_voice_card"):
            self._voice_card.set_playing(playing)

    def _on_play_clicked(self, path: str):
        self.play_requested.emit(path)


class BotTypingBubble(MessageBubble):
    """爱弥斯"正在思考..."气泡（三个圆点动画）"""

    def __init__(self, parent=None):
        super().__init__("left", parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        avatar = AvatarWidget("爱", styles.COLOR_AEMEATH_AVATAR_BG)
        layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

        self._bubble = QFrame()
        self._bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_BOT_BUBBLE};
                border: 1px solid {styles.COLOR_BOT_BUBBLE_BORDER};
                border-radius: {styles.BUBBLE_RADIUS}px;
                padding: 6px 14px;
            }}
        """)
        bubble_layout = QHBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(4, 4, 4, 4)
        self._indicator = BotTypingIndicator()
        bubble_layout.addWidget(self._indicator)
        layout.addWidget(self._bubble)

        layout.addItem(QSpacerItem(40, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.add_shadow_to(self._bubble)

    def add_shadow_to(self, widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(4)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 25))
        widget.setGraphicsEffect(shadow)


class TimestampLabel(QLabel):
    """时间戳标签"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            color: {styles.COLOR_TEXT_TIMESTAMP};
            font-family: {styles.FONT_FAMILY};
            font-size: {styles.FONT_SIZE_TINY}px;
            background: transparent;
            padding: 4px 0;
        """)