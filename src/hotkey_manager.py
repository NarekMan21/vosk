"""
Модуль управления глобальными горячими клавишами.
"""
import logging
import threading
import keyboard

logger = logging.getLogger(__name__)

class HotkeyManager:
    """Класс для управления глобальными горячими клавишами."""
    
    def __init__(self):
        """Инициализация менеджера горячих клавиш."""
        self.hotkeys = {}
        self.callbacks = {}
        self.is_running = False
        self.thread = None
    
    def register_hotkey(self, hotkey, callback, description=""):
        """
        Регистрация горячей клавиши.
        
        Args:
            hotkey: Комбинация клавиш (например, "ctrl+shift+v")
            callback: Функция-обработчик
            description: Описание горячей клавиши
        """
        try:
            # Нормализация комбинации клавиш
            normalized = self._normalize_hotkey(hotkey)
            
            # Регистрация через библиотеку keyboard
            keyboard.add_hotkey(normalized, callback)
            
            self.hotkeys[normalized] = hotkey
            self.callbacks[normalized] = callback
            
            logger.info(f"Зарегистрирована горячая клавиша: {normalized} ({description})")
            return True
        except Exception as e:
            logger.error(f"Ошибка при регистрации горячей клавиши {hotkey}: {e}")
            return False
    
    def unregister_hotkey(self, hotkey):
        """
        Отмена регистрации горячей клавиши.
        
        Args:
            hotkey: Комбинация клавиш
        """
        try:
            normalized = self._normalize_hotkey(hotkey)
            if normalized in self.hotkeys:
                keyboard.remove_hotkey(normalized)
                del self.hotkeys[normalized]
                del self.callbacks[normalized]
                logger.info(f"Горячая клавиша отменена: {normalized}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при отмене регистрации горячей клавиши {hotkey}: {e}")
        return False
    
    def unregister_all(self):
        """Отмена регистрации всех горячих клавиш."""
        for hotkey in list(self.hotkeys.keys()):
            self.unregister_hotkey(hotkey)
        logger.info("Все горячие клавиши отменены")
    
    def _normalize_hotkey(self, hotkey):
        """
        Нормализация комбинации клавиш.
        
        Args:
            hotkey: Комбинация клавиш
        
        Returns:
            Нормализованная комбинация
        """
        # Приводим к нижнему регистру и убираем пробелы
        normalized = hotkey.lower().replace(" ", "")
        return normalized
    
    def start(self):
        """Запуск менеджера горячих клавиш."""
        if self.is_running:
            logger.warning("Менеджер горячих клавиш уже запущен")
            return
        
        self.is_running = True
        logger.info("Менеджер горячих клавиш запущен")
    
    def stop(self):
        """Остановка менеджера горячих клавиш."""
        if not self.is_running:
            return
        
        self.unregister_all()
        self.is_running = False
        logger.info("Менеджер горячих клавиш остановлен")
    
    def __enter__(self):
        """Контекстный менеджер: вход."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер: выход."""
        self.stop()

