@echo off
REM ======================================================================
REM  爱弥斯语音 - 一键停止脚本
REM  关闭所有 Aemeath Voice 相关进程
REM ======================================================================

echo.
echo 正在停止爱弥斯语音 API ...
echo.

REM 关掉通过 start.bat 启动的后台进程（窗口标题 = "Aemeath Voice API"）
taskkill /FI "WINDOWTITLE eq Aemeath Voice API*" /F >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 没找到 API 进程窗口（可能已经退出）
)

REM 也兜底处理 EXE 进程名（未来 PyInstaller 打包后用）
taskkill /IM "AemeathVoice-API.exe" /F >nul 2>&1

REM 关掉任何占用 9880 端口的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9880" ^| findstr "LISTENING"') do (
    echo [清理] 关闭端口 9880 上的进程 PID=%%a
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo [完成] 所有爱弥斯语音进程已停止
echo.
timeout /t 3 /nobreak >nul