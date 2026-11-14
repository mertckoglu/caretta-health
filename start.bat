@echo off
echo Creating virtual environment...
python -m venv .venv > nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment! Please make sure Python is installed.
    pause
    exit /b 1
)

call .venv\Scripts\activate

echo Installing packages...
pip install -r requirements.txt > nul 2>&1
if errorlevel 1 (
    echo ERROR: An error occurred while installing packages.
    pause
    exit /b 1
)

echo Setup completed successfully!