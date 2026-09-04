# -*- coding: utf-8 -*-
"""创建 GitHub Release（不上传资产，资产用 curl 传）。Token 从 git credential fill 读入，不落盘明文。"""
import json
import subprocess
import sys
import urllib.request

REPO = "1983879947-ctrl/AemeathVoice"
TAG = "v1.0.0"

NOTES = """# 爱弥斯语音 · Aemeath Voice v1.0

鸣潮角色**爱弥斯**的 GPT-SoVITS 语音克隆 · EXE 一键分发版。

## 下载（3 个分卷，全部下载后解压到同一目录）

| 文件 | 内容 | 大小 |
|---|---|---|
| `part1_runtime.zip` | AemeathVoice.exe + Python 运行时 + 代码 | ~576 MB |
| `part2_models.zip` | 爱弥斯训练模型 + GPT-SoVITS v2 底座 | ~1.8 GB |
| `part3_g2pw_text.zip` | G2PW 多音字模型（605MB）+ 文本前端 | ~610 MB |

**解压**：三个 zip 解压到同一个文件夹，得到完整的 `AemeathVoice/` 目录（3.1 GB）。

## 使用

1. 双击 `AemeathVoice\\AemeathVoice.exe` —— 自动启动并打开浏览器 Web 控制台
2. 输入文本 → 点「合成语音」→ 播放
3. 关闭：双击 `stop.bat`

> 需要 NVIDIA 显卡（CUDA）。首次启动加载模型约 10-20 秒。

## 从源码部署

见仓库 [README_EXE.md](https://github.com/1983879947-ctrl/AemeathVoice/blob/main/README_EXE.md) 的「从零部署」一节。

## 采样参数

默认 `top_k=20, top_p=0.6, temperature=0.6`（对齐 GPT-SoVITS webui 默认值，听感稳定）。
"""
# noqa: 上面表格里的大小是预估值，若相差大可后续编辑

creds = subprocess.run(
    ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
    capture_output=True, text=True, timeout=30, cwd=r"E:\AemeathVoice",
).stdout
token = dict(line.split("=", 1) for line in creds.strip().splitlines() if "=" in line)["password"]

body = {"tag_name": TAG, "target_commitish": "main", "name": "爱弥斯语音 v1.0 · EXE 分发版",
        "body": NOTES, "draft": False, "prerelease": False}
req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/releases",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json",
             "Content-Type": "application/json", "User-Agent": "aemeath-release"},
)
try:
    with urllib.request.urlopen(req) as r:
        rel = json.load(r)
        print(json.dumps({"id": rel["id"], "html_url": rel["html_url"],
                          "upload_url": rel["upload_url"].split("{")[0]}, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode("utf-8")[:500])
    sys.exit(1)
