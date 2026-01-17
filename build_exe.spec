# -*- mode: python ; coding: utf-8 -*-
"""
Спецификация PyInstaller для сборки исполняемого файла.
"""
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Собираем все зависимости Vosk (включая DLL)
vosk_datas, vosk_binaries, vosk_hiddenimports = collect_all('vosk')
print(f"Найдено DLL Vosk: {len(vosk_binaries)} файлов")

# Собираем все зависимости Pillow (PIL)
pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')
print(f"Найдено скрытых импортов PIL: {len(pil_hiddenimports)}")

# Собираем все зависимости pystray
pystray_datas, pystray_binaries, pystray_hiddenimports = collect_all('pystray')
print(f"Найдено скрытых импортов pystray: {len(pystray_hiddenimports)}")

# Собираем зависимости win11toast
try:
    win11toast_datas, win11toast_binaries, win11toast_hiddenimports = collect_all('win11toast')
    print(f"Найдено скрытых импортов win11toast: {len(win11toast_hiddenimports)}")
except Exception:
    win11toast_datas, win11toast_binaries, win11toast_hiddenimports = [], [], []
    print("win11toast: зависимости не найдены (это нормально)")

# Определяем пути к файлам
base_path = Path('.').resolve()  # Абсолютный путь
config_file = base_path / 'config.json'
models_dir = base_path / 'models'
src_dir = base_path / 'src'

# Собираем список данных для включения
datas = []

# Добавляем config.json если существует
if config_file.exists():
    datas.append((str(config_file), '.'))

# НЕ включаем модель в exe - она должна быть рядом с exe в папке models/
# Это ускоряет сборку и запуск, так как модель не нужно распаковывать
# Модель будет загружаться из папки models/ рядом с exe файлом
print("Модель не включается в exe - она должна быть в папке models/ рядом с exe файлом")

# Если файлов нет, выводим предупреждение
if not datas:
    print("ВНИМАНИЕ: config.json или models/ не найдены!")
    print("Убедитесь, что они существуют перед сборкой.")

print(f"Базовый путь: {base_path}")
print(f"Директория src: {src_dir}")
print(f"Существует src: {src_dir.exists()}")

a = Analysis(
    [str(base_path / 'src' / 'main.py')],  # Абсолютный путь к main.py
    pathex=[str(src_dir)],  # Добавляем src в путь поиска модулей
    binaries=vosk_binaries + pil_binaries + pystray_binaries + win11toast_binaries,  # Включаем DLL файлы
    datas=datas + vosk_datas + pil_datas + pystray_datas + win11toast_datas,  # Включаем данные
    hiddenimports=[
        'pystray._win32',
        'keyboard',
        'vosk',
        'pyaudio',
        'vosk._vosk',
        'vosk.vosk_cffi',
        'vosk.transcriber',
        'webrtcvad',
        'win11toast',
        'winsound',
        'winreg',
        # Pillow (PIL) для работы с иконками - все зависимости собираются через collect_all
        # Явно указываем все модули из src
        'config',
        'audio_capture',
        'speech_recognition',
        'text_input',
        'voice_commands',
        'system_tray',
        'hotkey_manager',
        'notifications',
        'audio_feedback',
        'vad',
        'app_statistics',
        'autostart',
        'model_manager',
        'first_run',
        'updater',
    ] + vosk_hiddenimports + pil_hiddenimports + pystray_hiddenimports + win11toast_hiddenimports,  # Добавляем все скрытые импорты
    hookspath=['.'],  # Ищем hooks в текущей директории
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy.distutils',
        'pandas',
        'scipy',
        'tkinter.test',
        # НЕ исключаем PIL - он нужен для system_tray
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VoiceInput',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
        'libvosk.dll',
        'libgcc_s_seh-1.dll',
        'libstdc++-6.dll',
        'libwinpthread-1.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # Без консоли для продакшена
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Можно добавить иконку .ico файл
    version=None,  # Можно добавить version.txt для версии
)

