# 从零训练自己的模型

本指南介绍如何用自己的音频数据训练一个 GPT-SoVITS 语音克隆模型。

## 训练流程概览

```
原始音频 (wav/mp3)
    ↓ 1. 数据准备
标准化音频 (22050Hz, mono, 16-bit)
    ↓ 2. ASR 标注
带字幕的音频 + filelists
    ↓ 3. 特征提取
3-bert (文本) + 4-cnhubert + 5-wav32k + 6-semantic
    ↓ 4. 模型训练
S1 (GPT 语义模型) + S2 (SoVITS 声学模型)
    ↓ 5. 推理测试
最终模型
```

## 第一步：数据准备

### 音频要求

- **格式**：WAV（22050Hz，mono，16-bit）
- **时长**：单条 1-15 秒（推荐 3-8 秒）
- **总量**：≥ 20 分钟（推荐 30-60 分钟）
- **质量**：清晰人声，**无背景音乐 / 噪音**
- **数量**：≥ 100 条（推荐 200+）

### 音频切分工具

**推荐使用 [UVR5](https://github.com/Anjok07/ultimatevocalremovergui) 分离人声**

切分原则：
- 在**自然停顿**处切分
- 不要切到字中间
- 同一段情感 / 场景的连续段落优先放一起

### 文件命名

推荐格式：`角色名_序号.wav`，例如：
```
basic_121001.wav
basic_121002.wav
basic_121003.wav
```

---

## 第二步：ASR 自动字幕标注

### 使用 GPT-SoVITS 自带的 ASR 工具

```bash
# 进入 GPT-SoVITS 目录
cd GPT-SoVITS

# 启动 WebUI
python webui.py
```

访问 `http://localhost:7860`，选择 "0a-前置数据收集工具" 标签页：
1. 设置音频目录
2. 选择 ASR 模型（推荐 `达摩 ASR` 或 `Whisper`）
3. 点击 "开始处理"

### 命令行批量 ASR

也可以用 `tools/asr/` 下的工具直接批量处理：

```bash
python tools/asr/run_asr.py \
    --input_dir /path/to/wavs \
    --output_file asr_results.json \
    --model medium
```

### 准备 filelists

创建 `train.list` 和 `val.list`（按 9:1 划分）：

```
# filelists/train.list（每行：wav_path|speaker|language|text）
basic_121001.wav|aemeath|zh|今天天气真好呀
basic_121002.wav|aemeath|zh|我们去冒险吧
...
```

---

## 第三步：特征提取

### 使用预处理脚本

由于 GPT-SoVITS 原版脚本在 Windows + Python 3.12 上有兼容性问题，本项目附带了一个修复版本 `scripts/run_preprocess_v5.py`。

```bash
# Step 1: 文本特征（BERT）
python scripts/run_preprocess_v5.py --step 1

# Step 2: 音频特征（HuBERT + wav32k）
python scripts/run_preprocess_v5.py --step 2

# Step 3: 语义 token（SoVITS）
python scripts/run_preprocess_v5.py --step 3
```

### 产物清单

特征提取完成后，`filelists/` 目录下应该有：
```
filelists/
├── train.list
├── val.list
├── 3-bert/
│   ├── basic_121001.pt
│   └── ...
├── 4-cnhubert/
│   ├── basic_121001.pt
│   └── ...
├── 5-wav32k/
│   ├── basic_121001.wav
│   └── ...
├── 2-name2text-0.txt
└── 6-name2semantic-0.tsv
```

### 验证产物完整性

```python
import os
with open('filelists/train.list', encoding='utf-8') as f:
    lines = [l.strip().split('|') for l in f if l.strip()]
for parts in lines:
    name = parts[0].split('/')[-1].replace('.wav', '')
    assert os.path.isfile(f'filelists/3-bert/{name}.pt'), f'缺少 BERT 特征: {name}'
    assert os.path.isfile(f'filelists/4-cnhubert/{name}.pt'), f'缺少 HuBERT 特征: {name}'
    assert os.path.isfile(f'filelists/5-wav32k/{name}.wav'), f'缺少 wav32k: {name}'
print(f'✓ {len(lines)} 条数据全部就绪')
```

---

## 第四步：模型训练

### S1 训练（GPT 语义模型）

创建配置文件 `GPT_SoVITS/configs/myspeaker_s1.yaml`，关键参数：

```yaml
# 数据
train_files: "filelists/train.list.cleaned"
val_files: "filelists/val.list.cleaned"

# 模型
model:
  vocab_size: 1025          # 音频 token
  phoneme_vocab_size: 732   # 文本 token

# 训练
training:
  epochs: 20
  batch_size: 4
  learning_rate: 0.01       # 初始高，随后衰减到 0.0001
  half_weights_save_dir: "Logs/s2/myspeaker/weights"
```

启动训练：

```bash
cd GPT-SoVITS
python launch_aemeath_train.py s1
```

> ⚠️ **Windows 重要**：必须使用 `if __name__ == '__main__':` 保护 launcher，否则 spawn DataLoader 会无限递归。

### S2 训练（SoVITS 声学模型）

创建配置文件 `GPT_SoVITS/configs/myspeaker_s2.json`：

```json
{
  "train": {
    "epochs": 20,
    "batch_size": 4,
    "learning_rate": 0.0001,
    "save_every_epoch": 1,
    "if_save_latest": true,
    "if_save_every_weights": true,
    "gpu_numbers": "0",
    "name": "myspeaker",
    "save_weight_dir": "Logs/s2/myspeaker/weights"
  },
  "data": {
    "exp_dir": "filelists",
    "train_files": "filelists/train.list",
    "val_files": "filelists/val.list",
    "s2_ckpt_dir": "filelists/logs_s2_v2"
  },
  "model": {
    "version": "v2",
    "speech_encoder": "vec768l12"
  }
}
```

启动训练：

```bash
cd GPT-SoVITS
python run_s2_single_gpu.py
```

> ⚠️ **Windows 重要**：DDP 在 Windows 单卡上会崩溃，必须用 `run_s2_single_gpu.py` 模拟器绕过 `mp.spawn`。

### 训练监控

```bash
tensorboard --logdir Logs/
```

访问 `http://localhost:6006` 查看 loss 曲线。

---

## 第五步：提取推理权重 + 测试

S2 训练产物（`G_*.pth`）包含优化器状态等冗余信息，需要提取为推理权重：

```python
# scripts/extract_weights.py
import torch
ckpt = torch.load("filelists/logs_s2_v2/G_xxxxx.pth", map_location="cpu")
torch.save({
    "weight": ckpt["weight"],
    "config": ckpt["config"],
    "model": "v2"
}, "models/s2/myspeaker_e20.pth")
```

然后跑推理测试：

```bash
python scripts/aemeath_say.py --text "训练成功！这是我的声音" --ref-audio wavs/sample.wav
```

---

## 训练参数推荐

| 数据量 | 推荐 Epoch | 训练时长（RTX 5070 Ti） |
|--------|-----------|-----------------------|
| < 100 条 | 30-50 | 1-3 小时 |
| 100-200 条 | 15-25 | 1-2 小时 |
| 200-500 条 | 10-20 | 2-4 小时 |
| > 500 条 | 5-15 | 2-6 小时 |

---

## 常见训练问题

### Loss 不下降？
- 检查学习率（S1 应该是 0.01 起）
- 检查 BERT / HuBERT 特征是否完整
- 检查数据标签是否正确

### 合成效果差？
- 增加训练轮次
- 提高数据质量（更干净的人声、更准确的字幕）
- 尝试多个参考音频

### CUDA Out of Memory？
- 减小 `batch_size`（推荐 2-4）
- 使用 `s2_train_v3_lora.py`（LoRA 显存友好）

更多问题排查请查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
