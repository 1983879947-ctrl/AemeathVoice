"""压力测试：通过 API 调用合成多种文本，统计失控生成概率。

需要先启动 API: python AemeathVoice_Portable/api/inference_api.py --port 9880
"""
import json, time
import urllib.request
from pathlib import Path

PORTABLE = Path(r"E:/AemeathVoice/AemeathVoice_Portable")
OUT_DIR = PORTABLE / "stress_outputs"

CASES = [
    ("长文本_50字",   "春天到了，万物复苏，山野间的桃花一朵一朵地盛开了，开得那样鲜艳，那样好看。"),
    ("长文本_100字",  "春天的阳光格外明媚，春姑娘迈着轻盈的脚步走来了。她越过高山，飞过河流，向人们展示着春天的生机勃勃。小草偷偷地从土里钻出来，柳树抽出了嫩绿的枝条，燕子从南方飞回来了，到处都是一片生机盎然的景象，让人忍不住深深地吸一口新鲜的空气。"),
    ("中长_30字",     "今天天气真不错，阳光明媚，微风拂面，适合去公园散步。"),
    ("重复_爱弥斯三遍", "爱弥斯爱弥斯爱弥斯爱弥斯爱弥斯爱弥斯爱弥斯爱弥斯"),
    ("超短_1字",      "嗯"),
    ("数字+英文混合",  "我的 ID 是 1983879947-ctrl，Aemeath 启动了。"),
    ("重复_的",       "的的的的的的的的的的的的的的的的的的的的的的的"),
    ("正常文本_15字",  "飞行雪绒，永不落幕。"),
    ("正常文本_10字",  "家人，你好呀。"),
    ("古诗_将进酒节选", "君不见黄河之水天上来，奔流到海不复回。君不见高堂明镜悲白发，朝如青丝暮成雪。"),
]

print(f"{'文本':<22} {'时长':>7} {'判定':>15} {'耗时':>8}")
print("=" * 60)
for label, text in CASES:
    t0 = time.time()
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:9880/tts",
            data=json.dumps({"text": text, "text_language": "zh"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        elapsed = time.time() - t0
        # wav 头 data chunk: 偏移 36+4=40 处 4 字节 data 长度（float 样本数）
        # 但 soundfile 实际不写 raw RIFF header；用 wave 模块打开 BytesIO
        import io, wave
        try:
            with wave.open(io.BytesIO(data), 'rb') as w:
                sr = w.getframerate()
                n = w.getnframes()
                dur = n / sr
        except Exception:
            dur = len(data) / 32000  # 兜底
        bad = ""
        if dur > 12: bad = "⚠️ 失控"
        elif dur > len(text) * 0.5: bad = "⚠️ 偏长"
        print(f"{label:<22} {dur:>6.2f}s {bad:>15}  {elapsed:>6.1f}s")
    except Exception as e:
        print(f"{label:<22} [ERROR] {e}")
