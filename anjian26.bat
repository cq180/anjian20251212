@echo off
if "%~1"=="run_hidden" goto :run_application

:: 生成临时的 vbs 脚本来隐蔽调用当前 bat
echo CreateObject("WScript.Shell").Run """%~f0"" run_hidden", 0, False > "%temp%\run_hidden.vbs"
cscript //nologo "%temp%\run_hidden.vbs"
del "%temp%\run_hidden.vbs"
exit /b

:run_application
:: 切换到当前 bat 所在的目录
cd /d "%~dp0"
:: 执行主程序，并将输出重定向至 error.log 以便排查错误
python "%~dp0anjian20251212.py" > error.log 2>&1
