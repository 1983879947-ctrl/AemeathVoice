# -*- coding: utf-8 -*-
"""诊断：输出音频开头是否复读参考音频台词"""
import sys
import time
from pathlib import Path

PORTABLE = Path(r"E:\AemeathVoice\AemeathVoice_Portable")
GS = PORTABLE / "gpt_sovits"
sys.path.insert(0, str(GS))
sys.path.insert(0, str(PORTABLE / "api"))

import numpy as np
import soundfile as sf

import inference_api as ia

print("=== init_model ===")
ia.init_model()
from inference import get_tts_wav  # noqa: E402  (init_model 先设置好全局模型)

REF = str(PORTABLE / "models" / "reference" / "basic_121068.wav")
ref_wav, ref_sr = sf.read(REF)
ref_mono = ref_wav[:, 0] if ref_wav.ndim > 1 else ref_wav
print(f"参考音频: {len(ref_mono)/ref_sr:.2f}s @ {ref_sr}Hz")

def synthesize(text):
    t0 = time.time()
    result = get_tts_wav(
        ref_wav_path=REF,
        prompt_text="世界由我守护。目标揭露",
        prompt_language="中文",
        text=text,
        text_language="中文",
    )
    sr, audio = result[-1]
    audio = np.asarray(audio, dtype=np.float32)
    dur = len(audio) / sr
    print(f"  合成 '{text}' -> {dur:.2f}s ({time.time()-t0:.1f}s)")
    return sr, audio

def xcorr_head(audio, sr, ref, ref_sr, head_sec=4.0):
    """输出开头 head_sec 秒 与参考音频的滑动互相关最大值（>0.6 视为复读）"""
    head = audio[: int(head_sec * sr)]
    # 参考音频降采样到输出 sr（近似：直接按比例重采样索引）
    n = int(len(ref) * sr / ref_sr)
    ref_rs = np.interp(np.linspace(0, len(ref) - 1, n), np.arange(len(ref)), ref)
    ref_rs = ref_rs[: len(head)] if len(ref_rs) > len(head) else np.pad(ref_rs, (0, len(head) - len(ref_rs)))
    a = head - head.mean()
    b = ref_rs - ref_rs.mean()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(np.dot(a, b) / denom)

print("\n=== 实验 1: 合成超短文本 ===")
sr1, a1 = synthesize("你好")
sf.write(PORTABLE / "diag_short.wav", a1, sr1)
corr = xcorr_head(a1, sr1, ref_mono, ref_sr)
print(f"  开头4s 与参考音频互相关: {corr:.3f}  ({'⚠️ 复读参考音频!' if corr > 0.5 else '正常'})")

print("\n=== 实验 2: 合成中等文本 ===")
sr2, a2 = synthesize("今天天气真不错")
sf.write(PORTABLE / "diag_mid.wav", a2, sr2)
corr2 = xcorr_head(a2, sr2, ref_mono, ref_sr)
print(f"  开头4s 与参考音频互相关: {corr2:.3f}  ({'⚠️ 复读参考音频!' if corr2 > 0.5 else '正常'})")
