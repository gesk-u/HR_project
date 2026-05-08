@echo off
:: ============================================================
::  Raspberry Pi Pico – Health Monitor Installer
::  Copies all project files to the Pico via mpremote
:: ============================================================

title Pico Health Monitor – Installer
color 0A

echo.
echo  =========================================
echo   Pico Health Monitor -- File Installer
echo  =========================================
echo.

:: ── 1. Check that mpremote is available ─────────────────────
where mpremote >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] mpremote not found.
    echo  Install it with:  pip install mpremote
    echo.
    pause
    exit /b 1
)

:: ── 2. Wait for the Pico to be connected ────────────────────
echo  Connect your Pico W via USB, then press any key...
pause >nul
echo.

:: ── 3. Copy every project file to the Pico root ─────────────
echo  Uploading project files...
echo.

set FILES=main.py Con.py cross.py Input.py intro.py media.py OOPs.py client_ids.json localhistory.json

set ERRORS=0
for %%F in (%FILES%) do (
    if exist "%%F" (
        echo   ^> Uploading %%F ...
        mpremote cp "%%F" ":%%F"
        if errorlevel 1 (
            echo   [WARN] Failed to upload %%F
            set /a ERRORS+=1
        )
    ) else (
        echo   [SKIP] %%F not found in current folder
    )
)

:: ── 4. Install MicroPython libraries from PyPI ───────────────
echo.
echo  Installing MicroPython libraries...
echo.

echo   ^> Installing ssd1306 ...
mpremote mip install ssd1306
if errorlevel 1 echo   [WARN] ssd1306 install failed -- may already be present

echo   ^> Installing umqtt.simple ...
mpremote mip install umqtt.simple
if errorlevel 1 echo   [WARN] umqtt.simple install failed -- may already be present

:: ── 5. Summary ───────────────────────────────────────────────
echo.
echo  =========================================
if %ERRORS%==0 (
    echo   Done! All files uploaded successfully.
) else (
    echo   Done with %ERRORS% warning(s). Check output above.
)
echo  =========================================
echo.
echo  You can now reset your Pico or press Ctrl+D
echo  in a serial terminal to run main.py.
echo.
pause
