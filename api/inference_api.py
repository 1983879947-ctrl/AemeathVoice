"""爱弥斯语音 API 服务（FastAPI + GPT-SoVITS）

相对路径版本——专为 AemeathVoice_Portable 自包含分发设计：
- 启动后会自动找同级的 gpt_sovits/ 推理代码和 models/ 模型
- 不依赖任何外部环境变量

用法：
    python inference_api.py                 # 启动 API，监听 127.0.0.1:9880
    python inference_api.py --port 9881
"""
import os
import sys
import io
import time
import json
import shutil
import argparse
import logging
import traceback
from pathlib import Path
from typing import Optional

# ============== 路径解析（关键！）==============
# __file__ 可能在多个位置：
#   开发模式 A（主仓库）：   E:\AemeathVoice\api\inference_api.py
#   开发模式 B（精简版）：   E:\AemeathVoice\AemeathVoice_Portable\api\inference_api.py
#   EXE 模式（PyInstaller）：E:\xxx\dist\AemeathVoice\_internal\AV\api\inference_api.py
#                          → ROOT.parent = E:\xxx\dist\AemeathVoice\  ← 模型应该在这
ROOT = Path(__file__).resolve().parent.parent

# 自动检测 GPT-SoVITS 路径
GPT_SOVITS_DIR_CANDIDATES = [
    ROOT / "gpt_sovits",
    ROOT / "AemeathVoice_Portable" / "gpt_sovits",
    ROOT.parent / "AemeathVoice_Portable" / "gpt_sovits",  # 旧版兼容
]
GPT_SOVITS_DIR = next((p for p in GPT_SOVITS_DIR_CANDIDATES if p.exists()), GPT_SOVITS_DIR_CANDIDATES[0])

# 模型路径：EXE 同目录优先
def _exe_root():
    """如果运行在 PyInstaller 打包模式，返回 EXE 同目录
    通过检查 sys._MEIPASS（PyInstaller 特有）或 _internal 目录存在性来判断
    """
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        # PyInstaller 临时目录，从中找到真正的 EXE 目录
        # _MEIPASS 通常是 _internal/，EXE 在其 parent
        return Path(meipass).parent
    # 兜底：检查 _internal/AV/api/ 这种 PyInstaller 输出布局
    if (ROOT / "_internal" / "AV").exists() or "_internal" in str(ROOT):
        # ROOT 是 _internal/AV/，EXE 在 _internal/AV/../..
        return ROOT.parent.parent
    return None

_exe_root = _exe_root()
MODELS_DIR_CANDIDATES = [
    _exe_root / "models" if _exe_root else None,
    _exe_root / "AemeathVoice_Portable" / "models" if _exe_root else None,
    ROOT / "models",
    ROOT / "AemeathVoice_Portable" / "models",
    ROOT.parent / "AemeathVoice_Portable" / "models",
]
MODELS_DIR_CANDIDATES = [p for p in MODELS_DIR_CANDIDATES if p is not None]
MODELS_DIR = next((p for p in MODELS_DIR_CANDIDATES if p.exists()), MODELS_DIR_CANDIDATES[0])
PRETRAINED_DIR_CANDIDATES = [
    MODELS_DIR / "pretrained",
    MODELS_DIR.parent / "AemeathVoice_Portable" / "models" / "pretrained",
    ROOT.parent.parent / "models" / "pretrained" if _exe_root else None,  # EXE 同目录
]
PRETRAINED_DIR_CANDIDATES = [p for p in PRETRAINED_DIR_CANDIDATES if p is not None]
PRETRAINED_DIR = next((p for p in PRETRAINED_DIR_CANDIDATES if p.exists()), PRETRAINED_DIR_CANDIDATES[0])

# ============== 添加 GPT-SoVITS 路径 ==============
sys.path.insert(0, str(GPT_SOVITS_DIR))

# ============== 兼容补丁（同 aemeath_say.py）==============
import jieba as _jieba
import jieba.posseg as _psg
_jieba.setLogLevel = lambda level: None
sys.modules['jieba_fast'] = _jieba
sys.modules['jieba_fast.posseg'] = _psg

# 预创建 nltk cmudict
NLTK_TARGET = Path.home() / "AppData" / "Roaming" / "nltk_data"
NLTK_CORPORA = NLTK_TARGET / "corpora"
NLTK_CMUDICT = NLTK_CORPORA / "cmudict"
SOURCE_CMUDICT = GPT_SOVITS_DIR / "text" / "cmudict.rep"

if not NLTK_CMUDICT.exists():
    try:
        NLTK_CORPORA.mkdir(parents=True, exist_ok=True)
        NLTK_CMUDICT.mkdir(parents=True, exist_ok=True)
        if SOURCE_CMUDICT.exists():
            shutil.copy(SOURCE_CMUDICT, NLTK_CMUDICT / "cmudict")
            logging.info(f"✅ 预创建 nltk cmudict: {NLTK_CMUDICT}")
    except Exception as e:
        logging.warning(f"⚠️ 无法预创建 nltk cmudict: {e}")

# **必须在 import nltk 之前**设置 NLTK_DATA 环境变量（nltk 启动时会读）
os.environ["NLTK_DATA"] = str(NLTK_TARGET)

# PyTorch 2.6+ 兼容
import pathlib
import torch
torch.serialization.add_safe_globals([pathlib.WindowsPath, pathlib.Path])

# 设置 GPT-SoVITS 期望的环境变量（在 import 之前）
os.environ["version"] = os.environ.get("version", "v2")
os.environ["bert_path"] = str(PRETRAINED_DIR / "chinese-roberta-wwm-ext-large")
os.environ["cnhubert_base_path"] = str(PRETRAINED_DIR / "chinese-hubert-base")

# 默认模型路径（v2）
GPT_MODEL = MODELS_DIR / "s1" / "aemeath-e20.ckpt"
SOVITS_MODEL = MODELS_DIR / "s2" / "aemeath_e20.pth"
REF_AUDIO = MODELS_DIR / "reference" / "basic_121068.wav"

if GPT_MODEL.exists():
    os.environ["gpt_path"] = str(GPT_MODEL)
if SOVITS_MODEL.exists():
    os.environ["sovits_path"] = str(SOVITS_MODEL)


# ============== GPT-SoVITS 切到 cwd ==============
# 很多 GPT-SoVITS 代码用相对路径，所以 chdir
if GPT_SOVITS_DIR.exists():
    os.chdir(GPT_SOVITS_DIR)
else:
    print(f"[警告] GPT-SoVITS 目录不存在: {GPT_SOVITS_DIR}")
    print(f"       API 启动后调用会失败")

# ============== FastAPI 应用 ==============
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Aemeath Voice API",
    description="爱弥斯语音克隆模型 HTTP 服务",
    version="1.0.0",
)

# 全局模型
_tts_model = None
_i18n = None
_device = "cpu"
_is_half = False


def init_model():
    """启动时加载模型（一次性 ~15-30s）"""
    global _tts_model, _i18n, _device, _is_half

    logging.info("=" * 60)
    logging.info("🚀 Aemeath Voice API 启动中...")
    logging.info("=" * 60)
    logging.info(f"  ROOT: {ROOT}")
    logging.info(f"  GPT-SoVITS: {GPT_SOVITS_DIR}")
    logging.info(f"  Models: {MODELS_DIR}")
    logging.info(f"  Pretrained: {PRETRAINED_DIR}")
    logging.info(f"  GPT 模型: {GPT_MODEL}")
    logging.info(f"  SoVITS 模型: {SOVITS_MODEL}")
    logging.info(f"  参考音频: {REF_AUDIO}")

    # 检查文件存在
    if not GPT_MODEL.exists():
        raise FileNotFoundError(f"GPT 模型不存在: {GPT_MODEL}")
    if not SOVITS_MODEL.exists():
        raise FileNotFoundError(f"SoVITS 模型不存在: {SOVITS_MODEL}")
    if not REF_AUDIO.exists():
        raise FileNotFoundError(f"参考音频不存在: {REF_AUDIO}")

    bert_path = PRETRAINED_DIR / "chinese-roberta-wwm-ext-large"
    if not bert_path.exists():
        raise FileNotFoundError(f"BERT 预训练模型不存在: {bert_path}")
    cnhubert_path = PRETRAINED_DIR / "chinese-hubert-base"
    if not cnhubert_path.exists():
        raise FileNotFoundError(f"cnHubert 预训练模型不存在: {cnhubert_path}")

    # 检测 GPU
    if torch.cuda.is_available():
        _device = "cuda"
        _is_half = True
        logging.info(f"  ✅ 检测到 GPU: {torch.cuda.get_device_name(0)}")
    else:
        _device = "cpu"
        _is_half = False
        logging.info("  ⚠️ 未检测到 GPU，使用 CPU 模式（速度会较慢）")

    # 加载推理函数（用我们精简版的 inference.py）
    t0 = time.time()
    try:
        # 把 gpt_sovits/ 加入路径（inference.py 在 gpt_sovits/ 下）
        sys.path.insert(0, str(GPT_SOVITS_DIR))
        from inference import get_tts_wav
        from tools.i18n.i18n import I18nAuto
        _tts_model = get_tts_wav
        _i18n = I18nAuto()
        logging.info(f"  ✅ 模型加载完成 ({time.time() - t0:.1f}s)")
    except Exception as e:
        logging.error(f"  ❌ 模型加载失败: {e}")
        traceback.print_exc()
        raise


@app.on_event("startup")
async def startup_event():
    init_model()


# ============== API 模型 ==============
class TTSRequest(BaseModel):
    text: str = Field(..., description="要合成的文本", max_length=1000)
    text_language: str = Field("zh", description="文本语言 (zh/en/ja)")
    ref_audio_path: Optional[str] = Field(None, description="参考音频路径（可选）")
    prompt_text: Optional[str] = Field(None, description="参考音频对应文本（可选）")
    prompt_language: str = Field("zh", description="参考音频语言")
    # 默认值对齐 webui.get_tts_wav：top_k=20, top_p=0.6, temperature=0.6
    # 用更确定的采样，接近训练分布，听感更稳定
    top_k: int = Field(20, ge=-1, description="Top-K 采样（-1 禁用）")
    top_p: float = Field(0.6, ge=0, le=1, description="Nucleus 采样阈值")
    temperature: float = Field(0.6, ge=0, le=2, description="采样温度")


# ============== 端点 ==============
@app.get("/")
async def root():
    """默认路由：返回 Web 控制台（HTML）"""
    web_index = ROOT / "web" / "index.html"
    if web_index.exists():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=web_index.read_text(encoding="utf-8"))
    return {
        "name": "Aemeath Voice API",
        "version": "1.0.0",
        "device": _device,
        "is_half": _is_half,
        "endpoints": ["/health", "/voices", "/tts"],
        "hint": "Web 控制台未找到 — 请把 index.html 放到 ROOT/web/",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok" if _tts_model is not None else "loading",
        "model": "aemeath-e20",
        "version": "v2",
        "device": _device,
    }


@app.get("/voices")
async def list_voices():
    """列出可用参考音频"""
    ref_dir = MODELS_DIR / "reference"
    if not ref_dir.exists():
        return {"voices": []}
    voices = []
    for wav_path in ref_dir.glob("*.wav"):
        voices.append({"name": wav_path.name, "path": str(wav_path)})
    return {"voices": voices}


@app.post("/tts")
async def tts(req: TTSRequest):
    """文本转语音 → 返回 WAV 音频流"""
    if _tts_model is None:
        raise HTTPException(503, "模型尚未加载完成")

    # 默认参考音频
    ref_audio = req.ref_audio_path or str(REF_AUDIO)
    if not Path(ref_audio).exists():
        ref_audio = str(REF_AUDIO)
    if not Path(ref_audio).exists():
        raise HTTPException(404, f"参考音频不存在: {ref_audio}")

    prompt_text = req.prompt_text or "世界由我守护。目标揭露"

    lang_map = {"zh": "中文", "en": "英文", "ja": "日文"}
    text_lang = _i18n(lang_map.get(req.text_language, "中文"))
    prompt_lang = _i18n(lang_map.get(req.prompt_language, "中文"))

    try:
        t0 = time.time()
        result = list(_tts_model(
            ref_wav_path=ref_audio,
            prompt_text=prompt_text,
            prompt_language=prompt_lang,
            text=req.text,
            text_language=text_lang,
            top_k=req.top_k,
            top_p=req.top_p,
            temperature=req.temperature,
        ))
        if not result:
            raise HTTPException(500, "合成失败：返回结果为空")

        sr, audio = result[-1]
        import soundfile as sf
        import numpy as np
        # soundfile 不支持 float16，转 float32
        if isinstance(audio, np.ndarray) and audio.dtype == np.float16:
            audio = audio.astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        buf.seek(0)

        duration = len(audio) / sr
        latency = time.time() - t0
        logging.info(f"  ✓ 合成: \"{req.text[:30]}...\" ({duration:.1f}s, {latency:.1f}s)")

        return StreamingResponse(
            buf,
            media_type="audio/wav",
            headers={
                "X-Duration": f"{duration:.2f}",
                "X-Latency": f"{latency:.2f}",
                "Content-Disposition": f'attachment; filename="aemeath_{int(time.time())}.wav"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"合成失败: {e}")


# ============== 入口 ==============
def main():
    parser = argparse.ArgumentParser(description="Aemeath Voice API 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=9880, help="监听端口")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        import uvicorn
    except ImportError:
        print("❌ 缺少依赖: fastapi / uvicorn")
        print("请运行: pip install fastapi uvicorn[standard]")
        sys.exit(1)

    print(f"🚀 Aemeath Voice API 服务启动...")
    print(f"📡 监听地址: http://{args.host}:{args.port}")
    print(f"📖 API 文档: http://{args.host}:{args.port}/docs")
    print(f"📂 ROOT: {ROOT}")
    print()

    uvicorn.run(
        "inference_api:app",
        host=args.host,
        port=args.port,
        log_level="warning",  # 减少 uvicorn 的日志噪音
        access_log=False,
    )


if __name__ == "__main__":
    main()