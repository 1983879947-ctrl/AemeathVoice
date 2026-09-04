# -*- coding: utf-8 -*-
"""用 faster-whisper 转写诊断音频，确认开头复读内容"""
from faster_whisper import WhisperModel

model = WhisperModel(
    r"C:\Users\27298\.cache\huggingface\hub\faster-whisper-medium",
    device="cuda", compute_type="float16",
)

for f in ["diag_short.wav", "diag_mid.wav"]:
    path = rf"E:\AemeathVoice\AemeathVoice_Portable\{f}"
    segments, info = model.transcribe(path, language="zh", vad_filter=False)
    print(f"\n=== {f} ===")
    for seg in segments:
        print(f"  [{seg.start:.1f}s -> {seg.end:.1f}s] {seg.text}")
