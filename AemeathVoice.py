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


def _collect_python_candidates():
    """收集所有可用的 Python 解释器候选（返回去重后的路径列表）"""
    import shutil
    cands = []

    # 0. py launcher 枚举全部已安装 Python（最全）
    try:
        out = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=5)
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.lower().endswith("python.exe") and (":\\" in line or "/" in line):
                p = line.split()[-1]
                if p not in cands and Path(p).exists():
                    cands.append(p)
    except Exception:
        pass

    # 1. PATH 里的 pythonX.Y / python
    for name in ["python3.11", "python3.10", "python3.12", "python3.13", "python3", "python"]:
        py = shutil.which(name)
        if py and py not in cands:
            cands.append(py)

    # 2. 常见安装路径兜底
    home = Path.home()
    for v in ["311", "310", "312", "313"]:
        p = home / "AppData" / "Local" / "Programs" / "Python" / f"Python{v}" / "python.exe"
        if p.exists() and str(p) not in cands:
            cands.append(str(p))

    return cands


def _check_deps(py):
    """验证该解释器有运行 API 所需的依赖（fastapi/uvicorn/torch）"""
    try:
        out = subprocess.run(
            [py, "-c", "import fastapi, uvicorn, torch; print('DEPS_OK')"],
            capture_output=True, text=True, timeout=90,
        )
        return out.returncode == 0 and "DEPS_OK" in out.stdout
    except Exception:
        return False


def find_python():
    """找 Python 解释器（依赖优先，版本次之）

    优先级：
      1. 打包后的内嵌 Python（如果有 _internal/python/python.exe）
      2. AemeathVoice_Portable 内嵌 Python（如果存在）
      3. 系统解释器中**依赖齐全**（import fastapi/uvicorn/torch 成功）者：
         3.11 > 3.10 > 其他版本
      4. 找不到则返回 None，由调用方给出指引
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

    # 3. 系统解释器：先收集，再按版本偏好排序，逐个验证依赖
    cands = _collect_python_candidates()
    log.info(f"[find_python] 候选解释器: {cands}")

    def _ver_key(p):
        # 3.11 最优(0)，3.10 次之(1)，其余排后
        for pref, rank in (("311", 0), ("310", 1)):
            if f"Python{pref}" in p or f"python3.{pref[1:]}" in p or f"3.{pref[1:]}" in p:
                return rank
        return 2

    ordered = sorted(cands, key=_ver_key)
    log.info("[find_python] 正在验证各解释器的依赖（fastapi/uvicorn/torch）...")
    for py in ordered:
        if _check_deps(py):
            log.info(f"[find_python] ✅ 选中（依赖齐全）: {py}")
            return py
        log.info(f"[find_python] ⏭ 跳过（缺依赖或不可用）: {py}")

    return None


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
        log.error("[错误] 找不到依赖齐全的 Python 解释器")
        log.error("  API 需要 fastapi / uvicorn / torch，请任选其一：")
        log.error("  A) 安装 Python 3.11 并执行:")
        log.error('     pip install fastapi "uvicorn[standard]" torch --index-url https://download.pytorch.org/whl/cu128')
        log.error("  B) 或运行 scripts/install_deps.bat 自动安装")
        input("按回车退出...")
        sys.exit(1)

    if not api:
        log.error("[错误] 找不到 API 启动脚本")
        log.error(f"  期望位置: {root}/scripts/launch_aemeath_api.py")
        input("按回车退出...")
        sys.exit(1)

    # 模型分卷完整性检查（part2 = models/, part3 = text/）
    missing = []
    if not (root / "models" / "s1" / "aemeath-e20.ckpt").exists():
        missing.append("models/  ← 缺 part2_models.zip（1.8 GB，爱弥斯模型 + 底座）")
    if not (root / "text" / "G2PWModel" / "g2pW.onnx").exists():
        missing.append("text/    ← 缺 part3_g2pw_text.zip（608 MB，G2PW 多音字模型）")
    if missing:
        log.error("[错误] 模型文件不完整！只解压了 part1_runtime.zip？")
        log.error("  请把以下分卷也下载，并解压到 EXE 所在目录（解压后应出现这些文件夹）：")
        for m in missing:
            log.error(f"  ✗ {m}")
        log.error("  下载页: https://github.com/1983879947-ctrl/AemeathVoice/releases/tag/v1.0.0")
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