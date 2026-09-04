@echo off
REM ======================================================================
REM  爱弥斯语音 - 一键启动脚本（双击运行）
REM  启动 API server + 自动打开浏览器到 Web 控制台
REM ======================================================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ========== 选择 Python 解释器 ==========
set "PYTHON_EXE="

REM 1. 精简版内嵌的 Python311（最稳）
if exist "AemeathVoice_Portable\python\python.exe" (
    set "PYTHON_EXE=%~dp0AemeathVoice_Portable\python\python.exe"
    goto :have_python
)

REM 2. 系统 Python
for /f "delims=" %%i in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%i"
    goto :have_python
)

echo [错误] 找不到 Python，请先安装 Python 3.10+ 并加入 PATH
pause
exit /b 1

:have_python
echo.
echo ============================================================
echo   爱弥斯语音 API 启动器
echo   Python: !PYTHON_EXE!
echo ============================================================
echo.

REM ========== 关闭残留进程 ==========
call "%~dp0stop.bat" >nul 2>&1

REM ========== 启动 API server（后台新窗口） ==========
echo [1/2] 启动 API server ...
start "Aemeath Voice API" "!PYTHON_EXE!" "%~dp0scripts\launch_aemeath_api.py" --port 9880

REM ========== 等待 API 就绪 ==========
echo [2/2] 等待 API 就绪 ...
set /a retry=0
:wait_loop
set /a retry+=1
powershell -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:9880/health' -TimeoutSec 2 -UseBasicParsing).StatusCode | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 goto :api_ready
if !retry! geq 90 (
    echo.
    echo [警告] API 90 秒内未就绪，可能首次加载较慢
    echo        请查看 "Aemeath Voice API" 窗口的错误信息
    goto :open_browser
)
timeout /t 1 /nobreak >nul
goto :wait_loop

:api_ready
echo       API 已就绪！

:open_browser
echo.
echo ============================================================
echo   Web 控制台：http://127.0.0.1:9880/
echo   Swagger:    http://127.0.0.1:9880/docs
echo.
echo   关闭 API：双击 stop.bat
echo   或关闭 "Aemeath Voice API" 命令行窗口
echo ============================================================
echo.
start "" "http://127.0.0.1:9880/"

endlocal