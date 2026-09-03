"""特征提取预处理脚本（GPT-SoVITS Windows + Python 3.12 兼容版）

修复的关键 bug：
1. jieba_fast 不支持 Python 3.12
2. G2PW 路径是相对路径（双 module 对象都要 patch）
3. bert_path 默认相对路径被当 HF repo

用法：
    python run_preprocess_v5.py --step 1   # BERT 文本特征
    python run_preprocess_v5.py --step 2   # HuBERT + wav32k
    python run_preprocess_v5.py --step 3   # SoVITS 语义 token
"""
import os
import sys
import argparse
import shutil
from pathlib import Path

# 路径配置
ROOT = Path(__file__).parent.parent
GPT_SOVITS_REPO = Path(os.environ.get('GPT_SOVITS_PATH', './GPT-SoVITS')).resolve()
DATA_DIR = Path(os.environ.get('DATA_DIR', './filelists')).resolve()

sys.path.insert(0, str(GPT_SOVITS_REPO))
sys.path.insert(0, str(GPT_SOVITS_REPO / 'GPT_SoVITS'))

# === 补丁 1: jieba_fast 替代 ===
import jieba as _jieba
import jieba.posseg as _psg
_jieba.setLogLevel = lambda level: None
sys.modules['jieba_fast'] = _jieba
sys.modules['jieba_fast.posseg'] = _psg

# === 补丁 2: G2PW 路径 ===
def _patch_g2pw():
    import importlib
    try:
        mod_a = importlib.import_module('GPT_SoVITS.text.g2pw.onnx_api')
        mod_b = importlib.import_module('text.g2pw.onnx_api')
    except Exception as e:
        print(f'⚠️ G2PW 模块加载失败: {e}', file=sys.stderr)
        return

    target_dir = str(GPT_SOVITS_REPO / 'GPT_SoVITS' / 'text' / 'G2PWModel')

    def _patched(*args, **kwargs):
        return target_dir

    mod_a.download_and_decompress = _patched
    mod_b.download_and_decompress = _patched

_patch_g2pw()

# === 补丁 3: bert_path 环境变量 ===
os.environ['bert_path'] = str(GPT_SOVITS_REPO / 'GPT_SoVITS' / 'pretrained_models' / 'chinese-roberta-wwm-ext-large')

# === 参数解析 ===
parser = argparse.ArgumentParser()
parser.add_argument('--step', type=int, required=True, choices=[1, 2, 3])
parser.add_argument('--data-dir', default=str(DATA_DIR), help='数据目录（含 train.list/val.list）')
parser.add_argument('--exp-dir', default='logs_s2_v2', help='S2 实验子目录')
args = parser.parse_args()

os.chdir(args.data_dir)
print(f'📁 数据目录: {os.getcwd()}', file=sys.stderr)


def step1_bert():
    """Step 1: BERT 文本特征"""
    print('🚀 Step 1: BERT 文本特征提取...', file=sys.stderr)
    os.system(f'python "{GPT_SOVITS_REPO}/1-get-text.py"')


def step2_hubert():
    """Step 2: HuBERT 音频特征"""
    print('🚀 Step 2: HuBERT + wav32k 提取...', file=sys.stderr)
    os.system(f'python "{GPT_SOVITS_REPO}/2-get-hubert-wav32k.py"')


def step3_semantic():
    """Step 3: SoVITS 语义 token"""
    print('🚀 Step 3: SoVITS 语义 token...', file=sys.stderr)
    os.system(f'python "{GPT_SOVITS_REPO}/3-get-semantic.py"')


if __name__ == '__main__':
    if args.step == 1:
        step1_bert()
    elif args.step == 2:
        step2_hubert()
    elif args.step == 3:
        step3_semantic()
    print('✅ 完成！', file=sys.stderr)
