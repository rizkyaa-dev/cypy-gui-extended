@echo off
setlocal

if exist "%~dp0cypy.exe" if not exist "%~dp0run.bat" (
    "%~dp0cypy.exe" --gui %*
    exit /b %ERRORLEVEL%
)

call "%~dp0run.bat" --gui %*
exit /b %ERRORLEVEL%
