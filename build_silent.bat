@echo off
chcp 65001 >nul
echo Сборка VoiceInput.exe...
echo.

REM Очистка предыдущей сборки
if exist "build" rmdir /s /q build 2>nul
if exist "dist" rmdir /s /q dist 2>nul

REM Сборка
pyinstaller build_exe.spec

if errorlevel 1 (
    echo ОШИБКА при сборке!
    exit /b 1
)

if exist "dist\VoiceInput.exe" (
    echo.
    echo ========================================
    echo Сборка завершена успешно!
    echo ========================================
    echo Исполняемый файл: dist\VoiceInput.exe
    echo.
    dir dist\VoiceInput.exe
) else (
    echo ОШИБКА: VoiceInput.exe не создан!
    exit /b 1
)
