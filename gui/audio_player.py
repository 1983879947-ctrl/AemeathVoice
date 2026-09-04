"""爱弥斯语音 GUI - 音频播放器（基于 PySide6 QMediaPlayer）"""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl, QTimer, Signal, QObject
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioPlayer(QObject):
    """音频播放器（单例，复用以避免冲突）"""

    position_changed = Signal(int)  # 毫秒
    duration_changed = Signal(int)
    playback_finished = Signal()

    def __init__(self):
        super().__init__()
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

        self._current_path: Optional[str] = None

    def _on_position_changed(self, pos: int):
        self.position_changed.emit(pos)

    def _on_duration_changed(self, dur: int):
        self.duration_changed.emit(dur)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.playback_finished.emit()

    def play(self, audio_path: str):
        """播放 WAV 文件"""
        if not Path(audio_path).exists():
            return
        self._current_path = audio_path
        url = QUrl.fromLocalFile(audio_path)
        self._player.setSource(url)
        self._player.play()

    def stop(self):
        self._player.stop()

    def pause(self):
        self._player.pause()

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def position_ms(self) -> int:
        return self._player.position()

    def duration_ms(self) -> int:
        return self._player.duration()

    def set_volume(self, vol: float):
        """0.0 - 1.0"""
        self._audio_output.setVolume(max(0.0, min(1.0, vol)))