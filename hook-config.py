"""
PyInstaller hook для модуля config
"""
from PyInstaller.utils.hooks import collect_all

# Собираем все модули из src
datas, binaries, hiddenimports = collect_all('src')

