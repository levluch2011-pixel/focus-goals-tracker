@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Напоминатель Целей

:: Проверяем наличие python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Python не найден в системе. Установите Python с python.org
        pause
        exit /b 1
    )
    set PY_CMD=py
) else (
    set PY_CMD=python
)

:: Запуск приложения
echo Запуск «Напоминатель Целей»...
%PY_CMD% main.py

if errorlevel 1 (
    echo.
    echo ------------------------------------------------------------
    echo Произошла ошибка при запуске!
    echo Пробуем доустановить нужные модули...
    echo ------------------------------------------------------------
    %PY_CMD% -m pip install -r requirements.txt
    echo.
    echo Повторный запуск:
    %PY_CMD% main.py
    pause
)
