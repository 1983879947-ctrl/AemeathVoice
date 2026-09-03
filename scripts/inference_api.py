"""Aemeath Voice HTTP API 服务（FastAPI）

提供 /tts 端点，把文本转成爱弥斯风格的语音。

启动方法：
    python launch_aemeath_api.py
"""
import os
import sys
import io
import time
from pathlib import Path
from typing import Optional

# 路径配置
ROOT = Path(__file__).parent.parent
GPT_SOVITS_REPO = Path(os.environ.get('GPT_SOVITS_PATH', './GPT-SoVITS')).resolve()
SCRIPT_DIR = Path(__file__).parent.resolve()

# 添加路径
sys.path.insert(0, str(GPT_SOVITS_REPO))
sys.path.insert(0, str(GPT_SOVITS_REPO / 'GPT_SoVITS'))
sys.path.insert(0, str(SCRIPT_DIR))

# === 兼容补丁（与 aemeath_say.py 保持一致）===
import jieba as _jieba
import jieba.posseg as _psg
_jieba.setLogLevel = lambda level: None
sys.modules['jieba_fast'] = _jieba
sys.modules['jieba_fast.posseg'] = _psg

import shutil
NLTK_TARGET = Path.home() / 'AppData' / 'Roaming' / 'nltk_data'
NLTK_CMUDICT = NLTK_TARGET / 'corpora' / 'cmudict'
SOURCE_CMUDICT = GPT_SOVITS_REPO / 'GPT_SoVITS' / 'text' / 'cmudict.rep'

if not NLTK_CMUDICT.exists():
    try:
        NLTK_CMUDICT.mkdir(parents=True, exist_ok=True)
        if SOURCE_CMUDICT.exists():
            shutil.copy(SOURCE_CMUDICT, NLTK_CMUDICT / 'cmudict')
    except Exception as e:
        print(f'⚠️ NLTK cmudict 预创建失败: {e}', file=sys.stderr)

# PyTorch 2.6+ 兼容
import pathlib
import torch
torch.serialization.add_safe_globals([pathlib.WindowsPath, pathlib.Path])

# === FastAPI 应用 ===
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title='Aemeath Voice API',
    description='爱弥斯语音克隆模型 HTTP 服务',
    version='1.0.0',
)

# 全局模型（启动时加载一次）
_tts_model = None
_i18n = None


def init_model():
    """初始化模型（启动时调用一次）"""
    global _tts_model, _i18n

    # 设置环境变量
    os.environ['bert_path'] = str(GPT_SOVITS_REPO / 'GPT_SoVITS' / 'pretrained_models' / 'chinese-roberta-wwm-ext-large')
    os.environ['cnhubert_base_path'] = str(GPT_SOVITS_REPO / 'GPT_SoVITS' / 'pretrained_models' / 'chinese-hubert-base')

    # 模型路径（默认使用本项目自带的模型）
    s1_path = ROOT / 'models' / 's1' / 'aemeath-e20.ckpt'
    s2_path = ROOT / 'models' / 's2' / 'aemeath_e20.pth'

    # 如果项目内没有，回退到 GPT-SoVITS 仓库的 Logs
    if not s1_path.exists():
        s1_path = GPT_SOVITS_REPO / 'Logs' / 's1' / 'aemeath' / 'aemeath-e20.ckpt'
    if not s2_path.exists():
        s2_path = GPT_SOVITS_REPO / 'Logs' / 's2' / 'aemeath' / 'weights' / 'aemeath_e20.pth'

    os.environ['gpt_path'] = str(s1_path)
    os.environ['sovits_path'] = str(s2_path)

    # 切到 GPT-SoVITS 仓库根目录
    os.chdir(GPT_SOVITS_REPO)

    # 加载模型
    from GPT_SoVITS.inference_webui import get_tts_wav
    from tools.i18n.i18n import I18nAuto
    _tts_model = get_tts_wav
    _i18n = I18nAuto()

    print(f'✅ 模型加载完成', file=sys.stderr)
    print(f'   S1: {s1_path}', file=sys.stderr)
    print(f'   S2: {s2_path}', file=sys.stderr)


@app.on_event('startup')
async def startup_event():
    init_model()


# === API 模型 ===
class TTSRequest(BaseModel):
    text: str = Field(..., description='要合成的文本', max_length=1000)
    text_language: str = Field('zh', description='文本语言 (zh/en/ja)')
    ref_audio_path: Optional[str] = Field(None, description='参考音频路径（可选）')
    prompt_text: Optional[str] = Field(None, description='参考音频对应文本（可选）')
    prompt_language: str = Field('zh', description='参考音频语言')
    top_p: float = Field(1.0, ge=0, le=1, description='采样参数')
    temperature: float = Field(1.0, ge=0, le=2, description='温度参数')


# === API 端点 ===
@app.get('/')
async def root():
    return {
        'name': 'Aemeath Voice API',
        'version': '1.0.0',
        'docs': '/docs',
        'endpoints': ['/health', '/voices', '/tts']
    }


@app.get('/health')
async def health():
    return {
        'status': 'ok' if _tts_model is not None else 'loading',
        'model': 'aemeath-e20',
        'version': 'v2'
    }


@app.get('/voices')
async def list_voices():
    """列出可用参考音频"""
    ref_dir = ROOT / 'models' / 'reference'
    if not ref_dir.exists():
        ref_dir = GPT_SOVITS_REPO / 'models' / 'reference'
    if not ref_dir.exists():
        return {'voices': []}

    voices = []
    for wav_path in ref_dir.glob('*.wav'):
        voices.append({
            'name': wav_path.name,
            'path': str(wav_path),
        })
    return {'voices': voices}


@app.post('/tts')
async def tts(req: TTSRequest):
    """文本转语音"""
    if _tts_model is None:
        raise HTTPException(503, '模型尚未加载完成')

    # 默认参考音频
    ref_audio = req.ref_audio_path or str(ROOT / 'models' / 'reference' / 'basic_121068.wav')
    if not Path(ref_audio).exists():
        ref_audio = str(ROOT / 'models' / 'reference' / 'basic_121068.wav')
    if not Path(ref_audio).exists():
        raise HTTPException(404, f'参考音频不存在: {ref_audio}')

    prompt_text = req.prompt_text or '世界由我守护。目标揭露'

    lang_map = {'zh': '中文', 'en': '英文', 'ja': '日文'}
    text_lang = _i18n(lang_map.get(req.text_language, '中文'))
    prompt_lang = _i18n(lang_map.get(req.prompt_language, '中文'))

    try:
        t0 = time.time()
        result = list(_tts_model(
            ref_wav_path=ref_audio,
            prompt_text=prompt_text,
            prompt_language=prompt_lang,
            text=req.text,
            text_language=text_lang,
            top_p=req.top_p,
            temperature=req.temperature,
        ))

        if not result:
            raise HTTPException(500, '合成失败：返回结果为空')

        sr, audio = result[-1]

        # 编码为 WAV
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format='WAV')
        buf.seek(0)

        duration = len(audio) / sr
        latency = time.time() - t0

        return StreamingResponse(
            buf,
            media_type='audio/wav',
            headers={
                'X-Duration': f'{duration:.2f}',
                'X-Latency': f'{latency:.2f}',
                'Content-Disposition': f'attachment; filename="aemeath_{int(time.time())}.wav"',
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f'合成失败: {str(e)}')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=9880)
