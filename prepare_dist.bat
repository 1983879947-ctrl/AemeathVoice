@echo off
REM ======================================================================
REM  爱弥斯语音 - EXE 部署辅助
REM  把 models/、text/、pretrained/ 软链到 EXE 同目录
REM  避免重复拷贝 2.4GB+ 模型数据
REM
REM  使用方法：
REM    在有 AemeathVoice_Portable 模型的机器上运行一次即可
REM ======================================================================

setlocal

cd /d "%~dp0"

set "DIST_DIR=dist\AemeathVoice"
set "PORTABLE_DIR=AemeathVoice_Portable"

if not exist "%DIST_DIR%\" (
    echo [错误] 没找到 %DIST_DIR% — 请先运行 pyinstaller build.spec
    pause
    exit /b 1
)

if not exist "%PORTABLE_DIR%\" (
    echo [错误] 没找到 %PORTABLE_DIR% — 请确认模型在 AemeathVoice_Portable\models\
    pause
    exit /b 1
)

echo.
echo [1/2] 创建软链 ...
echo.

REM 删除旧链接（如果存在）
if exist "%DIST_DIR%\models" rmdir "%DIST_DIR%\models" 2>nul
if exist "%DIST_DIR%\text" rmdir "%DIST_DIR%\text" 2>nul

REM 创建符号链接（EXE 启动时会找 EXE 同目录的 models）
mklink /D "%DIST_DIR%\models" "..\%PORTABLE_DIR%\models" >nul
if %errorlevel% neq 0 (
    echo [警告] 软链 models 失败 — 尝试复制 ...
    xcopy /E /I /Y "%PORTABLE_DIR%\models" "%DIST_DIR%\models" >nul
)
mklink /D "%DIST_DIR%\text" "..\%PORTABLE_DIR%\text" >nul
if %errorlevel% neq 0 (
    echo [警告] 软链 text 失败 — 尝试复制 ...
    xcopy /E /I /Y /Q "%PORTABLE_DIR%\text" "%DIST_DIR%\text" >nul
)

echo.
echo [2/2] 验证 ...
if exist "%DIST_DIR%\models\s1\aemeath-e20.ckpt" (
    echo       ✓ models 链接 OK
) else (
    echo       ✗ models 链接失败
)
if exist "%DIST_DIR%\text\G2PWModel" (
    echo       ✓ text 链接 OK
) else (
    echo       ✗ text 链接失败
)

echo.
echo ============================================================
echo   准备完成！
echo   启动：双击 %DIST_DIR%\AemeathVoice.exe
echo   或命令行：%DIST_DIR%\AemeathVoice.exe
echo ============================================================
echo.

endlocal