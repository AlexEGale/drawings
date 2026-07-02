@echo off
rem See and change NX model parameters (expressions) from outside NX.
rem Usage:
rem   params.cmd model.prt                       list parameters -> <model>_params.json
rem   params.cmd model.prt "p5=180" "p8=p5/2"    change values/formulas, rebuild, save
rem   params.cmd model.prt "p0->side_length"     rename a parameter (quotes required)
rem   params.cmd model.prt changes.json          bulk-apply formulas from a JSON
rem                                              file (same format as the dump)
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: params.cmd model.prt ["name=value" ^| "name=formula" ^| "old->new" ^| changes.json] ...
    exit /b 1
)
set "NXPARAM_MODEL=%~f1"
set NXPARAM_ACTION=list
set NXPARAM_SET=
set NXPARAM_JSON=

:parse
if "%~2"=="" goto run
set "ARG=%~2"
if /i "!ARG:~-5!"==".json" (
    set "NXPARAM_JSON=%~f2"
    set NXPARAM_ACTION=set
    shift
    goto parse
)
echo "!ARG!" | findstr /c:"=" /c:"->" >nul
if errorlevel 1 (
    rem no '=' in token: cmd split NAME=VALUE into two args - re-join
    set "NXPARAM_SET=!NXPARAM_SET!%~2=%~3;"
    shift
) else (
    set "NXPARAM_SET=!NXPARAM_SET!%~2;"
)
set NXPARAM_ACTION=set
shift
goto parse

:run
call :find_nx || exit /b 1
"%NX_DIR%\NXBIN\run_journal.exe" "%~dp0nx_params.py"
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
