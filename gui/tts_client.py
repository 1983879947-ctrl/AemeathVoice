"""爱弥斯语音 GUI - TTS HTTP API 客户端

调用 AemeathVoice-API.exe 提供的 /tts 端点，POST 文本 → 拿到 WAV 字节流
"""
import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Optional, Callable

import requests


class TTSClient:
    """TTS HTTP API 客户端（带自动启动 API 子进程）"""

    def __init__(self, api_url: str = "http://127.0.0.1:9880"):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = 300  # 5 分钟超时

    def health(self) -> dict:
        """检查 API 健康状态"""
        try:
            r = self.session.get(f"{self.api_url}/health", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def wait_ready(self, timeout: float = 120.0) -> bool:
        """等待 API 就绪（首次启动可能需要加载模型 15-30 秒）"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                h = self.health()
                if h.get("status") == "ok":
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    def tts(
        self,
        text: str,
        text_language: str = "zh",
        ref_audio: Optional[str] = None,
        prompt_text: Optional[str] = None,
        prompt_language: str = "zh",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> dict:
        """合成语音

        progress_callback(percent: float, message: str) 用于实时报告进度

        返回 dict:
            success: bool
            audio_path: str  (WAV 文件路径)
            duration: float  (音频时长，秒)
            latency: float   (合成耗时，秒)
            error: str       (错误信息)
        """
        if progress_callback is None:
            progress_callback = lambda p, m: None

        progress_callback(5, "发送请求...")

        payload = {
            "text": text,
            "text_language": text_language,
            "prompt_language": prompt_language,
        }
        if ref_audio:
            payload["ref_audio_path"] = ref_audio
        if prompt_text:
            payload["prompt_text"] = prompt_text

        try:
            # 长文本合成可能较慢，给足超时
            t0 = time.time()
            progress_callback(10, "合成中，请稍候...")

            # 模拟进度（10 → 90 区间）
            import threading
            stop_flag = [False]

            def _fake_progress():
                pct = 10
                elapsed = 0
                while not stop_flag[0] and pct < 90:
                    time.sleep(0.5)
                    elapsed += 0.5
                    # 估算：每 1 秒文本大约合成 0.5 秒音频，按总时长线性增长
                    pct = min(90, 10 + elapsed * 8)
                    try:
                        progress_callback(pct, "爱弥斯在说话...")
                    except Exception:
                        break

            t = threading.Thread(target=_fake_progress, daemon=True)
            t.start()

            try:
                r = self.session.post(
                    f"{self.api_url}/tts",
                    json=payload,
                    timeout=self.timeout,
                    stream=False,
                )
            finally:
                stop_flag[0] = True

            r.raise_for_status()
            progress_callback(95, "下载音频...")

            # 写到临时文件
            tmp_dir = Path(tempfile.gettempdir()) / "aemeath_voice"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_text = "".join(c for c in text[:20] if c.isalnum() or c in " _-") or "voice"
            audio_path = tmp_dir / f"{safe_text}_{ts}.wav"
            audio_path.write_bytes(r.content)

            duration = float(r.headers.get("X-Duration", 0))
            latency = float(r.headers.get("X-Latency", 0))

            progress_callback(100, "完成！")
            return {
                "success": True,
                "audio_path": str(audio_path),
                "duration": duration,
                "latency": latency,
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "无法连接到 TTS 服务。请确认 AemeathVoice-API.exe 已启动。",
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "合成超时（>5分钟）。文本可能太长。",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"合成失败: {e}",
            }


class APILauncher:
    """自动启动 AemeathVoice-API.exe 子进程"""

    def __init__(self):
        self.process = None

    @staticmethod
    def find_api_exe() -> Optional[Path]:
        """查找 API 可执行文件"""
        # 打包后：EXE 在 AemeathVoice.exe 同目录
        # 开发时：API 源码在 E:\AemeathVoice\api\ 或 E:\workbuddy_workspace
        candidates = [
            # 1. 同目录的 API.exe（便携模式）
            Path(sys.executable).parent / "AemeathVoice-API.exe",
            # 2. 资源目录
            Path(sys.executable).parent / "_internal" / "AemeathVoice-API.exe",
            # 3. 开发模式：api/launch_api.py
            Path(__file__).parent.parent / "api" / "launch_api.py",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def start(self, console_output: bool = False) -> bool:
        """启动 API 子进程"""
        if self.process is not None and self.process.poll() is None:
            return True  # 已在运行

        api_path = self.find_api_exe()
        if api_path is None:
            return False

        try:
            import subprocess
            if api_path.suffix == ".exe":
                # EXE 模式
                creationflags = 0
                if not console_output and sys.platform == "win32":
                    # CREATE_NO_WINDOW
                    creationflags = 0x08000000
                self.process = subprocess.Popen(
                    [str(api_path)],
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL if not console_output else None,
                    stderr=subprocess.DEVNULL if not console_output else None,
                )
            else:
                # .py 脚本模式（开发）
                # 用 embedded Python 或系统 Python
                python_exe = Path(sys.executable).parent / "python.exe"
                if not python_exe.exists():
                    python_exe = Path(sys.executable)
                self.process = subprocess.Popen(
                    [str(python_exe), str(api_path)],
                    stdout=subprocess.DEVNULL if not console_output else None,
                    stderr=subprocess.DEVNULL if not console_output else None,
                )
            return True
        except Exception as e:
            print(f"启动 API 失败: {e}", file=sys.stderr)
            return False

    def stop(self):
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None