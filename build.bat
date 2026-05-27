@echo off
echo ==========================================
echo Network Booster - Build Script
echo ==========================================
echo.

:: 1. Check for the icon file
if not exist "app_icon.ico" (
    echo ERROR: "app_icon.ico" was not found in the current directory!
    echo Please place your custom icon file in this folder and name it "app_icon.ico".
    echo Build aborted.
    pause
    exit /b 1
)

:: 2. Install dependencies
echo Installing required Python dependencies...
pip install requests customtkinter pyinstaller certifi
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies. Check your Python/PIP installation.
    pause
    exit /b 1
)

:: 3. Run PyInstaller
echo.
echo Compiling main.py into a standalone Executable...
:: --noconsole hides the background terminal
:: --uac-admin triggers the Windows UAC prompt automatically for the Deep Optimize feature
:: --icon attaches your custom icon
:: --collect-all customtkinter ensures all UI theme assets are packaged into the onefile
pyinstaller --noconfirm --onefile --noconsole --uac-admin --icon="app_icon.ico" --hidden-import="certifi" --hidden-import="requests" --collect-all="customtkinter" main.py

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo BUILD SUCCESSFUL!
echo Your compiled executable is located inside the "dist" folder.
echo ==========================================
pause
