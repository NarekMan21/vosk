@echo off
chcp 65001 >nul
echo ========================================
echo Сборка VoiceInput.exe (РЕЖИМ ОТЛАДКИ)
echo ========================================
echo.

REM Временно включаем консоль в spec файле для отладки
echo Собираю с консолью для отладки ошибок...
echo.

pyinstaller build_exe.spec --clean

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
echo Запустите dist\VoiceInput.exe чтобы увидеть ошибку в консоли
echo.
pause

