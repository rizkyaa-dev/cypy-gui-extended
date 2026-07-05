@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "APP_NAME=cypy"
set "APP_LABEL=cypy CLI"
set "APP_MODULE=cypy"
set "DEFAULT_VENV=.venv"
set "VENV_DIR="
set "FORCE_INSTALL=0"
set "INSTALL_EXTRA="
set "CHECK_ONLY=0"

for %%A in (%*) do (
    if /I "%%~A"=="--gui" (
        set "APP_LABEL=cypy GUI"
        set "APP_MODULE=cypy.gui.app"
    )
    if /I "%%~A"=="--reinstall" set "FORCE_INSTALL=1"
    if /I "%%~A"=="--dev" set "INSTALL_EXTRA=[dev]"
    if /I "%%~A"=="--check" set "CHECK_ONLY=1"
)

title %APP_LABEL% launcher

echo.
echo ========================================
echo   %APP_LABEL% Windows launcher
echo ========================================
echo.

if exist "venv\Scripts\python.exe" (
    set "VENV_DIR=venv"
) else if exist ".venv\Scripts\python.exe" (
    set "VENV_DIR=.venv"
) else (
    set "VENV_DIR=%DEFAULT_VENV%"
)

set "BOOTSTRAP_PY="
where py >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PY=py -3"

if not defined BOOTSTRAP_PY (
    where python >nul 2>nul
    if not errorlevel 1 set "BOOTSTRAP_PY=python"
)

if not defined BOOTSTRAP_PY (
    echo [ERROR] Python was not found.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure "Add python.exe to PATH" is enabled during installation.
    echo.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment: %VENV_DIR%
    %BOOTSTRAP_PY% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set "PYTHON_EXE=%CD%\%VENV_DIR%\Scripts\python.exe"
set "DEPS_MARKER=%CD%\%VENV_DIR%\.cypy_deps_ok"

echo [INFO] Using virtual environment: %VENV_DIR%

"%PYTHON_EXE%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [SETUP] pip is missing. Running ensurepip...
    "%PYTHON_EXE%" -m ensurepip --upgrade
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install pip in the virtual environment.
        pause
        exit /b 1
    )
)

set "NEED_INSTALL=%FORCE_INSTALL%"

if "%FORCE_INSTALL%"=="0" (
    "%PYTHON_EXE%" -c "import cypy, cv2, fitz, numpy, PIL, onnxruntime, google.genai, dotenv, requests, rarfile" >nul 2>nul
    if errorlevel 1 (
        set "NEED_INSTALL=1"
    ) else (
        if not exist "%DEPS_MARKER%" > "%DEPS_MARKER%" echo Dependencies verified for %APP_NAME%.
    )
)

if "%NEED_INSTALL%"=="1" (
    echo [SETUP] Installing project dependencies...
    "%PYTHON_EXE%" -m pip install --upgrade pip
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to upgrade pip.
        pause
        exit /b 1
    )

    "%PYTHON_EXE%" -m pip install -e ".%INSTALL_EXTRA%"
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install project dependencies.
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )

    > "%DEPS_MARKER%" echo Dependencies verified for %APP_NAME%.
) else (
    echo [INFO] Dependencies already verified.
)

if "%CHECK_ONLY%"=="1" (
    echo.
    echo [OK] Environment check completed.
    pause
    exit /b 0
)

echo.
echo [RUN] Starting %APP_LABEL%...
echo.
"%PYTHON_EXE%" -m %APP_MODULE%

set "APP_EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%APP_EXIT_CODE%"=="0" (
    echo [ERROR] %APP_LABEL% exited with code %APP_EXIT_CODE%.
) else (
    echo [OK] %APP_LABEL% closed.
)
echo.
pause
exit /b %APP_EXIT_CODE%
