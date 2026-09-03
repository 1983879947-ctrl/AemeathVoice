"""爱弥斯 TTS 一键调用工具（WorkBuddy 直接调）

用法：
  python aemeath_say.py --text "你好我是爱弥斯"
  python aemeath_say.py --text "飞行雪绒" --output out.wav
  python aemeath_say.py --text "在虚质磁爆深处" --ref-audio basic_121068.wav
  python aemeath_say.py --text "Hello" --lang en

输出：wav 文件路径写到 stdout（一行）
"""
import os
import sys
import argparse
import time

# === 路径配置 ===
ROOT = r'E:\workbuddy_workspace'
GPT_SOVITS_REPO = os.path.join(ROOT, 'GPT-SoVITS')
GPT_SOVITS_PKG = os.path.join(GPT_SOVITS_REPO, 'GPT_SoVITS')
sys.path.insert(0, GPT_SOVITS_REPO)
sys.path.insert(0, GPT_SOVITS_PKG)

# === jieba_fast monkey-patch ===
import jieba as _jieba
import jieba.posseg as _psg
_jieba.setLogLevel = lambda level: None
sys.modules['jieba_fast'] = _jieba
sys.modules['jieba_fast.posseg'] = _psg

# === 预创建 nltk cmudict 包（绕开网络下载）===
# 复制 GPT-SoVITS 自带的 cmudict.rep 到 nltk 期望的路径结构
import shutil
NLTK_TARGET = os.path.expanduser(r'~\AppData\Roaming\nltk_data')
NLTK_CORPORA = os.path.join(NLTK_TARGET, 'corpora')
NLTK_CMUDICT = os.path.join(NLTK_CORPORA, 'cmudict')
SOURCE_CMUDICT = os.path.join(GPT_SOVITS_PKG, 'text', 'cmudict.rep')

if not os.path.isdir(NLTK_CMUDICT):
    try:
        os.makedirs(NLTK_CMUDICT, exist_ok=True)
        # nltk cmudict 期望文件名为 'cmudict'，里面是 'WORD PHONEME PHONEME' 格式
        # 复制 GPT-SoVITS 的 cmudict.rep 作为初始数据
        if os.path.isfile(SOURCE_CMUDICT):
            shutil.copy(SOURCE_CMUDICT, os.path.join(NLTK_CMUDICT, 'cmudict'))
            print(f'✅ 预创建 nltk cmudict: {NLTK_CMUDICT}', file=sys.stderr)
    except Exception as e:
        print(f'⚠️ 无法预创建 nltk cmudict: {e}', file=sys.stderr)

# === 解析参数 ===
parser = argparse.ArgumentParser(description='爱弥斯 TTS - 文本转语音')
parser.add_argument('--text', required=True, help='要合成的文本')
parser.add_argument('--lang', default='zh', choices=['zh', 'en', 'ja'], help='文本语言 (默认 zh)')
parser.add_argument('--ref-audio', default='basic_121068.wav', help='参考音频文件名（在 aemeath_train/wavs/ 下）')
parser.add_argument('--ref-text', default='世界由我守护。目标揭露', help='参考音频对应的文本')
parser.add_argument('--output', default=None, help='输出 wav 路径（默认到 aemeath_outputs/）')
args = parser.parse_args()

# === 切到仓库根（sv.py 需要 cwd = GPT-SoVITS/）===
os.chdir(GPT_SOVITS_REPO)

# === 设置模型路径 ===
os.environ['bert_path'] = os.path.join(ROOT, 'GPT-SoVITS', 'GPT_SoVITS', 'pretrained_models', 'chinese-roberta-wwm-ext-large')
os.environ['cnhubert_base_path'] = os.path.join(ROOT, 'GPT-SoVITS', 'GPT_SoVITS', 'pretrained_models', 'chinese-hubert-base')
os.environ['gpt_path'] = os.path.join(ROOT, 'GPT-SoVITS', 'Logs', 's1', 'aemeath', 'aemeath-e20.ckpt')
os.environ['sovits_path'] = os.path.join(ROOT, 'GPT-SoVITS', 'Logs', 's2', 'aemeath', 'weights', 'aemeath_e20.pth')

# === 加载参考音频路径 ===
ref_audio_path = os.path.join(ROOT, 'aemeath_train', 'wavs', args.ref_audio)
if not os.path.isfile(ref_audio_path):
    print(f'❌ 参考音频不存在: {ref_audio_path}', file=sys.stderr)
    sys.exit(1)

# === 输出路径 ===
if args.output:
    output_path = args.output
else:
    output_dir = os.path.join(ROOT, 'aemeath_outputs')
    os.makedirs(output_dir, exist_ok=True)
    safe_text = ''.join(c for c in args.text[:20] if c.isalnum() or c in ' _-')
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f'{safe_text}_{timestamp}.wav')

# === 加载模型（首次 ~15 秒，后续 ~1 秒） ===
print(f'加载模型...', file=sys.stderr, flush=True)
t0 = time.time()
from GPT_SoVITS.inference_webui import get_tts_wav
from tools.i18n.i18n import I18nAuto
i18n = I18nAuto()
print(f'模型加载完成 ({time.time()-t0:.1f}s)', file=sys.stderr, flush=True)

# === 合成语音 ===
t1 = time.time()
result = list(get_tts_wav(
    ref_wav_path=ref_audio_path,
    prompt_text=args.ref_text,
    prompt_language=i18n('中文' if args.lang == 'zh' else ('英文' if args.lang == 'en' else '日文')),
    text=args.text,
    text_language=i18n('中文' if args.lang == 'zh' else ('英文' if args.lang == 'en' else '日文')),
    top_p=1,
    temperature=1,
))
if not result:
    print('❌ 合成失败：返回结果为空', file=sys.stderr)
    sys.exit(2)

# === 保存 ===
import soundfile as sf
sr, audio = result[-1]
sf.write(output_path, audio, sr)
duration = len(audio) / sr
print(f'合成完成 ({time.time()-t1:.1f}s) -> {output_path} ({duration:.1f}s)', file=sys.stderr)
# stdout 输出路径（让 WorkBuddy 能直接拿到）
print(output_path)