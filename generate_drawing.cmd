@echo off
rem Usage: generate_drawing.cmd [path\to\model.prt]
rem Produces <model>_dwg.prt and <model>_dwg.pdf next to the model.

set NX_DIR=C:\Program Files\Siemens\DesigncenterX2606
if "%~1"=="" (
    set NXDRAW_MODEL=%~dp0examples\model3.prt
) else (
    set NXDRAW_MODEL=%~f1
)

echo Generating drawing for %NXDRAW_MODEL% ...
"%NX_DIR%\NXBIN\run_journal.exe" "%~dp0nx_drawing_generator.py"
