@echo off
chcp 65001 >nul
echo ========================================
echo Сборка VoiceInput.exe
echo ========================================
echo.

REM Проверка PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Установка PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить PyInstaller
        pause
        exit /b 1
    )
)

REM Проверка наличия модели
if not exist "models\vosk-model-small-ru-0.22" (
    echo.
    echo ВНИМАНИЕ: Модель Vosk не найдена!
    echo Убедитесь, что модель находится в models\vosk-model-small-ru-0.22
    echo.
    pause
)

REM Проверка config.json
if not exist "config.json" (
    echo.
    echo ВНИМАНИЕ: config.json не найден!
    echo Будет использован config.json по умолчанию.
    echo.
)

echo.
echo Начинаю сборку...
echo.

REM Очистка предыдущей сборки
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Сборка
pyinstaller build_exe.spec

if errorlevel 1 (
    echo.
    echo ОШИБКА при сборке!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Сборка завершена!
echo ========================================
echo.
echo Исполняемый файл: dist\VoiceInput.exe
echo.
echo Размер файла:
dir dist\VoiceInput.exe | find "VoiceInput.exe"
echo.
pause

