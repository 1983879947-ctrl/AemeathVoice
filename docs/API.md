# HTTP API 部署指南

Aemeath Voice 可以作为 HTTP 服务运行，方便其他应用集成。

## 启动服务

```bash
cd GPT-SoVITS
python scripts/launch_aemeath_api.py
```

服务默认运行在 `http://localhost:9880`。

## API 端点

### `POST /tts`

文本转语音。

**请求体**（JSON）：
```json
{
  "text": "你好，我是一行日辉的爱弥斯",
  "text_language": "zh",
  "ref_audio_path": "models/reference/basic_121068.wav",
  "prompt_text": "世界由我守护。目标揭露",
  "prompt_language": "zh",
  "top_p": 1,
  "temperature": 1
}
```

**响应**：WAV 音频二进制流

**示例**（curl）：
```bash
curl -X POST http://localhost:9880/tts \
    -H "Content-Type: application/json" \
    -d '{
        "text": "你好世界",
        "text_language": "zh"
    }' \
    --output hello.wav
```

**示例**（Python requests）：
```python
import requests

response = requests.post(
    "http://localhost:9880/tts",
    json={
        "text": "你好，我是一行日辉的爱弥斯",
        "text_language": "zh",
        "ref_audio_path": "models/reference/basic_121068.wav",
        "prompt_text": "世界由我守护。目标揭露",
        "prompt_language": "zh"
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

**示例**（JavaScript fetch）：
```javascript
const response = await fetch('http://localhost:9880/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        text: '你好世界',
        text_language: 'zh'
    })
});

const blob = await response.blob();
const url = URL.createObjectURL(blob);
const audio = new Audio(url);
audio.play();
```

### `GET /health`

健康检查端点。

**响应**：
```json
{
  "status": "ok",
  "model": "aemeath-e20",
  "version": "v2"
}
```

### `GET /voices`

列出所有可用的参考音频。

**响应**：
```json
{
  "voices": [
    {
      "name": "basic_121068.wav",
      "duration": 3.38,
      "text": "世界由我守护。目标揭露"
    },
    ...
  ]
}
```

---

## 部署到生产环境

### 方案一：systemd（Linux）

创建 `/etc/systemd/system/aemeath-api.service`：

```ini
[Unit]
Description=Aemeath Voice API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/GPT-SoVITS
ExecStart=/opt/GPT-SoVITS/venv/bin/python scripts/launch_aemeath_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用：
```bash
sudo systemctl enable aemeath-api
sudo systemctl start aemeath-api
```

### 方案二：Docker

```dockerfile
FROM nvidia/cuda:12.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3.11 python3-pip git

WORKDIR /app
RUN git clone https://github.com/RVC-Boss/GPT-SoVITS.git

COPY models/ /app/GPT-SoVITS/models/
COPY scripts/ /app/GPT-SoVITS/scripts/

WORKDIR /app/GPT-SoVITS
RUN pip install -r requirements.txt

CMD ["python", "scripts/launch_aemeath_api.py"]
```

构建并运行：
```bash
docker build -t aemeath-voice .
docker run -p 9880:9880 --gpus all aemeath-voice
```

### 方案三：Nginx 反向代理 + 守护进程

```nginx
# /etc/nginx/sites-available/aemeath
server {
    listen 80;
    server_name aemeath.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:9880;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;  # 长文本合成可能耗时较久
    }
}
```

---

## 性能优化

### 多 worker 并发

默认单 worker。可以通过 gunicorn 启动多 worker（注意：模型加载会消耗较多显存）：

```bash
pip install gunicorn
gunicorn -w 2 -k uvicorn.workers.UvicornWorker scripts.inference_api:app
```

### 异步任务队列

长文本建议异步处理：

```python
import uuid
from celery import Celery

app = Celery('aemeath', broker='redis://localhost:6379/0')

@app.task
def synthesize_task(text, output_id):
    audio_path = synthesize(text, f"outputs/{output_id}.wav")
    return audio_path
```

### 流式响应（开发中）

未来会支持 WebSocket 流式输出，可用于实时对话场景。

---

## 安全建议

部署到公网时务必注意：

1. **限流**：防止恶意调用拖垮服务
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=lambda: "global")
   @limiter.limit("10/minute")
   async def tts(...): ...
   ```

2. **认证**：避免滥用
   ```python
   @app.post("/tts")
   async def tts(req: TTSRequest, api_key: str = Header(...)):
       if api_key != "your-secret-key":
           raise HTTPException(403)
       ...
   ```

3. **输入校验**：限制单次文本长度
   ```python
   MAX_TEXT_LENGTH = 1000
   if len(req.text) > MAX_TEXT_LENGTH:
       raise HTTPException(400, "文本过长")
   ```

---

## 监控

### 简单监控脚本

```bash
#!/bin/bash
# monitor.sh
while true; do
    if ! curl -s http://localhost:9880/health > /dev/null; then
        echo "[$(date)] API 异常，尝试重启..."
        systemctl restart aemeath-api
    fi
    sleep 30
done
```

### Prometheus + Grafana

API 可以暴露 `/metrics` 端点供 Prometheus 抓取（需要扩展 `inference_api.py`）。
