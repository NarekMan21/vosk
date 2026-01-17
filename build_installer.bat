@echo off
chcp 65001 >nul
echo ========================================
echo Сборка установщика VoiceInput
echo ========================================
echo.

REM Проверяем наличие Inno Setup
set "ISCC=D:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC%" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC%" (
    echo.
    echo ОШИБКА: Inno Setup 6 не найден!
    echo.
    echo Скачайте и установите Inno Setup 6:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

REM Проверяем наличие dist
if not exist "dist\VoiceInput.exe" (
    echo.
    echo ОШИБКА: dist\VoiceInput.exe не найден!
    echo Сначала выполните сборку: build.bat
    echo.
    pause
    exit /b 1
)

REM Создаём папку для выходного файла
if not exist "installer_output" mkdir installer_output

echo.
echo Компиляция установщика...
echo.

"%ISCC%" installer.iss

if errorlevel 1 (
    echo.
    echo ОШИБКА при создании установщика!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Установщик создан успешно!
echo ========================================
echo.
echo Файл: installer_output\VoiceInput-Setup-1.0.0.exe
echo.
dir installer_output\*.exe
echo.
pause
