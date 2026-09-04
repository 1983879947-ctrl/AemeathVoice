# 爱弥斯语音 · EXE 分发版

## 一键下载（Release v1.0.0）

三个分卷全部下载后解压到同一目录：

| 分卷 | 内容 | 大小 | 一键下载 |
|------|------|------|----------|
| part1 | EXE + Python 运行时 + 代码 | 576 MB | [⬇️ 下载](https://github.com/1983879947-ctrl/AemeathVoice/releases/download/v1.0.0/AemeathVoice_v1.0.0_part1_runtime.zip) |
| part2 | 爱弥斯模型 + GPT-SoVITS v2 底座 | 1.8 GB | [⬇️ 下载](https://github.com/1983879947-ctrl/AemeathVoice/releases/download/v1.0.0/AemeathVoice_v1.0.0_part2_models.zip) |
| part3 | G2PW 多音字模型 + 文本前端 | 608 MB | [⬇️ 下载](https://github.com/1983879947-ctrl/AemeathVoice/releases/download/v1.0.0/AemeathVoice_v1.0.0_part3_g2pw_text.zip) |

## 从零部署（拿到源码后）

本仓库不含预训练底座与 G2PW 模型（体积原因），源码部署需自行补齐：

1. **克隆仓库**（模型走 Git LFS，需先 `git lfs install`）
   ```bash
   git clone https://github.com/1983879947-ctrl/AemeathVoice.git
   cd AemeathVoice
   ```
   克隆后得到：爱弥斯训练成果（`models/s1/*.ckpt`、`models/s2/*.pth`）、参考音频、精简版推理代码（`AemeathVoice_Portable/gpt_sovits/`）。

2. **补齐 GPT-SoVITS v2 预训练底座** → 放到 `AemeathVoice_Portable/models/pretrained/`
   - `gsv-v2final-pretrained/`（GPT + SoVITS 底座）
   - `chinese-roberta-wwm-ext-large/`（中文 BERT）
   - `chinese-hubert-base/`（Hubert 特征提取）
   来源：GPT-SoVITS 官方 Releases（v2 底座包）+ HuggingFace。

3. **补齐 G2PW 多音字模型** → 放到 `AemeathVoice_Portable/text/G2PWModel/`
   - 来源：https://www.modelscope.cn/models/kamiorinn/g2pw （`G2PWModel_1.1.zip`，605 MB）

4. **启动 API**（Python 3.10/3.11 + CUDA）：
   ```bash
   python api/inference_api.py --port 9880
   ```

5. **打包 EXE**：见下方 [重新打包](#重新打包)。`prepare_dist.bat` 可一键复制运行时文件。

> 只要 `dist/AemeathVoice/` 完整目录的人无需以上步骤，解压即用。

## 一键使用

1. **解压** `AemeathVoice/` 目录到任意位置（推荐 `D:\AemeathVoice\`）
2. **双击** `AemeathVoice\AemeathVoice.exe` —— 自动启动 API + 打开浏览器到 Web 控制台
3. 在 Web 控制台输入文本 → 点 "合成语音" → 听音频

第一次启动需要 10-20 秒加载模型，之后秒响应。

## 文件结构

```
AemeathVoice/                         ← 解压后的目录（3.1 GB）
├── AemeathVoice.exe                  ← 双击启动这个（1.6 MB）
├── AemeathVoice.log                  ← 启动日志（每次启动覆盖）
├── start.bat                         ← 命令行启动脚本（双击也行）
├── stop.bat                          ← 关闭所有相关进程
├── _internal/                        ← Python + 代码（684 MB）
│   ├── python311.dll 等
│   └── AV/
│       ├── api/inference_api.py      ← FastAPI 服务
│       ├── scripts/launch_aemeath_api.py
│       ├── web/index.html            ← Web 控制台（也通过 API 提供）
│       ├── gpt_sovits/               ← 内嵌的 GPT-SoVITS 推理代码
│       └── text/                     ← 文本处理（cmudict 等小文件）
├── models/                           ← 训练好的模型（1.8 GB）
│   ├── s1/aemeath-e20.ckpt
│   ├── s2/aemeath_e20.pth
│   ├── reference/basic_121068.wav    ← 参考音频
│   └── pretrained/                   ← GPT-SoVITS 预训练底座
└── text/                             ← G2PW 多音字模型（610 MB）
    └── G2PWModel/                    ← 自动加载（多音字消歧）
```

## API 端点

| 端点 | 用途 |
|------|------|
| `GET /` | Web 控制台（HTML） |
| `GET /health` | 健康检查 |
| `GET /docs` | Swagger API 文档 |
| `POST /tts` | 合成语音 |

**TTS 调用示例**：
```bash
curl -X POST http://127.0.0.1:9880/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "一行日辉是爱弥斯最重要的人哦~",
    "text_language": "zh",
    "top_k": 20,
    "top_p": 0.6,
    "temperature": 0.6
  }' \
  --output out.wav
```

## 重新打包

如果有源码改动，重新构建 EXE：

```bash
# 1. 安装 PyInstaller
"C:\Users\27298\AppData\Local\Programs\Python\Python311\python.exe" -m pip install pyinstaller

# 2. 清理旧 build
python -c "import shutil; shutil.rmtree('E:/AemeathVoice/build', ignore_errors=True); shutil.rmtree('E:/AemeathVoice/dist', ignore_errors=True)"

# 3. 打包（耗时约 10-20 秒）
cd "E:\AemeathVoice"
"C:\Users\27298\AppData\Local\Programs\Python\Python311\python.exe" -m PyInstaller build.spec --noconfirm

# 4. 复制模型（2.4 GB，约 1-3 分钟）
python -c "
import shutil
shutil.copytree('AemeathVoice_Portable/models', 'dist/AemeathVoice/models', dirs_exist_ok=True)
shutil.copytree('AemeathVoice_Portable/text', 'dist/AemeathVoice/text', dirs_exist_ok=True)
"
```

## 启动常用链接

- Web 控制台：http://127.0.0.1:9880/
- Swagger：http://127.0.0.1:9880/docs
- 默认采样参数：`top_k=20, top_p=0.6, temperature=0.6`（对齐 GPT-SoVITS webui 默认）

## 关闭服务

- 关闭 **AemeathVoice.exe** 的命令行窗口
- 或双击 `stop.bat`
- 或在 PowerShell：`taskkill /IM AemeathVoice.exe /F`

## 常见问题

### 启动慢（30+ 秒）
首次启动需要加载 GPT/SoVITS 模型（每次 1-2 GB），后续启动也会 10-20 秒（CUDA 初始化）。

### 端口 9880 被占用
修改 `start.bat` 里的 `--port 9880` 为其他端口（如 9881），同时 `AemeathVoice.py` 里的 `port = 9880` 也要改。

### 浏览器没自动打开
手动访问：http://127.0.0.1:9880/

### 多音字读错
确认 `text/G2PWModel/g2pW.onnx` 存在（605 MB）。日志里会显示 `✅ G2PW 多音字模型已启用`。

## 技术栈

- PyInstaller 6.19 + Python 3.11
- FastAPI 0.100+ / uvicorn
- PyTorch 2.1+ / CUDA 12.x
- transformers 4.x（Hubert）
- GPT-SoVITS v2 模型

## 体积优化

当前 EXE 目录 3.1 GB：
- _internal/AV/：684 MB（代码 + Python）
- models/：1.8 GB（GPT-SoVITS 模型 + 训练成果）
- text/：610 MB（G2PW 多音字模型）

可进一步优化：
1. 删除 `text/G2PWModel/`（600 MB）→ 默认用纯 pypinyin（多音字可能读错）
2. 删除 `models/pretrained/chinese-roberta-wwm-ext-large/` 等大文件（如果用户用其他 BERT）
3. 训练 SOP：把 `models/pretrained/gsv-v2final-pretrained/` 也保留

## 故障排查

启动失败时查看 `AemeathVoice.log`，关键信息：
- `加载 GPT 模型: ...` → 模型路径
- `[API] ERROR:` → API 报错
- `Python: ...` → 用的 Python 解释器

如果 API 一直 `Loading`，可能是：
1. GPU 驱动问题（看有没有 cuda 相关报错）
2. 模型文件损坏（重新下 models/）
3. 端口被占用（关掉其他 AemeathVoice 进程）
