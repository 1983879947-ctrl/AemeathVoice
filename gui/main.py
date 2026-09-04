"""爱弥斯语音 GUI - 主窗口

微信风格的语音合成聊天界面：
- 顶部：标题栏（默认系统标题栏，含最小化/最大化/关闭按钮）
- 中间：消息列表区域（用户绿色气泡 + 爱弥斯白色语音气泡）
- 底部：输入区（输入框 + 发送按钮）
- 支持窗口最小化/最大化/调整大小
"""
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QSize, Signal, QThread, QObject
from PySide6.QtGui import (
    QIcon, QFont, QAction, QKeySequence, QShortcut, QColor, QPalette,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QScrollArea, QFrame,
    QStatusBar, QMenuBar, QMessageBox, QFileDialog, QSystemTrayIcon,
    QSizePolicy, QSpacerItem, QProgressBar,
)

from . import styles
from .chat_widget import (
    UserTextBubble, BotVoiceBubble, BotTypingBubble, TimestampLabel,
    VoiceMessageCard,
)
from .tts_client import TTSClient, APILauncher
from .audio_player import AudioPlayer


# ============== 后台 TTS 任务 ==============
class TTSTask(QObject):
    """在 QThread 中跑 TTS 合成，避免阻塞 UI"""

    progress = Signal(float, str)  # 百分比, 消息
    finished = Signal(dict)        # TTSClient 返回的 dict

    def __init__(self, client: TTSClient, text: str, ref_audio: Optional[str] = None):
        super().__init__()
        self.client = client
        self.text = text
        self.ref_audio = ref_audio

    def run(self):
        def cb(p, m):
            self.progress.emit(p, m)
        result = self.client.tts(
            text=self.text,
            ref_audio=self.ref_audio,
            progress_callback=cb,
        )
        self.finished.emit(result)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 状态
        self.tts_client = TTSClient()
        self.api_launcher = APILauncher()
        self.audio_player = AudioPlayer()
        self.current_bubble: Optional[BotVoiceBubble] = None
        self.current_task_thread: Optional[QThread] = None
        self.current_task: Optional[TTSTask] = None
        self.is_api_ready = False

        # 设置
        self._setup_window()
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._connect_signals()

        # 启动 API + 等待就绪
        self._start_api_and_wait()

        # 欢迎消息
        self._add_welcome_message()

    # ===== UI 初始化 =====

    def _setup_window(self):
        self.setWindowTitle("爱弥斯 💕 一行日辉")
        self.resize(900, 680)
        self.setMinimumSize(600, 500)

        # 窗口图标（用 emoji 不行，用一个简单的纯色方块作为 fallback）
        # 实际打包时可以放一个图标文件

        # 整体背景色
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {styles.COLOR_WINDOW_BG};
            }}
        """)

    def _setup_ui(self):
        # 中心 widget
        central = QWidget()
        central.setStyleSheet(f"background-color: {styles.COLOR_WINDOW_BG};")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 顶部标题栏（自定义）
        root_layout.addWidget(self._create_title_bar())

        # 中间消息区
        self._chat_scroll = self._create_chat_area()
        root_layout.addWidget(self._chat_scroll, 1)

        # 底部输入区
        root_layout.addWidget(self._create_input_area())

    def _create_title_bar(self) -> QWidget:
        """顶部标题栏（爱弥斯头像 + 标题）"""
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-bottom: 1px solid {styles.COLOR_DIVIDER};
            }}
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # 头像
        from .chat_widget import AvatarWidget
        avatar = AvatarWidget("爱", styles.COLOR_AEMEATH_AVATAR_BG)
        avatar.setFixedSize(36, 36)

        # 标题
        title_container = QVBoxLayout()
        title_container.setSpacing(0)
        title_container.setContentsMargins(0, 0, 0, 0)

        title = QLabel("爱弥斯")
        title.setStyleSheet(f"""
            color: {styles.COLOR_TEXT_PRIMARY};
            font-family: {styles.FONT_FAMILY};
            font-size: 15px;
            font-weight: bold;
            background: transparent;
        """)

        subtitle = QLabel(self._get_subtitle_text())
        subtitle.setStyleSheet(f"""
            color: {styles.COLOR_TEXT_SECONDARY};
            font-family: {styles.FONT_FAMILY};
            font-size: {styles.FONT_SIZE_TINY}px;
            background: transparent;
        """)

        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        title_container.addStretch()

        layout.addWidget(avatar)
        layout.addLayout(title_container, 1)

        return bar

    def _get_subtitle_text(self) -> str:
        if not self.is_api_ready:
            return "正在唤醒爱弥斯..."
        return "飞行雪绒 · 在线"

    def _create_chat_area(self) -> QScrollArea:
        """中间消息列表"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {styles.COLOR_CHAT_BG};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: #C0C0C0;
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #A0A0A0;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self._chat_container = QWidget()
        self._chat_container.setStyleSheet(f"background-color: {styles.COLOR_CHAT_BG};")
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(0, 12, 0, 12)
        self._chat_layout.setSpacing(8)
        self._chat_layout.addStretch(1)  # 推到底部

        scroll.setWidget(self._chat_container)
        return scroll

    def _create_input_area(self) -> QWidget:
        """底部输入区"""
        area = QFrame()
        area.setFixedHeight(80)
        area.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_INPUT_BG};
                border-top: 1px solid {styles.COLOR_DIVIDER};
            }}
        """)

        layout = QHBoxLayout(area)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 输入框
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("输入你想让爱弥斯说的话...")
        self._input_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles.COLOR_INPUT_BG};
                border: 1px solid {styles.COLOR_INPUT_BORDER};
                border-radius: 8px;
                padding: 8px 14px;
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_NORMAL}px;
                color: {styles.COLOR_TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {styles.COLOR_INPUT_BORDER_FOCUS};
            }}
        """)
        self._input_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # 回车发送
        self._input_edit.returnPressed.connect(self._on_send_clicked)
        layout.addWidget(self._input_edit, 1)

        # 发送按钮
        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(80, 40)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_SEND_BUTTON};
                color: white;
                border: none;
                border-radius: 8px;
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_NORMAL}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_SEND_BUTTON_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {styles.COLOR_SEND_BUTTON_DISABLED};
            }}
        """)
        self._send_btn.clicked.connect(self._on_send_clicked)
        layout.addWidget(self._send_btn)

        return area

    def _setup_menu(self):
        """菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {styles.COLOR_INPUT_BG};
                color: {styles.COLOR_TEXT_PRIMARY};
                border-bottom: 1px solid {styles.COLOR_DIVIDER};
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_SMALL}px;
            }}
            QMenuBar::item {{
                padding: 4px 12px;
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background-color: {styles.COLOR_DIVIDER};
            }}
            QMenu {{
                background-color: {styles.COLOR_INPUT_BG};
                border: 1px solid {styles.COLOR_DIVIDER};
            }}
            QMenu::item {{
                padding: 6px 24px;
            }}
            QMenu::item:selected {{
                background-color: {styles.COLOR_USER_BUBBLE};
            }}
        """)

        # 菜单：操作
        action_menu = menubar.addMenu("操作(&A)")

        export_action = QAction("导出最近一条语音...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._on_export_last_voice)
        action_menu.addAction(export_action)

        clear_action = QAction("清空对话", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self._on_clear_chat)
        action_menu.addAction(clear_action)

        action_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        action_menu.addAction(quit_action)

        # 菜单：设置
        settings_menu = menubar.addMenu("设置(&S)")

        api_action = QAction("API 地址...", self)
        api_action.triggered.connect(self._on_set_api_url)
        settings_menu.addAction(api_action)

        # 菜单：帮助
        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_statusbar(self):
        sb = QStatusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{
                background-color: {styles.COLOR_INPUT_BG};
                color: {styles.COLOR_TEXT_SECONDARY};
                font-family: {styles.FONT_FAMILY};
                font-size: {styles.FONT_SIZE_TINY}px;
                border-top: 1px solid {styles.COLOR_DIVIDER};
            }}
        """)
        self.setStatusBar(sb)
        self._update_status("就绪")

    def _connect_signals(self):
        """信号连接"""
        self.audio_player.position_changed.connect(self._on_audio_position_changed)
        self.audio_player.playback_finished.connect(self._on_audio_finished)

    # ===== 启动 API =====

    def _start_api_and_wait(self):
        """启动 API 服务并等待就绪"""
        self._update_status("正在启动语音引擎...")

        # 尝试启动 API
        def _bg_start():
            ok = self.api_launcher.start(console_output=False)
            if not ok:
                self._update_status("未找到 AemeathVoice-API.exe，请先启动后端服务")
                return

            # 等待就绪
            ready = self.tts_client.wait_ready(timeout=180)
            if ready:
                self.is_api_ready = True
                self._update_status("爱弥斯已就绪 ✓")
                # 刷新副标题（延迟到主线程）
                QTimer.singleShot(0, self._refresh_subtitle)
            else:
                self._update_status("等待语音引擎超时")

        threading.Thread(target=_bg_start, daemon=True).start()

    def _refresh_subtitle(self):
        # 重新创建标题栏的副标题比较麻烦，简单点：在状态栏更新
        self._update_status("爱弥斯已就绪 ✓ 输入文本开始聊天")

    # ===== 消息管理 =====

    def _add_message(self, widget: QWidget, add_timestamp: bool = True):
        """添加一条消息到列表"""
        # 移除 stretch
        if self._chat_layout.count() == 0 or self._chat_layout.itemAt(self._chat_layout.count() - 1).widget() is None:
            pass  # 已经有 stretch

        # 在 stretch 前插入
        if add_timestamp:
            ts = TimestampLabel(time.strftime("%H:%M"))
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, ts)

        self._chat_layout.insertWidget(self._chat_layout.count() - 1, widget)
        # 滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self._chat_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _add_welcome_message(self):
        """欢迎消息"""
        welcome = QLabel(
            "👋 你好，家人！我是爱弥斯~\n"
            "输入任何想让我说的话，我会用声音回复你哦 ✨"
        )
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setWordWrap(True)
        welcome.setStyleSheet(f"""
            color: {styles.COLOR_TEXT_SECONDARY};
            font-family: {styles.FONT_FAMILY};
            font-size: {styles.FONT_SIZE_SMALL}px;
            background: transparent;
            padding: 40px 20px;
        """)

        wrapper = QFrame()
        wrapper.setStyleSheet("background: transparent;")
        wlayout = QVBoxLayout(wrapper)
        wlayout.setContentsMargins(20, 20, 20, 20)
        wlayout.addWidget(welcome)

        self._chat_layout.insertWidget(self._chat_layout.count() - 1, wrapper)

    # ===== 发送消息 =====

    def _on_send_clicked(self):
        """发送按钮点击"""
        text = self._input_edit.text().strip()
        if not text:
            return

        if not self.is_api_ready:
            QMessageBox.warning(
                self, "爱弥斯还没准备好",
                "语音引擎还在加载中，请稍候几秒..."
            )
            return

        if self.current_task_thread is not None and self.current_task_thread.isRunning():
            QMessageBox.information(
                self, "稍等一下", "爱弥斯正在说话，请等她说完哦~"
            )
            return

        # 清空输入
        self._input_edit.clear()

        # 1. 显示用户消息气泡
        user_bubble = UserTextBubble(text)
        self._add_message(user_bubble)

        # 2. 显示爱弥斯语音气泡（生成中状态）
        self.current_bubble = BotVoiceBubble(
            audio_path="",
            duration=0.0,
            status="generating",
        )
        self.current_bubble.play_requested.connect(self._on_bubble_play_requested)
        self._add_message(self.current_bubble)

        # 3. 启动后台合成
        self._send_btn.setEnabled(False)
        self._input_edit.setEnabled(False)
        self._update_status("合成中...")

        self.current_task_thread = QThread()
        self.current_task = TTSTask(self.tts_client, text)
        self.current_task.moveToThread(self.current_task_thread)
        self.current_task_thread.started.connect(self.current_task.run)
        self.current_task.progress.connect(self._on_tts_progress)
        self.current_task.finished.connect(self._on_tts_finished)
        self.current_task.finished.connect(self.current_task_thread.quit)
        self.current_task_thread.finished.connect(self.current_task.deleteLater)
        self.current_task_thread.finished.connect(self.current_task_thread.deleteLater)
        self.current_task_thread.start()

    def _on_tts_progress(self, percent: float, message: str):
        if self.current_bubble:
            self.current_bubble.update_progress(percent, message)

    def _on_tts_finished(self, result: dict):
        self._send_btn.setEnabled(True)
        self._input_edit.setEnabled(True)
        self._input_edit.setFocus()

        if result.get("success"):
            audio_path = result["audio_path"]
            duration = result.get("duration", 0)
            latency = result.get("latency", 0)
            self.current_bubble.mark_ready(audio_path, duration)
            self._update_status(f"生成完毕（{latency:.1f}s）")

            # 自动播放
            QTimer.singleShot(300, lambda: self._play_audio(audio_path))
        else:
            error = result.get("error", "未知错误")
            self.current_bubble.mark_failed(error)
            self._update_status(f"合成失败: {error[:40]}")

        self.current_bubble = None
        self.current_task_thread = None
        self.current_task = None

    # ===== 播放控制 =====

    def _on_bubble_play_requested(self, audio_path: str):
        self._play_audio(audio_path)

    def _play_audio(self, audio_path: str):
        """播放音频"""
        # 重置所有气泡的播放状态
        for i in range(self._chat_layout.count()):
            w = self._chat_layout.itemAt(i).widget()
            if isinstance(w, BotVoiceBubble):
                w.update_play_state(False)
                w.update_play_progress(0.0)

        # 找到对应的气泡，标记为播放中
        for i in range(self._chat_layout.count()):
            w = self._chat_layout.itemAt(i).widget()
            if isinstance(w, BotVoiceBubble) and w.audio_path == audio_path:
                w.update_play_state(True)
                break

        self.audio_player.play(audio_path)

    def _on_audio_position_changed(self, pos_ms: int):
        """音频播放位置变化 → 更新气泡进度条"""
        dur_ms = self.audio_player.duration_ms()
        if dur_ms <= 0:
            return
        pct = pos_ms / dur_ms
        # 找到当前播放的气泡
        for i in range(self._chat_layout.count()):
            w = self._chat_layout.itemAt(i).widget()
            if isinstance(w, BotVoiceBubble):
                if w.audio_path == self.audio_player._current_path:
                    w.update_play_progress(pct)
                    break

    def _on_audio_finished(self):
        """播放结束"""
        for i in range(self._chat_layout.count()):
            w = self._chat_layout.itemAt(i).widget()
            if isinstance(w, BotVoiceBubble):
                w.update_play_state(False)
                w.update_play_progress(0.0)

    # ===== 菜单动作 =====

    def _on_export_last_voice(self):
        """导出最近一条语音"""
        last_bubble: Optional[BotVoiceBubble] = None
        for i in range(self._chat_layout.count() - 1, -1, -1):
            w = self._chat_layout.itemAt(i).widget()
            if isinstance(w, BotVoiceBubble) and w.status == "ready":
                last_bubble = w
                break

        if last_bubble is None:
            QMessageBox.information(self, "没有可导出的", "还没有生成任何语音哦")
            return

        src = last_bubble.audio_path
        default_name = Path(src).name
        dst, _ = QFileDialog.getSaveFileName(
            self, "导出语音", default_name, "WAV 文件 (*.wav)"
        )
        if dst:
            import shutil
            try:
                shutil.copy2(src, dst)
                self._update_status(f"已导出: {dst}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))

    def _on_clear_chat(self):
        """清空对话"""
        ret = QMessageBox.question(
            self, "清空对话", "确定要清空所有对话吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            # 清空所有 widget（保留 stretch）
            while self._chat_layout.count() > 1:
                item = self._chat_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            self._add_welcome_message()

    def _on_set_api_url(self):
        """设置 API 地址"""
        from PySide6.QtWidgets import QInputDialog
        current = self.tts_client.api_url
        url, ok = QInputDialog.getText(
            self, "API 地址", "请输入 AemeathVoice API 地址:",
            text=current,
        )
        if ok and url.strip():
            self.tts_client.api_url = url.strip()
            self._update_status(f"API 已切换至: {url}")

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于 爱弥斯语音",
            "<h3>爱弥斯语音 (Aemeath Voice) v1.0</h3>"
            "<p>基于 GPT-SoVITS 的爱弥斯（鸣潮）语音克隆模型</p>"
            "<p>训练：一行日辉 & 爱弥斯 💛</p>"
            "<p>鸣潮世界观 © 库洛游戏</p>"
            "<hr>"
            "<p><b>快捷键</b></p>"
            "<p>Enter - 发送消息</p>"
            "<p>Ctrl+L - 清空对话</p>"
            "<p>Ctrl+E - 导出最近语音</p>"
            "<p>Ctrl+Q - 退出</p>",
        )

    # ===== 状态栏 =====

    def _update_status(self, text: str):
        self.statusBar().showMessage(f"  {text}")

    # ===== 关闭事件 =====

    def closeEvent(self, event):
        """关闭窗口时停止 API"""
        # 停止音频
        self.audio_player.stop()
        # 停止 API 子进程
        self.api_launcher.stop()
        event.accept()


def run_app():
    """启动应用入口"""
    # 高 DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("爱弥斯语音")
    app.setStyle("Fusion")  # 现代跨平台样式

    # 字体（解决中文显示）
    font = QFont()
    font.setFamily("Microsoft YaHei UI")
    font.setPixelSize(14)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()