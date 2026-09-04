"""AemeathVoice Launcher —— PyInstaller 入口

逻辑：
1. 检测打包目录（sys._MEIPASS 或 脚本同目录）
2. 启动 API server 作为后台进程
3. 等待 API 就绪
4. 打开浏览器到 Web 控制台
5. 阻塞主线程直到 API 进程退出
"""
import os
import sys
import time
import socket
import subprocess
import threading
import webbrowser
import logging
from pathlib import Path

# 强制 UTF-8（Windows 默认 GBK，emoji 会报错）
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def get_root():
    """获取 AemeathVoice 根目录（兼容开发模式 + 打包模式）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后：EXE 所在目录
        return Path(sys.executable).parent
    else:
        # 开发模式：脚本所在目录
        return Path(__file__).parent


# 写日志到 EXE 同目录
LOG_PATH = get_root() / "AemeathVoice.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("AemeathVoice")


def find_python():
    """找 Python 解释器
    优先级：
      1. 打包后的内嵌 Python（如果有 _internal/python/python.exe）
      2. AemeathVoice_Portable 内嵌 Python（如果存在）
      3. 系统 Python 3.11（GPT-SoVITS 兼容性最好）
      4. 系统 Python 3.10/3.12 兜底
      5. 其他系统 python
    """
    root = get_root()

    # 1. 内嵌 Python（_internal 子目录）
    embedded = root / "_internal" / "python" / "python.exe"
    if embedded.exists():
        return str(embedded)

    # 2. AemeathVoice_Portable 内嵌 Python
    portable = root / "AemeathVoice_Portable" / "python" / "python.exe"
    if portable.exists():
        return str(portable)

    # 3. 系统 Python（按版本优先级）
    import shutil
    candidates = []
    # 优先 3.11
    for v in ["3.11", "3.10", "3.12", "3.9"]:
        py = shutil.which(f"python{v}") or shutil.which(f"python3.{v[2:]}")
        if py:
            candidates.append(py)
    # 兜底：系统 python
    py = shutil.which("python")
    if py:
        candidates.append(py)

    # 4. 兜底：常见安装路径（Windows）
    home = Path.home()
    fallback_paths = [
        home / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "python.exe",
        home / "AppData" / "Local" / "Programs" / "Python" / "Python310" / "python.exe",
        Path("C:/Python311/python.exe"),
        Path("C:/Python310/python.exe"),
        Path("D:/Python311/python.exe"),
        Path("D:/Python310/python.exe"),
    ]
    for p in fallback_paths:
        if p.exists() and str(p) not in candidates:
            candidates.append(str(p))

    for py in candidates:
        # 验证版本
        try:
            out = subprocess.run(
                [py, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=5
            )
            ver = out.stdout.strip()
            # GPT-SoVITS 在 3.10 / 3.11 跑得最稳
            if ver in ("3.10", "3.11"):
                return py
            elif ver == "3.12" and not any("3.10" in c or "3.11" in c for c in candidates):
                return py
        except Exception:
            continue

    # 兜底返回第一个
    return candidates[0] if candidates else None


def find_api_script():
    """找 API 启动脚本（launch_aemeath_api.py）"""
    root = get_root()

    candidates = [
        # 1. 打包模式：API 文件在 _internal/AV/scripts/launch_aemeath_api.py
        root / "_internal" / "AV" / "scripts" / "launch_aemeath_api.py",
        # 2. 打包模式：API 文件在 _internal/AV/api/inference_api.py
        root / "_internal" / "AV" / "api" / "inference_api.py",
        # 3. 旧版兼容
        root / "_internal" / "aemeath_scripts" / "launch_aemeath_api.py",
        root / "_internal" / "aemeath_api" / "inference_api.py",
        # 4. 开发模式：脚本同目录的 scripts/launch_aemeath_api.py
        root / "scripts" / "launch_aemeath_api.py",
        # 5. 开发模式：精简版
        root / "AemeathVoice_Portable" / "scripts" / "launch_aemeath_api.py",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def wait_port(host: str, port: int, timeout: float = 120.0) -> bool:
    """等待端口开始监听"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    root = get_root()
    py = find_python()
    api = find_api_script()

    if not py:
        log.error("[错误] 找不到 Python 解释器")
        log.error("  请安装 Python 3.10+ 并加入 PATH")
        input("按回车退出...")
        sys.exit(1)

    if not api:
        log.error("[错误] 找不到 API 启动脚本")
        log.error(f"  期望位置: {root}/scripts/launch_aemeath_api.py")
        input("按回车退出...")
        sys.exit(1)

    port = 9880
    host = "127.0.0.1"

    log.info("=" * 60)
    log.info("  爱弥斯语音 - Aemeath Voice")
    log.info("=" * 60)
    log.info(f"  Python: {py}")
    log.info(f"  API 脚本: {api}")
    log.info(f"  监听端口: {host}:{port}")
    log.info(f"  日志文件: {LOG_PATH}")
    log.info("=" * 60)

    # 启动 API 子进程
    log.info("[1/3] 启动 API server...")
    cwd = str(Path(api).parent.parent)  # 切到 ROOT
    api_proc = subprocess.Popen(
        [py, api, "--port", str(port), "--host", host],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='replace',
    )

    # 后台线程：把 API stdout/stderr 打印到控制台
    def _drain_output():
        if api_proc.stdout:
            for line in iter(api_proc.stdout.readline, ""):
                log.info(f"[API] {line.rstrip()}")

    t = threading.Thread(target=_drain_output, daemon=True)
    t.start()

    # 等 API 就绪
    log.info(f"[2/3] 等待 API 在 {host}:{port} 就绪...")
    if not wait_port(host, port, timeout=180.0):
        log.error("[错误] API 启动超时（180秒）")
        log.error("  请检查 GPU 驱动、CUDA、PyTorch 安装")
        api_proc.terminate()
        input("按回车退出...")
        sys.exit(1)

    # 打开浏览器
    url = f"http://{host}:{port}/"
    log.info(f"[3/3] 打开浏览器: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        log.warning(f"自动打开浏览器失败: {e}")
        log.warning(f"  请手动访问: {url}")

    log.info("")
    log.info("=" * 60)
    log.info("  API 已启动，关闭此窗口将停止 API")
    log.info("  或按 Ctrl+C 退出")
    log.info("=" * 60)

    try:
        # 阻塞主线程，直到 API 进程结束
        api_proc.wait()
    except KeyboardInterrupt:
        log.info("\n正在停止 API ...")
        api_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()


if __name__ == "__main__":
    main()