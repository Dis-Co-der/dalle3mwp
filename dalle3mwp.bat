@echo off
setlocal

cls

set BASE_DIR=%~dp0

icacls "%BASE_DIR%main.py" /grant %username%:F > nul 2>&1
icacls "%BASE_DIR%application_config.txt" /grant %username%:F > nul 2>&1

echo Checking for requirements...
python -m pip install --upgrade --force-reinstall -r "%BASE_DIR%requirements.txt" --quiet > nul 2>&1

IF ERRORLEVEL 1 (
    echo Installing requirements...
    python -m pip cache purge > nul 2>&1
    python -m pip install --upgrade --force-reinstall -r "%BASE_DIR%requirements.txt" --quiet > nul 2>&1
    IF ERRORLEVEL 1 (
        echo ERROR: Dependency installation failed even after cache purge.
        goto :end
    ) ELSE (
        echo Requirements installed...launching app
    )
) ELSE (
    echo Requirements installed/upgraded successfully.
)

echo NOTE: If you get errors in the app, check if your OpenAI account has enough credits. Also close the app by closing this terminal and relaunch dalle3mwp.bat
python "%BASE_DIR%main.py" 2> error.log

IF ERRORLEVEL 1 (
    echo ERROR: An error occurred while running the app.
    for /f "tokens=*" %%A in ('findstr /r /c:"^[^ ]*Error:.*" error.log') do echo %%A
    del error.log
)

:end
endlocal
exit