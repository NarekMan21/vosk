"""
Модуль управления автозапуском приложения при старте Windows.

Использует реестр Windows (HKEY_CURRENT_USER) — не требует прав администратора.
"""
import logging
import sys
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь в реестре для автозапуска текущего пользователя
REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "VoiceInput"


def _get_app_path() -> str:
    """Получить путь к исполняемому файлу приложения."""
    if getattr(sys, 'frozen', False):
        # Запущено как .exe
        return sys.executable
    else:
        # Запущено как скрипт — создаём команду запуска
        python_exe = sys.executable
        script_path = Path(__file__).parent / "main.py"
        return f'"{python_exe}" "{script_path}"'


def is_autostart_enabled() -> bool:
    """
    Проверяет, включён ли автозапуск.
    
    Returns:
        True если автозапуск включён, False иначе
    """
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
            
    except Exception as e:
        logger.error(f"Ошибка проверки автозапуска: {e}")
        return False


def enable_autostart() -> bool:
    """
    Включает автозапуск приложения при старте Windows.
    
    Returns:
        True если успешно, False при ошибке
    """
    try:
        import winreg
        
        app_path = _get_app_path()
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_WRITE
        )
        try:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)
            logger.info(f"Автозапуск включён: {app_path}")
            return True
        finally:
            winreg.CloseKey(key)
            
    except Exception as e:
        logger.error(f"Ошибка включения автозапуска: {e}")
        return False


def disable_autostart() -> bool:
    """
    Отключает автозапуск приложения.
    
    Returns:
        True если успешно, False при ошибке
    """
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_WRITE
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
            logger.info("Автозапуск отключён")
            return True
        except FileNotFoundError:
            # Значение уже отсутствует
            logger.info("Автозапуск уже был отключён")
            return True
        finally:
            winreg.CloseKey(key)
            
    except Exception as e:
        logger.error(f"Ошибка отключения автозапуска: {e}")
        return False


def set_autostart(enabled: bool) -> bool:
    """
    Устанавливает состояние автозапуска.
    
    Args:
        enabled: True для включения, False для отключения
        
    Returns:
        True если успешно, False при ошибке
    """
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()
