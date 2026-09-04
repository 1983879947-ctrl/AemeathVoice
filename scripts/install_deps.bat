@echo off
chcp 65001 >nul
echo ============================================
echo   爱弥斯语音 - 依赖一键安装
echo   需要已安装 Python 3.10 / 3.11
echo ============================================
where py >nul 2>nul
if %errorlevel%==0 (
    py -3.11 -m pip install fastapi "uvicorn[standard]" soundfile librosa cn2an pypinyin opencc jieba transformers onnxruntime nltk 2>nul || python -m pip install fastapi "uvicorn[standard]" soundfile librosa cn2an pypinyin opencc jieba transformers onnxruntime nltk
    py -3.11 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128 2>nul || python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
) else (
    python -m pip install fastapi "uvicorn[standard]" soundfile librosa cn2an pypinyin opencc jieba transformers onnxruntime nltk
    python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
)
echo.
echo 安装完成！重新双击 AemeathVoice.exe 即可。
pause
