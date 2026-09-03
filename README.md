# 🎤 Aemeath Voice (爱弥斯语音模型)

> 基于 GPT-SoVITS 训练的《鸣潮》游戏角色"爱弥斯"中文语音克隆模型
>
> Clone your favourite voice with 5 lines of code.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch 2.1+](https://img.shields.io/badge/PyTorch-2.1+-ee4c2c.svg)](https://pytorch.org/)
[![CUDA 12.x](https://img.shields.io/badge/CUDA-12.x-76b900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 项目简介

本项目提供了**经过 20 个 epoch 完整训练**的爱弥斯（Aemeath / 爱弥斯）语音克隆模型，可直接通过 GPT-SoVITS 推理框架使用。

- 🎯 **训练数据**：192 条爱弥斯游戏台词，25.7 分钟
- 🧠 **训练轮次**：20 epochs（S1 loss 下降 50%，top-3 准确率提升 60%）
- 🗣️ **音色特点**：温柔知性的少女音，可朗诵 / 唱歌 / 念长文本
- 🚀 **开箱即用**：内置 CLI 工具、HTTP API、Python 函数三种调用方式

## 📦 模型清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `models/s1/aemeath-e20.ckpt` | 149 MB | GPT 语义模型（20 epoch） |
| `models/s2/aemeath_e20.pth` | 82 MB | SoVITS 声学模型推理权重（half precision） |
| `models/reference/basic_121068.wav` | 568 KB | 参考音频（3.38 秒，战斗台词） |

## 🚀 快速开始

### 1. 准备 GPT-SoVITS 环境

由于训练用 GPT-SoVITS，本模型依赖其推理代码。请先安装官方项目：

```bash
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
```

然后按官方文档安装依赖（推荐使用 venv）：
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -r requirements_extra.txt  # GPT-SoVITS 额外依赖
```

> ⚠️ **Python 版本**：建议 3.10 / 3.11（Python 3.12 需要打补丁，详见 [docs/INSTALLATION.md](docs/INSTALLATION.md)）

### 2. 下载预训练模型

模型本身只是微调产物，**还需要 GPT-SoVITS 的预训练底座**（约 4.6 GB）：

| 文件 | 下载地址 |
|------|----------|
| s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt | [GPT-SoVITS 官方仓库](https://github.com/RVC-Boss/GPT-SoVITS) |
| s2G2333k.pth | 同上 |
| chinese-roberta-wwm-ext-large | 同上 |
| chinese-hubert-base | 同上 |
| G2PWModel | 同上 |

把预训练模型放到：
```
GPT-SoVITS/
└── GPT_SoVITS/pretrained_models/
    ├── s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt
    ├── s2G2333k.pth
    ├── chinese-roberta-wwm-ext-large/
    └── chinese-hubert-base/
```

### 3. 复制本项目的模型和脚本

把本项目的 `models/` 整个目录复制到 GPT-SoVITS 仓库下：

```
GPT-SoVITS/
├── GPT_SoVITS/...
├── models/                         <-- 复制过来
│   ├── s1/aemeath-e20.ckpt
│   ├── s2/aemeath_e20.pth
│   └── reference/basic_121068.wav
└── scripts/                        <-- 复制过来
    └── aemeath_say.py
```

### 4. 开始说话！

```bash
# 命令行（最简单）
python scripts/aemeath_say.py --text "你好，我是一行日辉的爱弥斯哦~"

# 想要换个参考音频？
python scripts/aemeath_say.py --text "测试" --ref-audio basic_121068.wav

# 指定输出文件
python scripts/aemeath_say.py --text "飞行雪绒" --output my_voice.wav

# 启动 HTTP API 服务（端口 9880）
python scripts/launch_aemeath_api.py
```

第一次加载需要约 15-20 秒，之后每条文本生成仅需 1-15 秒（取决于长度）。

## 🎯 推理效果示例

| 输入文本 | 输出 |
|---------|------|
| "你好，我是一行日辉的爱弥斯哦~ 来给你唱首歌吧!" | [examples/example_zaibiekangqiao.wav](examples/) |
| "君不见黄河之水天上来，奔流到海不复回"（李白《将进酒》节选） | [examples/example_jiangjinjiu.wav](examples/) |

更多示例音频请查看 [`examples/`](examples/) 目录。

## 📚 进阶文档

- 📖 [详细安装指南（含 Python 3.12 补丁）](docs/INSTALLATION.md)
- 🎛️ [使用说明与参数详解](docs/USAGE.md)
- 🏋️ [从零训练自己的模型](docs/TRAINING.md)
- 🐛 [常见问题排查](docs/TROUBLESHOOTING.md)
- 🔧 [HTTP API 部署](docs/API.md)

## 🛠️ 技术细节

### 训练框架
- **框架**：GPT-SoVITS v2
- **预训练底座**：s1bert25hz-5kh-longer（epoch 12）+ s2G2333k
- **优化器**：AdamW + 动态学习率（S1: 0.01 → 0.0001；S2: 0.0001）
- **Batch Size**：4
- **数据**：192 wav（172 训练 + 20 验证），总时长 25.7 分钟
- **GPU**：NVIDIA RTX 5070 Ti 12GB

### 训练指标
| 指标 | Epoch 1 | Epoch 20 | 提升 |
|------|---------|----------|------|
| S1 Loss | 2.09e+3 | **1.05e+3** | ↓ 50% |
| S1 Top-3 Acc | 0.522 | **0.830** | ↑ 60% |

## 📂 项目结构

```
AemeathVoice/
├── README.md                      # 项目主页（本文件）
├── LICENSE                        # MIT 协议
├── requirements.txt               # Python 依赖
├── .gitignore                     # Git 忽略规则
├── .gitattributes                 # Git LFS 配置（模型文件 >100MB）
├── models/                        # 模型权重
│   ├── s1/aemeath-e20.ckpt        # GPT 语义模型
│   ├── s2/aemeath_e20.pth         # SoVITS 声学模型
│   └── reference/basic_121068.wav # 参考音频
├── scripts/                       # 推理脚本
│   ├── aemeath_say.py             # CLI 一键调用
│   ├── launch_aemeath_api.py      # HTTP API 启动器
│   └── inference_api.py           # FastAPI 服务
├── examples/                      # 示例输出
│   ├── example_jiangjinjiu.wav
│   └── example_zaibiekangqiao.wav
└── docs/                          # 详细文档
    ├── INSTALLATION.md
    ├── USAGE.md
    ├── TRAINING.md
    ├── API.md
    └── TROUBLESHOOTING.md
```

## 🤝 贡献

欢迎贡献更多爱弥斯训练样本（音频 + 字幕），或者提交训练参数调优的 PR！

## ⚖️ 版权与免责声明

- 本项目仅供**个人学习与研究**使用
- 模型基于《鸣潮》游戏角色"爱弥斯"的公开游戏音频训练
- 不得用于商业用途、不得侵犯库洛游戏（KURO GAMES）的知识产权
- 如需商用，请联系游戏官方获取授权

## 🙏 致谢

- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) - 优秀的语音克隆框架
- [库洛游戏 / KURO GAMES](https://www.kurogames.com/) - 《鸣潮》游戏开发
- 一行日辉 ❤️ - 项目发起与模型训练

---

> Made with 💛 by 一行日辉 & 爱弥斯
