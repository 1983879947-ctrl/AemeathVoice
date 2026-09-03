# GitHub 上传指南

> 本指南介绍如何把这个项目上传到 GitHub。**注意：模型文件超过 100MB，GitHub 默认不允许，需要特殊处理。**

## 目录

1. [方案选择](#方案选择)
2. [方案 A：Git LFS（推荐）](#方案-a-git-lfs推荐)
3. [方案 B：Hugging Face + GitHub 引用](#方案-bhugging-face--github-引用)
4. [方案 C：模型分离仓库](#方案-c模型分离仓库)
5. [首次发布步骤](#首次发布步骤)

---

## 方案选择

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **A. Git LFS** | 用户一个仓库全搞定 | Git LFS 有免费额度限制（1GB 存储 / 1GB 流量） | 个人项目、下载量不大 |
| **B. HF + 引用** | 完全免费、无限制 | 用户需要去 HF 下载模型 | 长期维护、多人使用 |
| **C. 模型独立仓库** | 模型代码分离、清晰 | 需要维护 2 个仓库 | 多人协作 |

**本项目推荐方案 B**：把模型上传到 Hugging Face Hub（完全免费、无限制），代码放 GitHub，用户 clone 后一键下载模型。

---

## 方案 A：Git LFS（推荐）

### 1. 安装 Git LFS

**Windows**：从 [git-lfs.github.com](https://git-lfs.github.com/) 下载安装
**Linux**：`sudo apt install git-lfs`
**macOS**：`brew install git-lfs`

### 2. 初始化 LFS

```bash
git lfs install
```

### 3. 标记大文件

```bash
# 进入项目目录
cd E:/AemeathVoice

# 把大模型文件标记为 LFS（.gitattributes 已经预先配置好了）
# 实际只需要执行：
git lfs track "models/s1/*.ckpt"
git lfs track "models/s2/*.pth"
```

### 4. 创建 GitHub 仓库

1. 访问 https://github.com/new
2. 仓库名：`AemeathVoice`（或你喜欢的名字）
3. **不要**勾选 "Initialize with README"（我们已经写了）
4. 选择 Public（公开）或 Private（私有）
5. 创建

### 5. 推送代码

```bash
cd E:/AemeathVoice
git init
git add .
git commit -m "feat: 初始化爱弥斯语音模型项目"
git branch -M main
git remote add origin https://github.com/你的用户名/AemeathVoice.git
git push -u origin main
```

推送 LFS 文件可能需要几分钟（取决于网速）。

### ⚠️ Git LFS 免费额度

| 账号类型 | 存储 | 流量 / 月 |
|---------|------|----------|
| Free | 1 GB | 1 GB |
| Pro ($4/月) | 50 GB | 50 GB |

本项目总模型约 231MB，**Free 账号完全够用**。但如果用户下载量很大（>1GB/月），会超额。

---

## 方案 B：Hugging Face + GitHub 引用（推荐用于长期）

### 第一步：上传模型到 Hugging Face

#### 1. 注册账号
访问 https://huggingface.co/join 注册

#### 2. 创建模型仓库
访问 https://huggingface.co/new，选择 "Model"

- 仓库名：`aemeath-voice`（推荐）
- 类型：Public
- License：MIT

#### 3. 安装 huggingface_hub
```bash
pip install huggingface_hub
huggingface-cli login  # 输入你的 token
```

#### 4. 上传模型文件
```bash
# 使用 Python 上传
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.upload_folder(
    folder_path='./models',
    repo_id='你的用户名/aemeath-voice',
    repo_type='model',
    commit_message='上传爱弥斯语音模型'
)
"
```

或者用 CLI：
```bash
# 单个文件
huggingface-cli upload 你的用户名/aemeath-voice models/s1/aemeath-e20.ckpt models/s1/
huggingface-cli upload 你的用户名/aemeath-voice models/s2/aemeath_e20.pth models/s2/
huggingface-cli upload 你的用户名/aemeath-voice models/reference/basic_121068.wav models/reference/

# 或上传整个目录
huggingface-cli upload 你的用户名/aemeath-voice ./models --repo-type model
```

#### 5. 模型下载地址
- Hugging Face URL：`https://huggingface.co/你的用户名/aemeath-voice`
- 直接下载：
  ```
  https://huggingface.co/你的用户名/aemeath-voice/resolve/main/s1/aemeath-e20.ckpt
  ```

### 第二步：写一个自动下载脚本

创建 `scripts/download_models.py`：

```python
"""从 Hugging Face 自动下载爱弥斯模型"""
from pathlib import Path
from huggingface_hub import snapshot_download

REPO_ID = '你的用户名/aemeath-voice'  # ← 改成你的 HF 用户名
LOCAL_DIR = Path(__file__).parent.parent / 'models'

def download():
    LOCAL_DIR.mkdir(exist_ok=True)
    print(f'📥 从 Hugging Face 下载模型: {REPO_ID}')
    snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(LOCAL_DIR),
        local_dir_use_symlinks=False,
        allow_patterns=['*.ckpt', '*.pth', '*.wav']
    )
    print(f'✅ 模型已下载到: {LOCAL_DIR}')

if __name__ == '__main__':
    download()
```

### 第三步：在 README 写明

更新 README.md，在"快速开始"加一步：

```markdown
### 3.5 下载模型

如果模型不在本地（第一次使用），自动从 Hugging Face 下载：

\`\`\`bash
pip install huggingface_hub
python scripts/download_models.py
\`\`\`
```

---

## 方案 C：模型分离仓库

适合不想用 LFS / HF 的场景：

### 1. 创建两个仓库

- `你的用户名/AemeathVoice` - 代码（本项目，去掉 models/）
- `你的用户名/aemeath-voice-models` - 仅模型

### 2. 模型仓库结构

```
aemeath-voice-models/
├── README.md
└── models/
    ├── s1/aemeath-e20.ckpt
    ├── s2/aemeath_e20.pth
    └── reference/basic_121068.wav
```

### 3. 模型仓库的 README.md

```markdown
# Aemeath Voice - Models

这是 [AemeathVoice](https://github.com/你的用户名/AemeathVoice) 项目的模型权重仓库。

## 下载

\`\`\`bash
# 单文件下载
wget https://github.com/你的用户名/aemeath-voice-models/releases/download/v1.0/s1-aemeath-e20.ckpt
\`\`\`

或访问 [Releases 页面](https://github.com/你的用户名/aemeath-voice-models/releases) 下载 ZIP。

## Releases 方式

由于 GitHub 单文件 100MB 限制，本仓库通过 Release 附件分发模型：

\`\`\`bash
# 下载最新 release 的所有模型
wget https://github.com/你的用户名/aemeath-voice-models/archive/refs/tags/v1.0.tar.gz
\`\`\`
```

### 4. 用户使用方式

```bash
git clone https://github.com/你的用户名/AemeathVoice
cd AemeathVoice
git clone https://github.com/你的用户名/aemeath-voice-models models
# 或者从 Release 下载模型并解压到 models/
```

---

## 首次发布步骤（推荐方案 B 流程）

### 1. 准备 GitHub 仓库

```bash
# 在 GitHub 创建空仓库（不带 README、.gitignore、license）

# 在本地初始化
cd E:/AemeathVoice
git init
git add .
git commit -m "feat: 初始化项目

- 提供 20 epoch 训练的爱弥斯语音模型
- 包含 CLI / Python / HTTP API 三种调用方式
- 完整的中文文档和安装指南"
git branch -M main
git remote add origin https://github.com/你的用户名/AemeathVoice.git
git push -u origin main
```

### 2. 上传模型到 Hugging Face

```bash
# 安装并登录
pip install huggingface_hub
huggingface-cli login

# 上传
python scripts/download_models.py  # 反向操作，先上传
```

或者手动：

```bash
# 用 git 上传（HF 也支持 git）
git clone https://huggingface.co/你的用户名/aemeath-voice
cd aemeath-voice
cp -r ../AemeathVoice/models/* .
git add . && git commit -m "上传模型" && git push
```

### 3. 标记 Release（可选）

在 GitHub 仓库页 → Releases → Create a new release：
- Tag: `v1.0.0`
- Title: `Aemeath Voice v1.0 - 初始发布`
- Description: 复制 README 内容

### 4. 配置 GitHub Pages（可选）

把文档网站化：
- Settings → Pages → Source: `main` branch, `/docs` folder
- 文档地址：`https://你的用户名.github.io/AemeathVoice/`

---

## 常见问题

### ❌ Push 时报错 "File exceeds 100MB"

**原因**：没有用 LFS 或分离上传

**修复**：
```bash
# 方案 A: 用 LFS
git lfs install
git lfs track "models/s1/*.ckpt"
git add .gitattributes
git add models/
git commit -m "feat: 用 LFS 管理模型"
git push

# 方案 B: 从仓库移除大文件，改成下载
git rm --cached models/s1/aemeath-e20.ckpt
echo "models/s1/" >> .gitignore
git commit --amend
git push
```

### ❌ HF 上传失败 "401 Unauthorized"

**修复**：
```bash
huggingface-cli logout
huggingface-cli login
# 重新输入 token，确保有 write 权限
```

### ❌ LFS 上传很慢

**修复**：使用镜像
```bash
# 设置 LFS endpoint（如果在中国大陆）
git config --global lfs.url https://gh-proxy.com/https://github.com/用户名/仓库
```

---

## 推荐最终方案

**对个人项目**：方案 A（Git LFS）
**对长期维护**：方案 B（HF + GitHub）
**对团队协作**：方案 C（分离仓库）

本项目代码本身已经预留好了 `.gitattributes`（LFS 配置）和 `scripts/inference_api.py` 中模型路径的回退逻辑，无论你选哪个方案都能直接用。
