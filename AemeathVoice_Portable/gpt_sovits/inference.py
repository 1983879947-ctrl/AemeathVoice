"""精简版 GPT-SoVITS 推理入口（去掉 Gradio WebUI）

只暴露 get_tts_wav() 函数，专为 HTTP API / CLI / GUI 调用。
完全兼容 inference_webui.py 的接口。
"""
import os
import sys
import json
import logging
import warnings as _warnings
from pathlib import Path
from typing import List, Tuple, Optional

# 抑制大量无用 warning
_warnings.simplefilter(action="ignore", category=FutureWarning)
logging.getLogger("markdown_it").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)

import torch
import torchaudio
import numpy as np
import random
import soundfile as sf
from time import time as ttime

# 子模块（同级目录）
from text.LangSegmenter import LangSegmenter
from feature_extractor import cnhubert
from transformers import AutoModelForMaskedLM, AutoTokenizer
from module.models import Generator, SynthesizerTrn, SynthesizerTrnV3
from AR.models.t2s_lightning_module import Text2SemanticLightningModule
from peft import LoraConfig, get_peft_model
from text import cleaned_text_to_sequence
from text.cleaner import clean_text
from process_ckpt import get_sovits_version_from_path_fast, load_sovits_new
from tools.i18n.i18n import I18nAuto

# ============== 全局状态 ==============
version = os.environ.get("version", "v2")
model_version = version

cnhubert_base_path = os.environ.get("cnhubert_base_path", "pretrained_models/chinese-hubert-base")
bert_path = os.environ.get("bert_path", "pretrained_models/chinese-roberta-wwm-ext-large")

is_half = eval(os.environ.get("is_half", "True")) and torch.cuda.is_available()
dtype = torch.float16 if is_half else torch.float32
# is_half = False  # debug

punctuation = set(["!", "?", "…", ",", ".", "-", " "])

cnhubert.cnhubert_base_path = cnhubert_base_path

# device
if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

# i18n
language = os.environ.get("language", "Auto")
i18n = I18nAuto(language=language)

dict_language_v1 = {
    i18n("中文"): "all_zh",
    i18n("英文"): "en",
    i18n("日文"): "all_ja",
    i18n("中英混合"): "zh",
    i18n("日英混合"): "ja",
    i18n("多语种混合"): "auto",
}
dict_language_v2 = {
    i18n("中文"): "zh",  # 精简版：直接 zh，跳过 LangSegmenter
    i18n("英文"): "en",
    i18n("日文"): "ja",
    i18n("粤语"): "yue",
    i18n("韩文"): "ko",
    i18n("中英混合"): "zh",
    i18n("日英混合"): "ja",
    i18n("粤英混合"): "yue",
    i18n("韩英混合"): "ko",
    i18n("多语种混合"): "auto",
    i18n("多语种混合(粤语)"): "auto_yue",
}
dict_language = dict_language_v1 if version == "v1" else dict_language_v2

# BERT 特征模型（启动时加载一次）
tokenizer = AutoTokenizer.from_pretrained(bert_path)
bert_model = AutoModelForMaskedLM.from_pretrained(bert_path)
if is_half == True:
    bert_model = bert_model.half().to(device)
else:
    bert_model = bert_model.to(device)


def get_bert_feature(text, word2ph):
    with torch.no_grad():
        inputs = tokenizer(text, return_tensors="pt")
        for i in inputs:
            inputs[i] = inputs[i].to(device)
        res = bert_model(**inputs, output_hidden_states=True)
        res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()[1:-1]
    assert len(word2ph) == len(text)
    phone_level_feature = []
    for i in range(len(word2ph)):
        repeat_feature = res[i].repeat(word2ph[i], 1)
        phone_level_feature.append(repeat_feature)
    phone_level_feature = torch.cat(phone_level_feature, dim=0)
    return phone_level_feature.T


class DictToAttrRecursive(dict):
    def __init__(self, input_dict):
        super().__init__(input_dict)
        for key, value in input_dict.items():
            if isinstance(value, dict):
                value = DictToAttrRecursive(value)
            self[key] = value
            setattr(self, key, value)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"Attribute {item} not found")

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            value = DictToAttrRecursive(value)
        super(DictToAttrRecursive, self).__setitem__(key, value)
        super().__setattr__(key, value)

    def __delattr__(self, item):
        try:
            del self[item]
        except KeyError:
            raise AttributeError(f"Attribute {item} not found")


# cnhubert SSL 特征模型
ssl_model = cnhubert.get_model()
if is_half == True:
    ssl_model = ssl_model.half().to(device)
else:
    ssl_model = ssl_model.to(device)


# ============== 加载模型 ==============
v3v4set = {"v3", "v4"}

# 模型路径
gpt_path = os.environ.get("gpt_path", "")
sovits_path = os.environ.get("sovits_path", "")

t2s_model = None
vq_model = None
hps = None
if_lora_v3 = False
t2s_model_cudagraph = None


def change_sovits_weights(sovits_p, prompt_language=None, text_language=None):
    """切换 SoVITS 模型权重"""
    global vq_model, hps, version, model_version, dict_language, if_lora_v3, t2s_model_cudagraph

    t2s_model_cudagraph = None
    version, model_version, if_lora_v3 = get_sovits_version_from_path_fast(sovits_p)

    # 是否需要 LoRA 底模
    is_exist_s2gv3 = os.environ.get("path_sovits_v3", "") and os.path.exists(os.environ.get("path_sovits_v3", ""))
    is_exist_s2gv4 = os.environ.get("path_sovits_v4", "") and os.path.exists(os.environ.get("path_sovits_v4", ""))
    is_exist = is_exist_s2gv3 if model_version == "v3" else is_exist_s2gv4

    if if_lora_v3 == True and not is_exist:
        raise FileExistsError(f"SoVITS {model_version} 底模缺失，无法加载 LoRA 权重")

    dict_language = dict_language_v1 if version == "v1" else dict_language_v2

    dict_s2 = load_sovits_new(sovits_p)
    hps = dict_s2["config"]
    hps = DictToAttrRecursive(hps)
    hps.model.semantic_frame_rate = "25hz"

    if "enc_p.text_embedding.weight" not in dict_s2["weight"]:
        hps.model.version = "v2"
    elif dict_s2["weight"]["enc_p.text_embedding.weight"].shape[0] == 322:
        hps.model.version = "v1"
    else:
        hps.model.version = "v2"
    version = hps.model.version

    if "pretrained" not in sovits_p:
        clean_names = [n for n in hps.model.keys() if "vq" in n]
        for clean_name in clean_names:
            clean_name_clean = clean_name.replace(".quantizer.", ".vq.")
            clean_name_clean = clean_name_clean.replace(".quantizer",".vq")
            hps.model[clean_name.replace("vq.","quantizer.")] = hps.model[clean_name_clean]
            del hps.model[clean_name_clean]

    vq_model = SynthesizerTrn(
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        n_speakers=hps.data.n_speakers if hasattr(hps.data, 'n_speakers') else 0,
        **hps.model,
    )
    if is_half == True:
        vq_model = vq_model.half().to(device)
    else:
        vq_model = vq_model.to(device)
    vq_model.eval()
    vq_model.load_state_dict(dict_s2["weight"], strict=False)

    # if prompt_language/text_language 传入，自动切换 i18n 字典
    # 这里不需要 yield，因为我们是直接调用而非 Gradio 流式


def change_gpt_weights(gpt_p):
    """切换 GPT 模型权重"""
    global t2s_model, hz
    hz = 50
    dict_s1 = torch.load(gpt_p, map_location="cpu", weights_only=False)
    config = dict_s1["config"]
    t2s_model = Text2SemanticLightningModule(config, "****", is_train=False)
    t2s_model.load_state_dict(dict_s1["weight"], strict=False)
    if is_half == True:
        t2s_model = t2s_model.half().to(device)
    else:
        t2s_model = t2s_model.to(device)
    t2s_model.eval()


def set_seed(seed):
    if seed == -1:
        seed = random.randint(0, 1000000)
    seed = int(seed)
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)


# 启动时加载默认模型
if gpt_path and os.path.exists(gpt_path):
    print(f"[inference] 加载 GPT 模型: {gpt_path}")
    change_gpt_weights(gpt_path)
if sovits_path and os.path.exists(sovits_path):
    print(f"[inference] 加载 SoVITS 模型: {sovits_path}")
    change_sovits_weights(sovits_path)

print(f"[inference] 设备: {device}, 半精度: {is_half}")
print(f"[inference] 模型就绪 ✓")


# ============== 主推理函数 ==============
def get_bert_feature_with_lengths(text, word2ph):
    return get_bert_feature(text, word2ph)


def clean_text_inf(text, language, version):
    """调用 GPT-SoVITS 的文本清洗"""
    phones, word2ph, norm_text = clean_text(text, language, version)
    return phones, word2ph, norm_text


def get_tts_wav(
    ref_wav_path,
    prompt_text,
    prompt_language,
    text,
    text_language,
    top_k=20,
    top_p=0.6,
    temperature=0.6,
    ref_free=False,
):
    """GPT-SoVITS 主推理函数

    返回 [(sample_rate, audio_array), ...] 列表
    """
    if t2s_model is None or vq_model is None:
        raise RuntimeError("模型未加载")

    t_0 = ttime()
    prompt_language = dict_language[prompt_language]
    text_language = dict_language[text_language]

    if not ref_free:
        # 处理参考音频（用 soundfile 避免 torchaudio/torchcodec 依赖）
        from text.cleaner import clean_text
        phones1, word2ph1, norm_text1 = clean_text(prompt_text, prompt_language, version)

        # 保存原始音频数据（用于 refer spec 计算，对齐 hps.data.sampling_rate）
        ref_audio_np, sr = sf.read(ref_wav_path, dtype='float32')
        if ref_audio_np.ndim == 2:
            ref_audio_np = ref_audio_np.mean(axis=1)
        from_srate = sr

        # 关键：ssl_model (Hubert) 训练时是 16kHz，必须给 16kHz！
        # 对齐 webui 的 librosa.load(ref_wav_path, sr=16000)
        import librosa
        wav16k, _ = librosa.load(ref_wav_path, sr=16000)
        if wav16k.shape[0] > 160000 or wav16k.shape[0] < 48000:
            print(f"⚠️ 参考音频长度 {wav16k.shape[0]/16000:.1f}s 不在 3~10s 范围", flush=True)
        wav16k = torch.from_numpy(wav16k)
        # 拼接 0.3s 静音（按 32kHz 计算长度 = 9600，但实际接在 16kHz 后面 = 0.6s，对齐 webui）
        zero_wav = np.zeros(int(hps.data.sampling_rate * 0.3), dtype=np.float16 if is_half else np.float32)
        zero_wav_torch = torch.from_numpy(zero_wav).to(device)
        if is_half:
            zero_wav_torch = zero_wav_torch.half()
        if is_half:
            wav16k = wav16k.half().to(device)
        else:
            wav16k = wav16k.to(device)
        wav16k = torch.cat([wav16k, zero_wav_torch])

        # 用 16kHz 喂 ssl_model（对齐 webui）
        # cnhubert.forward 内部会自己加 batch 维度，所以传 1D
        # 返回的已是 last_hidden_state（Tensor），不是 BaseModelOutput
        wav16k_input = wav16k  # (T,) @ 16kHz
        print(f"  wav16k_input.shape = {tuple(wav16k_input.shape)}, dtype={wav16k_input.dtype}", flush=True)
        last_hidden = ssl_model(wav16k_input)  # (B, T, dim)
        ssl_content = last_hidden.transpose(1, 2)  # (B, dim, T)
        ssl_content = ssl_content.to(device)
        if is_half:
            ssl_content = ssl_content.half()
        codes = vq_model.extract_latent(ssl_content)
        # 对齐原版 webui: codes=(B, layers, T) → codes[0, 0] = (T,) 完整语义序列
        # （之前误写成 codes[0,:,0] 只取到 1 帧，prompt 语义缺失导致复读参考台词）
        if codes.dim() >= 2:
            prompt_semantic = codes[0, 0]  # (T,)
        else:
            prompt_semantic = codes.flatten()
        prompt = prompt_semantic.unsqueeze(0).to(device).long()  # (1, T) long

        # 计算 refer spec（v2 模型 vq_model.decode 需要 refers 参数）
        # 完全对齐 webui 的 get_spepc：用原始 wav → resample 到 hps.data.sampling_rate
        from module.mel_processing import spectrogram_torch
        sr1 = int(hps.data.sampling_rate)
        # 用原始采样率的 wav 数据
        ref_audio_orig = torch.from_numpy(ref_audio_np).float().unsqueeze(0)  # (1, T) float32
        if ref_audio_orig.shape[0] == 2:
            ref_audio_orig = ref_audio_orig.mean(0).unsqueeze(0)
        ref_audio_orig = ref_audio_orig.to(device)
        if from_srate != sr1:
            import torchaudio.functional as _taf2
            ref_audio_orig = _taf2.resample(ref_audio_orig, from_srate, sr1)
        maxx = ref_audio_orig.abs().max()
        if maxx > 1:
            ref_audio_orig /= min(2, maxx)
        refer_spec = spectrogram_torch(
            ref_audio_orig,
            hps.data.filter_length,
            hps.data.sampling_rate,
            hps.data.hop_length,
            hps.data.win_length,
            center=False,
        )
        refer_spec = refer_spec.to(dtype)  # half/float
        refers = [refer_spec]
    else:
        prompt = None
        refers = None
        phones1 = None
        word2ph1 = None
        norm_text1 = ""

    # 处理目标文本
    phones2, word2ph2, norm_text2 = clean_text(text, text_language, version)
    print(f"  文本规范化: {repr(norm_text2)}")

    # 短文本兜底：phones 太少时 GPT 推理会出问题
    if not ref_free and len(phones2) < 6:
        text = "。" + text
        phones2, word2ph2, norm_text2 = clean_text(text, text_language, version)
        print(f"  文本过短，已补全: {repr(norm_text2)}")
    from text import cleaned_text_to_sequence
    phones2_ids = cleaned_text_to_sequence(phones2, version)

    # 拼接 prompt + target（按 webui 方式）
    if not ref_free:
        bert = torch.cat([get_bert_feature(norm_text1, word2ph1).to(device),
                          get_bert_feature(norm_text2, word2ph2).to(device)], dim=1)
        phones2_ids = cleaned_text_to_sequence(phones1, version) + phones2_ids
    else:
        bert = get_bert_feature(norm_text2, word2ph2).to(device)

    all_phoneme_ids = torch.tensor(phones2_ids, dtype=torch.long).to(device).unsqueeze(0)
    all_phoneme_len = torch.tensor([all_phoneme_ids.shape[-1]], dtype=torch.long).to(device)
    bert = bert.to(device).unsqueeze(0)

    # T2S 推理
    t_1 = ttime()
    set_seed(-1)
    if i18n("中文") in text_language:
        lang = "zh"
    elif i18n("英文") in text_language:
        lang = "en"
    elif i18n("日文") in text_language:
        lang = "ja"
    else:
        lang = "auto"

    with torch.no_grad():
        pred_semantic, idx = t2s_model.model.infer_panel(
            all_phoneme_ids,
            all_phoneme_len,
            prompt,
            bert,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            repetition_penalty=1.35,  # 对齐原版 webui，防重复字成"乱码长音"
            early_stop_num=600,      # 收紧到 12 秒上限（50Hz*12s），降低失控生成的模糊尾音概率
        )
    pred_semantic = pred_semantic[:, -idx:].unsqueeze(dim=0)
    print(f"  T2S 用时: {ttime() - t_1:.2f}s")

    # SoVITS 推理
    t_2 = ttime()
    # v2 decode 需要 refers 参数；phones2 用 target 部分（不含 prompt）
    target_phones2, _, _ = clean_text(text, text_language, version)
    target_phoneme_ids = cleaned_text_to_sequence(target_phones2, version)
    if not ref_free:
        audio = vq_model.decode(
            pred_semantic,
            torch.LongTensor(target_phoneme_ids).to(device).unsqueeze(0),
            refers,
            speed=1.0,
        )[0][0].detach().cpu().numpy()
    else:
        audio = vq_model.decode(
            pred_semantic,
            torch.LongTensor(target_phoneme_ids).to(device).unsqueeze(0),
            speed=1.0,
        )[0][0].detach().cpu().numpy()
    print(f"  SoVITS 用时: {ttime() - t_2:.2f}s")
    print(f"  总用时: {ttime() - t_0:.2f}s")

    return [(32000, audio)]


# ============== 入口（仅用于测试）==============
if __name__ == "__main__":
    import soundfile as sf

    ref_wav = "../models/reference/basic_121068.wav"
    prompt = "世界由我守护。目标揭露"
    text = "你好，我是一行日辉的爱弥斯哦~"

    print(f"测试推理: {text}")
    result = get_tts_wav(
        ref_wav_path=ref_wav,
        prompt_text=prompt,
        prompt_language=i18n("中文"),
        text=text,
        text_language=i18n("中文"),
    )
    sr, audio = result[-1]
    out_path = "test_output.wav"
    sf.write(out_path, audio, sr)
    print(f"✅ 输出: {out_path} ({len(audio)/sr:.2f}s)")