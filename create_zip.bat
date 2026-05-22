@echo off
setlocal EnableExtensions

if /i not "%~1"=="__RUN__" (
    cmd /k ""%~f0" __RUN__"
    exit /b
)

for %%I in ("%~dp0.") do set "ROOT_DIR=%%~fI"
set "OUTPUT_ZIP=%ROOT_DIR%\code-verification-guard.zip"
set "EXIT_CODE=0"

echo ==========================================
echo Code Verification Guard zip script started
echo ==========================================
echo Root directory: %ROOT_DIR%
echo Output archive: %OUTPUT_ZIP%
echo.

if not exist "%ROOT_DIR%" (
    echo ERROR: Root directory does not exist.
    set "EXIT_CODE=1"
    goto :END
)

echo Creating archive...
python "%ROOT_DIR%\scripts\create_zip.py" "%ROOT_DIR%" "%OUTPUT_ZIP%"
if errorlevel 1 (
    echo ERROR: Compression failed.
    set "EXIT_CODE=1"
    goto :END
)

echo.
echo SUCCESS: Archive created successfully.

:END
echo.
if /i "%~2"=="--no-pause" exit /b %EXIT_CODE%

echo Press any key to close this window...
pause >nul
exit /b %EXIT_CODE%
