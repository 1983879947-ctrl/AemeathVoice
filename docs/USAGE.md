# 使用说明

本指南详细介绍 Aemeath Voice 推理脚本的使用方法。

## 目录

1. [CLI 一键调用](#cli-一键调用)
2. [Python 函数调用](#python-函数调用)
3. [HTTP API](#http-api)
4. [参数详解](#参数详解)
5. [推荐用法](#推荐用法)

---

## CLI 一键调用

最简单的使用方式，直接命令行运行：

```bash
# 最简用法
python scripts/aemeath_say.py --text "你好，我是爱弥斯"

# 指定输出文件
python scripts/aemeath_say.py --text "飞行雪绒" --output my_voice.wav

# 换个参考音频（需要提前放入 models/reference/）
python scripts/aemeath_say.py --text "测试" --ref-audio other_audio.wav

# 英文文本
python scripts/aemeath_say.py --text "Hello World" --lang en

# 完整参数示例
python scripts/aemeath_say.py \
    --text "今天天气真好啊" \
    --ref-audio basic_121068.wav \
    --ref-text "世界由我守护。目标揭露" \
    --output sunny_day.wav \
    --lang zh
```

输出会保存到 `aemeath_outputs/` 目录（默认）或你指定的路径。

---

## Python 函数调用

在自己的 Python 代码中集成：

```python
import sys
sys.path.insert(0, 'scripts')

from aemeath_say import synthesize

audio_path = synthesize(
    text="一行日辉，今天也辛苦了！",
    output_path="hello.wav",
    ref_audio="basic_121068.wav",
    ref_text="世界由我守护。目标揭露",
    lang="zh"
)
print(f"已生成: {audio_path}")
```

或者直接调用底层 GPT-SoVITS 推理：

```python
import os
import sys

# 配置环境变量
os.environ['bert_path'] = '/path/to/chinese-roberta-wwm-ext-large'
os.environ['cnhubert_base_path'] = '/path/to/chinese-hubert-base'
os.environ['gpt_path'] = '/path/to/models/s1/aemeath-e20.ckpt'
os.environ['sovits_path'] = '/path/to/models/s2/aemeath_e20.pth'

# 切换到 GPT-SoVITS 仓库根目录（sv.py 需要）
os.chdir('/path/to/GPT-SoVITS')
sys.path.insert(0, '.')

from GPT_SoVITS.inference_webui import get_tts_wav
from tools.i18n.i18n import I18nAuto
i18n = I18nAuto()

# 合成语音
result = list(get_tts_wav(
    ref_wav_path="models/reference/basic_121068.wav",
    prompt_text="世界由我守护。目标揭露",
    prompt_language=i18n("中文"),
    text="你好，我是爱弥斯",
    text_language=i18n("中文"),
    top_p=1,
    temperature=1,
))

# 保存
import soundfile as sf
sr, audio = result[-1]
sf.write("output.wav", audio, sr)
```

---

## HTTP API

启动一个 REST API 服务，让其他应用通过 HTTP 调用：

```bash
python scripts/launch_aemeath_api.py
# 服务运行在 http://localhost:9880
```

### 调用示例

```bash
# 基础调用
curl -X POST http://localhost:9880/tts \
    -H "Content-Type: application/json" \
    -d '{
        "text": "你好，我是爱弥斯",
        "text_language": "zh"
    }' \
    --output output.wav
```

更多 API 细节请查看 [API.md](API.md)。

---

## 参数详解

### `--text`（必填）

要合成的文本内容。

- 支持中英文及混合
- 推荐单次文本 ≤ 300 字（更长的会被自动切句）
- 支持标点：，。！？；：""''（）【】《》
- **不支持** emoji（会触发编码错误）

### `--lang`（默认 `zh`）

文本语言：
- `zh`：中文
- `en`：英文
- `ja`：日文

### `--ref-audio`（默认 `basic_121068.wav`）

参考音频文件，决定合成音色的**风格与情感**。

- 推荐时长：3-10 秒
- 推荐内容：清晰的人声，无背景音乐
- 放置位置：`models/reference/` 或使用绝对路径

### `--ref-text`（默认 "世界由我守护。目标揭露"）

参考音频对应的**精确文本**。必须与音频内容完全一致！

### `--output`

输出 WAV 文件路径。默认保存到 `aemeath_outputs/` 并自动命名。

---

## 推理参数调优

`aemeath_say.py` 中可以调节：

```python
result = list(get_tts_wav(
    ...
    top_p=1,           # 0-1，越大越多样（推荐 0.7-1.0）
    temperature=1,     # 越大越随机（推荐 0.7-1.0）
))
```

| 参数 | 默认 | 推荐范围 | 效果 |
|------|------|----------|------|
| `top_p` | 1.0 | 0.7-1.0 | 越小越稳定但可能平淡 |
| `temperature` | 1.0 | 0.7-1.0 | 越小越稳定但可能机械 |

---

## 推荐用法

### 🎵 长文本朗诵

```bash
python scripts/aemeath_say.py --text "君不见黄河之水天上来..."
```

- 自动切句，无需手动处理
- 48-60 秒的诗篇约需 14-17 秒合成

### 💬 短句问候

```bash
python scripts/aemeath_say.py --text "早安呀~" --output morning.wav
```

- 3 秒内的文本约 1-2 秒合成

### 🎬 视频配音

将生成的 wav 用 ffmpeg 转为 mp3：
```bash
ffmpeg -i output.wav -codec:a libmp3lame -b:a 192k output.mp3
```

### 📱 批量合成

```python
import subprocess
texts = ["你好", "再见", "谢谢"]
for i, text in enumerate(texts):
    subprocess.run([
        "python", "scripts/aemeath_say.py",
        "--text", text,
        "--output", f"batch_{i}.wav"
    ])
```

---

## 常见问题

**Q：合成速度慢？**
A：首次加载约 15-20 秒，后续每条约 1-15 秒。GPU 性能越强越快。

**Q：生成的音频有杂音？**
A：尝试不同的参考音频，或者调节 `top_p` / `temperature`。

**Q：长文本合成卡顿？**
A：本项目已支持长文本自动切句，建议每段 ≤ 300 字。

**Q：能换参考音频吗？**
A：可以，但需要提供精确的参考文本，否则音色不稳定。
