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
        self._hold_hotkeys = {}  # Для режима зажатия
        self._hold_active = {}   # Отслеживание активных hold
    
    def register_hotkey(self, hotkey, callback, description="", hold_mode=False, 
                        on_release=None):
        """
        Регистрация горячей клавиши.
        
        Args:
            hotkey: Комбинация клавиш (например, "ctrl+shift+v")
            callback: Функция-обработчик (при нажатии)
            description: Описание горячей клавиши
            hold_mode: Если True — режим зажатия (push-to-talk)
            on_release: Функция при отпускании (только для hold_mode)
        """
        try:
            normalized = self._normalize_hotkey(hotkey)
            
            if hold_mode and on_release:
                # Режим зажатия: регистрируем нажатие и отпускание
                self._hold_active[normalized] = False
                
                def on_press_handler():
                    if not self._hold_active.get(normalized, False):
                        self._hold_active[normalized] = True
                        callback()
                
                def on_release_handler():
                    if self._hold_active.get(normalized, False):
                        self._hold_active[normalized] = False
                        on_release()
                
                keyboard.add_hotkey(normalized, on_press_handler, suppress=False)
                keyboard.on_release(lambda e: self._check_release(normalized, hotkey, on_release_handler))
                
                self._hold_hotkeys[normalized] = {
                    'callback': callback,
                    'on_release': on_release,
                    'on_release_handler': on_release_handler
                }
                logger.info(f"Зарегистрирована горячая клавиша (hold): {normalized} ({description})")
            else:
                # Обычный режим toggle
                keyboard.add_hotkey(normalized, callback)
                logger.info(f"Зарегистрирована горячая клавиша (toggle): {normalized} ({description})")
            
            self.hotkeys[normalized] = hotkey
            self.callbacks[normalized] = callback
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при регистрации горячей клавиши {hotkey}: {e}")
            return False
    
    def _check_release(self, normalized, hotkey, on_release_handler):
        """Проверка отпускания клавиш для hold режима."""
        if normalized not in self._hold_hotkeys:
            return
        if not self._hold_active.get(normalized, False):
            return
        
        # Проверяем, отпущена ли основная клавиша или модификаторы
        parts = hotkey.lower().replace('+', ' ').split()
        for part in parts:
            key_map = {'win': 'windows', 'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift'}
            key_to_check = key_map.get(part, part)
            if not keyboard.is_pressed(key_to_check):
                on_release_handler()
                return
    
    def unregister_hotkey(self, hotkey):
        """
        Отмена регистрации горячей клавиши.
        
        Args:
            hotkey: Комбинация клавиш
        """
        try:
            normalized = self._normalize_hotkey(hotkey)
            
            # Убираем hold-режим если был
            if normalized in self._hold_hotkeys:
                del self._hold_hotkeys[normalized]
            if normalized in self._hold_active:
                del self._hold_active[normalized]
            
            if normalized in self.hotkeys:
                try:
                    keyboard.remove_hotkey(normalized)
                except:
                    pass
                del self.hotkeys[normalized]
                if normalized in self.callbacks:
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
        self._hold_hotkeys.clear()
        self._hold_active.clear()
        # Снимаем все обработчики release
        try:
            keyboard.unhook_all()
        except:
            pass
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

