#!/usr/bin/env python3
"""从 Hugging Face Hub 下载爱弥斯语音模型

用法：
    python download_models.py                  # 下载到默认目录（./models）
    python download_models.py --output /path/to/models  # 自定义目录
    python download_models.py --repo user/custom-repo  # 自定义仓库

环境变量：
    HF_TOKEN: Hugging Face token（私有仓库需要）

依赖：
    pip install huggingface_hub
"""
import os
import sys
import argparse
from pathlib import Path

# 默认仓库（用户应改为自己的）
DEFAULT_REPO = os.environ.get('AEMEATH_REPO', 'your-username/aemeath-voice')


def main():
    parser = argparse.ArgumentParser(
        description='从 Hugging Face 下载爱弥斯语音模型',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s                                          # 使用默认仓库
  %(prog)s --repo yourname/aemeath-voice          # 指定仓库
  %(prog)s --output D:/models/aemeath              # 自定义目录

如果还没有上传模型到 Hugging Face，请参考 docs/GITHUB_UPLOAD.md
        """
    )
    parser.add_argument(
        '--repo',
        default=DEFAULT_REPO,
        help=f'Hugging Face 仓库 ID（默认: {DEFAULT_REPO}）'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='下载到的本地目录（默认: ./models）'
    )
    parser.add_argument(
        '--files',
        nargs='+',
        default=None,
        help='只下载指定文件（默认: 全部 *.ckpt/*.pth/*.wav）'
    )
    parser.add_argument(
        '--token',
        default=None,
        help='Hugging Face token（也可通过 HF_TOKEN 环境变量）'
    )
    args = parser.parse_args()

    # 检查 huggingface_hub
    try:
        from huggingface_hub import snapshot_download, login
    except ImportError:
        print('❌ 缺少依赖 huggingface_hub')
        print('请运行: pip install huggingface_hub')
        sys.exit(1)

    # 登录（如果提供了 token）
    token = args.token or os.environ.get('HF_TOKEN')
    if token:
        print('🔑 登录 Hugging Face...')
        login(token=token)

    # 输出目录
    output_dir = Path(args.output) if args.output else Path(__file__).parent.parent / 'models'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 文件过滤
    if args.files:
        allow_patterns = args.files
    else:
        allow_patterns = ['*.ckpt', '*.pth', '*.wav']

    print(f'📥 下载模型')
    print(f'   仓库: {args.repo}')
    print(f'   目录: {output_dir}')
    print(f'   文件: {allow_patterns}')
    print()

    try:
        snapshot_download(
            repo_id=args.repo,
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,
            allow_patterns=allow_patterns,
            token=token,
        )
        print()
        print(f'✅ 下载完成！')
        print(f'   模型位置: {output_dir}')
        print()
        print('下一步：')
        print(f'   python scripts/aemeath_say.py --text "测试一下"')
    except Exception as e:
        print(f'❌ 下载失败: {e}')
        print()
        print('可能的原因：')
        print(f'  1. 仓库 {args.repo} 不存在或为私有（需要 --token）')
        print('  2. 网络问题（可设置 HF_ENDPOINT 镜像）')
        print('  3. huggingface_hub 版本过旧（pip install -U huggingface_hub）')
        sys.exit(1)


if __name__ == '__main__':
    main()
