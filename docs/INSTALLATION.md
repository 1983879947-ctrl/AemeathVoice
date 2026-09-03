# 安装指南

本指南详细介绍 Aemeath Voice 模型的安装步骤。

## 目录

1. [环境要求](#环境要求)
2. [安装 GPT-SoVITS](#安装-gpt-sovits)
3. [下载预训练模型](#下载预训练模型)
4. [部署 Aemeath Voice](#部署-aemeath-voice)
5. [Python 3.12 兼容性问题](#python-312-兼容性问题)
6. [验证安装](#验证安装)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11, Linux, macOS |
| Python | 3.10 / 3.11（推荐），3.12（需打补丁） |
| GPU | NVIDIA GPU（推荐），显存 ≥ 6GB |
| CUDA | 12.x（与 PyTorch 2.1+ 匹配） |
| 内存 | ≥ 8GB |
| 硬盘 | ≥ 10GB（包含预训练模型） |

### Windows + RTX 50 系用户特别提示

如果你使用的是 RTX 5070 Ti / 5080 / 5090 等 50 系显卡：
- 必须使用 PyTorch 2.7+（支持 sm_120 架构）
- 建议 Python 3.12.10

---

## 安装 GPT-SoVITS

### 1. 克隆官方仓库

```bash
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
```

### 2. 创建虚拟环境

**Windows**：
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS**：
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装 PyTorch（CUDA 12.x）

```bash
# CUDA 12.x
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CUDA 12.8（50 系显卡推荐）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### 4. 安装 GPT-SoVITS 依赖

```bash
pip install -r requirements.txt
pip install -r requirements_extra.txt  # GPT-SoVITS 额外依赖
```

---

## 下载预训练模型

Aemeath Voice 是**微调模型**，必须配合 GPT-SoVITS 官方预训练底座使用。

### 方法一：从官方仓库下载（推荐）

1. 访问 [GPT-SoVITS 官方文档](https://github.com/RVC-Boss/GPT-SoVITS)
2. 下载以下文件到 `GPT-SoVITS/GPT_SoVITS/pretrained_models/`：
   - `s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt` (约 700MB)
   - `s2G2333k.pth` (约 600MB)
   - `chinese-roberta-wwm-ext-large/` (约 1.3GB)
   - `chinese-hubert-base/` (约 360MB)
3. 下载 `G2PWModel` 模型到 `GPT-SoVITS/GPT_SoVITS/text/G2PWModel/` (约 610MB)

### 方法二：使用一键下载脚本

GPT-SoVITS 提供了一键脚本：
```bash
python download_models.bat  # Windows
bash download_models.sh     # Linux/macOS
```

---

## 部署 Aemeath Voice

把本项目的关键目录复制到 GPT-SoVITS 仓库根目录：

### 方法一：直接复制

```bash
# 在 AemeathVoice 项目根目录执行
cp -r models/ ../GPT-SoVITS/
cp -r scripts/ ../GPT-SoVITS/
cp -r examples/ ../GPT-SoVITS/
```

### 方法二：符号链接（推荐，便于模型更新）

**Windows（PowerShell，需管理员）**：
```powershell
New-Item -ItemType SymbolicLink -Path "..\GPT-SoVITS\models" -Target "$PWD\models"
New-Item -ItemType SymbolicLink -Path "..\GPT-SoVITS\scripts" -Target "$PWD\scripts"
```

**Linux/macOS**：
```bash
ln -s "$(pwd)/models" ../GPT-SoVITS/models
ln -s "$(pwd)/scripts" ../GPT-SoVITS/scripts
```

---

## Python 3.12 兼容性问题

GPT-SoVITS 本身在 Python 3.12 上有一些兼容性问题。本项目已包含必要补丁：

### 问题 1：`jieba_fast` 未适配 Python 3.12

**症状**：
```
ModuleNotFoundError: No module named 'jieba_fast'
```

**修复**：项目脚本（`aemeath_say.py`）已自动 monkey-patch，使用 `jieba` 替代。

### 问题 2：NLTK 资源缺失

**症状**：
```
Resource cmudict not found.
Resource averaged_perceptron_tagger_eng not found.
```

**修复**：脚本会自动复制/下载缺失资源。也可手动执行：
```bash
python -c "import nltk; nltk.download('cmudict'); nltk.download('averaged_perceptron_tagger_eng')"
```

### 问题 3：torchcodec DLL 错误

**症状**：
```
OSError: [WinError 126] 找不到指定的模块。Error loading "torchcodec" or "ffmpeg"
```

**修复**：脚本使用 `soundfile` 库替代 `torchaudio.load`，无需额外操作。

### 问题 4：PyTorch 2.6+ `weights_only=True` 错误

**症状**：
```
_pickle.UnpicklingError: Weights only load failed.
WeightsUnpickler error: unsupported operand type(s) for //.
```

**修复**：脚本启动时会自动调用 `torch.serialization.add_safe_globals(...)`。

---

## 验证安装

运行以下命令验证一切就绪：

```bash
cd GPT-SoVITS
python scripts/aemeath_say.py --text "测试一下爱弥斯的声音"
```

成功的话会输出：
```
加载模型...
模型加载完成 (15.3s)
合成完成 (1.2s) -> output.wav (3.5s)
```

如果遇到错误，请查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
