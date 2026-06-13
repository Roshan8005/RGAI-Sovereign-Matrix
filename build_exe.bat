@echo off
title RGAI Universe Standalone Builder
echo ===================================================
echo 📦 RGAI UNIVERSE STANDALONE PORTABLE BUILDER 📦
echo ===================================================
echo.
echo Step 1: Navigating to E:\VirtualUniverse...
E:
cd E:\VirtualUniverse
echo.
echo Step 2: Checking and Installing PyInstaller...
python -m pip install pyinstaller
echo.
echo Step 3: Compiling RGAI_Universe Standalone Folder...
echo [This might take a minute, please wait...]
echo.
python -m PyInstaller --onedir --name="RGAI_Universe" --add-data "templates;templates" launcher.py
echo.
echo ===================================================
echo 🎉 COMPILATION PROCESS FINISHED!
echo ===================================================
echo.
echo What's Next?
echo 1. Go to "E:\VirtualUniverse\dist\RGAI_Universe".
echo 2. Copy the "RGAI_Universe" folder to your Pendrive.
echo 3. Manually COPY these folders from "E:\VirtualUniverse" inside your pendrive's "RGAI_Universe" folder:
echo    - "core_32_architects"
echo    - "native_infrastructure"
echo    - "network_users"
echo 4. Double click "RGAI_Universe.exe" on any Windows PC to run!
echo.
pause
