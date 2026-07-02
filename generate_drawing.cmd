@echo off
rem Generate an ASME-compliant drawing (.prt + .pdf + report) from an NX part.
rem Usage: generate_drawing.cmd path\to\model.prt
setlocal

if "%~1"=="" (
    echo Usage: generate_drawing.cmd path\to\model.prt
    echo Outputs ^<model^>_dwg.prt, ^<model^>_dwg.pdf, ^<model^>_dwg_report.txt next to the model.
    exit /b 1
)
set "NXDRAW_MODEL=%~f1"

call :find_nx || exit /b 1
echo Generating drawing for %NXDRAW_MODEL% ...
"%NX_DIR%\NXBIN\run_journal.exe" "%~dp0nx_drawing_generator.py"
exit /b

:find_nx
if defined NX_DIR if exist "%NX_DIR%\NXBIN\run_journal.exe" exit /b 0
for /d %%D in ("C:\Program Files\Siemens\*") do (
    if exist "%%D\NXBIN\run_journal.exe" (
        set "NX_DIR=%%D"
        exit /b 0
    )
)
if defined UGII_BASE_DIR if exist "%UGII_BASE_DIR%\NXBIN\run_journal.exe" (
    set "NX_DIR=%UGII_BASE_DIR%"
    exit /b 0
)
echo Could not find NX. Set NX_DIR to your NX install folder (the one containing NXBIN).
exit /b 1
