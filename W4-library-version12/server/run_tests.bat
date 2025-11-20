@echo off
REM Script để chạy tests trên Windows
REM Sử dụng: run_tests.bat [mode]
REM   mode: all, coverage, verbose, fast

setlocal

echo ========================================
echo   Library API Test Runner
echo ========================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo WARNING: Virtual environment not activated
    echo Consider running: .\venv\Scripts\activate
    echo.
)

REM Get mode from argument or default to 'all'
set MODE=%1
if "%MODE%"=="" set MODE=all

echo Mode: %MODE%
echo.

REM Run tests based on mode
if "%MODE%"=="all" (
    echo Running all tests with unittest...
    python -m unittest test_api.py
) else if "%MODE%"=="coverage" (
    echo Running tests with coverage report...
    pytest test_api.py --cov=. --cov-report=html --cov-report=term
    echo.
    echo Coverage report generated in htmlcov\index.html
) else if "%MODE%"=="verbose" (
    echo Running tests in verbose mode...
    python -m unittest test_api.py -v
) else if "%MODE%"=="fast" (
    echo Running tests with pytest...
    pytest test_api.py -v --tb=short
) else (
    echo Unknown mode: %MODE%
    echo Valid modes: all, coverage, verbose, fast
    exit /b 1
)

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo   Tests completed successfully!
    echo ========================================
) else (
    echo ========================================
    echo   Tests failed!
    echo ========================================
    exit /b 1
)

endlocal
