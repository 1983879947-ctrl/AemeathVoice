# 更新日志

所有重要的项目变更都会记录在此。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 添加 LoRA 训练脚本
- 支持流式 HTTP API（WebSocket）
- 添加 WebUI 启动脚本
- 模型量化版本（int8）

## [1.0.0] - 2026-09-02

### 新增
- 🎉 首次发布爱弥斯语音克隆模型
- 提供 20 epoch 训练的 S1 / S2 模型
- CLI 推理工具 `scripts/aemeath_say.py`
- FastAPI HTTP 服务 `scripts/inference_api.py`
- 完整文档（安装 / 使用 / 训练 / API / 故障排查 / 上传指南）
- GitHub Actions CI 配置
- Hugging Face 模型卡片
- 2 个示例音频输出（《将进酒》《再别康桥》）

### 修复
- 兼容 Python 3.12（jieba_fast / G2PW / torchcodec 补丁）
- 兼容 Windows + RTX 50 系 GPU
- PyTorch 2.6+ weights_only 加载问题

### 训练细节
- 训练数据：192 wav（25.7 分钟）
- 预训练底座：s1bert25hz-5kh-longer (epoch 12) + s2G2333k
- 训练硬件：RTX 5070 Ti 12GB
- 训练时长：约 10 分钟/epoch

[Unreleased]: https://github.com/your-username/AemeathVoice/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-username/AemeathVoice/releases/tag/v1.0.0
