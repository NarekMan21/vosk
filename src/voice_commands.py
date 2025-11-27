"""
Модуль обработки голосовых команд для пунктуации.
"""
import logging
import re

logger = logging.getLogger(__name__)

class VoiceCommands:
    """Класс для обработки голосовых команд и замены их на символы."""
    
    def __init__(self, commands_dict=None):
        """
        Инициализация обработчика голосовых команд.
        
        Args:
            commands_dict: Словарь команд {команда: символ}
        """
        self.commands = commands_dict or {}
        # Нормализация команд (приведение к нижнему регистру)
        self.commands_normalized = {k.lower(): v for k, v in self.commands.items()}
        logger.info(f"Загружено {len(self.commands)} голосовых команд")
    
    def update_commands(self, commands_dict):
        """
        Обновление словаря команд.
        
        Args:
            commands_dict: Новый словарь команд
        """
        self.commands = commands_dict
        self.commands_normalized = {k.lower(): v for k, v in self.commands.items()}
        logger.info(f"Обновлено {len(self.commands)} голосовых команд")
    
    def process_text(self, text):
        """
        Обработка текста: замена голосовых команд на символы.
        
        Args:
            text: Исходный текст
        
        Returns:
            Обработанный текст с замененными командами
        """
        if not text:
            return text
        
        processed_text = text
        
        # Проходим по всем командам и заменяем их
        for command, replacement in self.commands_normalized.items():
            # Используем регулярное выражение для поиска команды как отдельного слова
            # Учитываем регистр и границы слов
            pattern = r'\b' + re.escape(command) + r'\b'
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)
        
        if processed_text != text:
            logger.debug(f"Текст обработан: '{text}' -> '{processed_text}'")
        
        return processed_text
    
    def is_command(self, text):
        """
        Проверка, является ли текст голосовой командой.
        
        Args:
            text: Текст для проверки
        
        Returns:
            True если это команда, False иначе
        """
        if not text:
            return False
        
        text_lower = text.lower().strip()
        return text_lower in self.commands_normalized
    
    def get_replacement(self, command):
        """
        Получение символа-замены для команды.
        
        Args:
            command: Голосовая команда
        
        Returns:
            Символ-замена или None
        """
        return self.commands_normalized.get(command.lower().strip())

