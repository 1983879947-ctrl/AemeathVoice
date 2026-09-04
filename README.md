# 🎤 Aemeath Voice (爱弥斯语音模型)

> 基于 GPT-SoVITS 训练的《鸣潮》游戏角色"爱弥斯"中文语音克隆模型
>
> Clone your favourite voice with 5 lines of code.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch 2.1+](https://img.shields.io/badge/PyTorch-2.1+-ee4c2c.svg)](https://pytorch.org/)
[![CUDA 12.x](https://img.shields.io/badge/CUDA-12.x-76b900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![AI Assisted](https://img.shields.io/badge/AI_assisted-WorkBuddy-8A2BE2.svg)](#ai-协作声明)

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

### ⚡ 方式一：一键下载 EXE 分发版（推荐，无需配环境）

三个分卷全部下载后解压即用，不装 Python、不配 CUDA 环境：

| 分卷 | 内容 | 大小 | 一键下载 |
|------|------|------|----------|
| part1 | `AemeathVoice.exe` + Python 运行时 + 全部代码 | 576 MB | [⬇️ 下载](https://github.com/1983879947-ctrl/AemeathVoice/releases/download/v1.0.0/AemeathVoice_v1.0.0_part1_runtime.zip) |
| part2 | 爱弥斯训练模型 + GPT-SoVITS v2 预训练底座 | 1.8 GB | [⬇️ 下载](https://github.com/1983879947-ctrl/AemeathVoice/releases/download/v1.0.0/AemeathVoice_v1.0.0_part2_models.zip) |
| part3 | G2PW 多音字模型 + 文本前端 | 608 MB | [⬇️ 下载](https://github.com/1983879947-ctrl/AemeathVoice/releases/download/v1.0.0/AemeathVoice_v1.0.0_part3_g2pw_text.zip) |

> 也可以到 [Release v1.0.0](https://github.com/1983879947-ctrl/AemeathVoice/releases/tag/v1.0.0) 页面统一下载。

**三步上手：**

1. 三个分卷**解压到同一个目录** → 得到完整的 `AemeathVoice/` 文件夹（3.1 GB）
2. 双击 `AemeathVoice\AemeathVoice.exe` —— 自动启动并打开浏览器 Web 控制台
3. 输入文本 → 点「合成语音」→ 播放 🎵

> - 需要 NVIDIA 显卡（CUDA 12.x）；首次启动加载模型约 10-20 秒，之后秒响应
> - 关闭服务：双击 `stop.bat`，或直接关掉命令行窗口
> - 改端口 / 排错 / API 文档见 [README_EXE.md](README_EXE.md)

### 🧑‍💻 方式二：从源码运行

```bash
git clone https://github.com/1983879947-ctrl/AemeathVoice.git
cd AemeathVoice
# 补齐 GPT-SoVITS 预训练底座与 G2PW 模型 → 见 README_EXE.md「从零部署」
python api/inference_api.py --port 9880    # FastAPI → http://127.0.0.1:9880
```

CLI 一键合成（需先配好 GPT-SoVITS 环境，[详细安装步骤](docs/INSTALLATION.md)）：

```bash
# 命令行（最简单）
python scripts/aemeath_say.py --text "你好，我是一行日辉的爱弥斯哦~"

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

## 🤖 AI 协作声明

本项目由 **一行日辉** 发起并主导，部分开发工作在 AI 编程助手协助下完成：

- **人工完成**：项目创意与规划、训练数据整理与校对、模型训练与效果验收、最终决策
- **AI 协助完成**：GPT-SoVITS 推理代码精简移植与 bug 修复、EXE 打包工程、GUI / Web 控制台、发布脚本与文档编写
- **依赖的开源框架**：[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)（语音克隆训练与推理框架）

训练与推理均基于上述开源框架在本地完成，不涉及任何云端模型服务。

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
