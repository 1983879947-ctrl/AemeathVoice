#!/usr/bin/env python3
"""启动 Aemeath Voice HTTP API 服务

用法：
    python launch_aemeath_api.py
    python launch_aemeath_api.py --port 9880 --host 0.0.0.0

环境要求：
    pip install fastapi uvicorn[standard]
"""
import argparse
import sys
import os

# 确保能找到 inference_api
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

def main():
    parser = argparse.ArgumentParser(description='启动 Aemeath Voice HTTP API')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址（默认 127.0.0.1，公网请用 0.0.0.0）')
    parser.add_argument('--port', type=int, default=9880, help='监听端口（默认 9880）')
    parser.add_argument('--reload', action='store_true', help='开发模式：自动重载')
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print('❌ 缺少依赖: fastapi / uvicorn')
        print('请运行: pip install fastapi "uvicorn[standard]"')
        sys.exit(1)

    print(f'🚀 启动 Aemeath Voice API 服务...')
    print(f'📡 监听地址: http://{args.host}:{args.port}')
    print(f'📖 API 文档: http://{args.host}:{args.port}/docs')
    print()

    uvicorn.run(
        'inference_api:app',
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level='info'
    )

if __name__ == '__main__':
    main()
