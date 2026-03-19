@echo off
rem call_andrep.bat — invoke the AndRep renderer from any directory.
rem
rem Usage:
rem   call_andrep.bat render --template tmpl.json --records records.json ^
rem                          --format pdf --output report.pdf
rem
rem The script adds the renderer\ directory to PYTHONPATH so that
rem "python -m andrep" works without installing the package.

set "SCRIPT_DIR=%~dp0"
set "RENDERER_DIR=%SCRIPT_DIR%..\renderer"

if defined PYTHONPATH (
    set "PYTHONPATH=%RENDERER_DIR%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%RENDERER_DIR%"
)

python -m andrep %*
