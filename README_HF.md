---
license: mit
language:
  - zh
tags:
  - text-to-speech
  - tts
  - voice-clone
  - chinese
  - gpt-sovits
  - wuthering-waves
  - aemeath
  - character-voice
datasets:
  - custom-wav-collection
metrics:
  - loss
pipeline_tag: text-to-speech
model_name: Aemeath Voice
---

# 🎤 Aemeath Voice (爱弥斯语音模型)

基于 GPT-SoVITS v2 训练的《鸣潮》游戏角色"爱弥斯"中文语音克隆模型。

> 🤖 本文件是 Hugging Face 模型页面专用 README（带 YAML frontmatter），GitHub 主页请看主仓库的 [README.md](https://github.com/your-username/AemeathVoice/blob/main/README.md)

## ✨ 简介

- 🎯 **训练数据**：192 条爱弥斯游戏台词（25.7 分钟）
- 🧠 **训练轮次**：20 epochs（S1 loss 下降 50%，top-3 准确率提升 60%）
- 🗣️ **音色特点**：温柔知性的少女音，适合朗诵 / 念长文本
- 🚀 **开箱即用**：CLI / Python / HTTP API 三种调用方式

## 📦 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `models/s1/aemeath-e20.ckpt` | 149 MB | GPT 语义模型（20 epoch） |
| `models/s2/aemeath_e20.pth` | 82 MB | SoVITS 推理权重（half precision） |
| `models/reference/basic_121068.wav` | 568 KB | 参考音频（3.38 秒，战斗台词） |

## 🚀 快速使用

### 1. 安装依赖

```bash
pip install huggingface_hub gpt_sovits  # 详见主仓库
```

### 2. 一键下载 + 运行

```bash
# 从 Hugging Face 下载模型
git clone https://huggingface.co/your-username/aemeath-voice
cd aemeath-voice

# 或者用 huggingface_hub
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='your-username/aemeath-voice', local_dir='./models')"
```

### 3. 调用推理

```python
# 用 transformers / huggingface_hub 一行代码调用
# 详见主仓库: https://github.com/your-username/AemeathVoice
```

## 📊 训练指标

| 指标 | Epoch 1 | Epoch 20 | 提升 |
|------|---------|----------|------|
| S1 Loss | 2.09e+3 | **1.05e+3** | ↓ 50% |
| S1 Top-3 Acc | 0.522 | **0.830** | ↑ 60% |

## ⚖️ 版权

- 角色"爱弥斯"是库洛游戏的知识产权
- 本模型仅供个人学习与研究使用
- 不得用于商业用途

## 🙏 致谢

- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) - 训练框架
- [库洛游戏 / KURO GAMES](https://www.kurogames.com/) - 《鸣潮》游戏开发

## 📞 链接

- 🐙 主仓库：https://github.com/your-username/AemeathVoice
- 📖 详细文档：见主仓库 `docs/` 目录
- 🐛 问题反馈：GitHub Issues
