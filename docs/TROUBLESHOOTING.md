# 常见问题排查

## 目录

1. [安装相关](#安装相关)
2. [模型加载错误](#模型加载错误)
3. [推理错误](#推理错误)
4. [训练错误](#训练错误)
5. [性能问题](#性能问题)

---

## 安装相关

### `ModuleNotFoundError: No module named 'jieba_fast'`

**原因**：jieba_fast 未适配 Python 3.12

**修复**：项目脚本已自动 monkey-patch。如果你看到此错误，说明你没用项目自带的脚本。

---

### `FileNotFoundError: [Errno 2] No such file or directory: 'GPT_SoVITS/text/G2PWModel'`

**原因**：相对路径解析错误（cwd 不是 GPT-SoVITS 根目录）

**修复**：
1. 确保在 GPT-SoVITS 仓库根目录运行
2. 或使用项目提供的修复版脚本 `scripts/aemeath_say.py`

---

### `OSError: Repo id must be in form 'repo_name'`

**原因**：transformers 把相对路径当 HuggingFace repo ID

**修复**：设置环境变量为绝对路径：
```python
import os
os.environ['bert_path'] = '/abs/path/to/chinese-roberta-wwm-ext-large'
```

---

### `OSError: [WinError 126] 找不到指定的模块`

**原因**：torchcodec DLL 缺失（Python 3.12 + torchaudio 2.x）

**修复**：使用 `soundfile` 替代 `torchaudio.load`（项目脚本已处理）

---

## 模型加载错误

### `_pickle.UnpicklingError: Weights only load failed`

**原因**：PyTorch 2.6+ 默认 `weights_only=True`，但模型包含 `pathlib.WindowsPath`

**修复**：
```python
import torch
import pathlib
torch.serialization.add_safe_globals([pathlib.WindowsPath, pathlib.Path])
```

（项目脚本已自动处理）

---

### `RuntimeError: Attempting to deserialize object on CUDA device 0`

**原因**：ckpt 在 GPU 上训练，加载时环境没有 GPU

**修复**：
```python
ckpt = torch.load(path, map_location="cpu")  # 强制 CPU 加载
```

---

### `size mismatch for ... `

**原因**：模型版本不匹配

**修复**：
- 确认 `aemeath-e20.ckpt` 配套 `aemeath_e20.pth`（不要混用不同 epoch）
- 确认 GPT-SoVITS 版本与训练时一致

---

## 推理错误

### `Resource cmudict not found`

**修复**：
```python
import shutil, os
src = '/path/to/GPT-SoVITS/GPT_SoVITS/text/cmudict.rep'
dst = os.path.expanduser('~/AppData/Roaming/nltk_data/corpora/cmudict/cmudict')
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copy(src, dst)
```

（项目脚本已自动处理）

---

### `Resource averaged_perceptron_tagger_eng not found`

**修复**：
```python
import nltk
nltk.download('averaged_perceptron_tagger_eng', download_dir=os.path.expanduser('~/AppData/Roaming/nltk_data'))
```

---

### 中文文本生成英文？

**原因**：`--lang` 参数错误

**修复**：
```bash
# 正确
python aemeath_say.py --text "你好" --lang zh

# 错误（会被当英文处理）
python aemeath_say.py --text "你好"
```

---

### 输出为空 / 静音

**可能原因**：
1. 参考音频时长 < 1 秒 → 换用 3-10 秒的参考音频
2. 参考文本不准确 → 修正 `--ref-text`
3. 模型损坏 → 重新下载

---

### 合成很慢（> 30 秒 / 句）

**优化方法**：
1. **启用 CUDA Graph**（RTX 50 系）：脚本已默认启用
2. **关闭不必要的安全加载**：如果你的模型来源可信，可以去掉 `add_safe_globals`
3. **使用更短的文本**：拆成多段分别合成

---

## 训练错误

### S2 训练崩溃（Windows）

**症状**：`Segmentation Fault` 或 DDP 多进程卡死

**原因**：Windows + gloo + 单卡 DDP 不兼容

**修复**：使用 `run_s2_single_gpu.py`（项目附带）：
```bash
python run_s2_single_gpu.py
```

---

### S1 训练 DataLoader 死循环

**症状**：CPU 跑满但 GPU 利用率 0

**原因**：launcher 没有 `if __name__ == '__main__':` 保护

**修复**：项目提供的 `launch_aemeath_train.py` 已修复。

---

### CUDA Out of Memory

**修复**：
1. 减小 `batch_size`（从 4 → 2 → 1）
2. 使用 LoRA 训练：`s2_train_v3_lora.py`
3. 启用梯度累积：
   ```python
   training.accumulate_grad_batches = 4
   ```

---

### Loss 不下降 / NaN

**排查步骤**：
1. 检查数据标签（用 ASR 重新校对）
2. 检查 BERT 特征完整性
3. 降低学习率（S1 试试 0.001）
4. 检查预训练底座是否正确加载

---

## 性能问题

### GPU 利用率只有 30%

**原因**：DataLoader worker 不够 / 文本太长等待 GPU

**修复**：
```yaml
training:
  num_workers: 4
  prefetch_factor: 2
```

---

### 显存只用了 5GB（GPU 是 12GB）

**修复**：可以增大 batch_size 到 6-8 加速训练

---

### 推理延迟高（> 5 秒）

**可能原因**：
1. **首次加载**：模型加载 15-20 秒属正常
2. **GPU 不工作**：`nvidia-smi` 确认 GPU 利用率
3. **CUDA 版本不匹配**：PyTorch 和 CUDA 版本必须一致
4. **文本过长**：超过 300 字的文本会切分成多段

---

## 其他问题

### Windows 控制台中文乱码

**修复**：设置环境变量
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

或在脚本开头加：
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

### macOS 上 torch 无法使用 MPS

GPT-SoVITS 暂不支持 MPS 后端，请使用 CPU 或外接 NVIDIA GPU（eGPU）。

---

### 找不到对应文档的错误？

欢迎提交 [Issue](https://github.com/your-repo/AemeathVoice/issues)，我们会补充。
