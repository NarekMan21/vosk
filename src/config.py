"""
Модуль управления конфигурацией приложения.
"""
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """Класс для управления настройками приложения."""
    
    def __init__(self, config_path="config.json"):
        """
        Инициализация конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации из файла."""
        if not self.config_path.exists():
            logger.warning(f"Файл конфигурации {self.config_path} не найден. Создаю файл с настройками по умолчанию.")
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Конфигурация загружена из {self.config_path}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при чтении конфигурации: {e}. Использую настройки по умолчанию.")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Получение конфигурации по умолчанию."""
        return {
            "audio": {
                "sample_rate": 16000,
                "chunk_size": 4000,
                "channels": 1
            },
            "vosk": {
                "model_path": "models/vosk-model-small-ru-0.22",
                "language": "ru"
            },
            "hotkeys": {
                "toggle": "win+h",
                "pause": "ctrl+shift+p"
            },
            "input": {
                "method": "clipboard"  # clipboard or typing
            },
            "voice_commands": {
                "запятая": ",",
                "точка": ".",
                "восклицательный знак": "!",
                "вопросительный знак": "?",
                "двоеточие": ":",
                "точка с запятой": ";",
                "новая строка": "\n",
                "абзац": "\n\n",
                "пробел": " "
            },
            "auto_start": False,
            "log_level": "INFO"
        }
    
    def _save_config(self, config=None):
        """Сохранение конфигурации в файл."""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"Конфигурация сохранена в {self.config_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")
    
    def get(self, key, default=None):
        """
        Получение значения конфигурации.
        
        Args:
            key: Ключ конфигурации (можно использовать точечную нотацию, например "audio.sample_rate")
            default: Значение по умолчанию
        
        Returns:
            Значение конфигурации или default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """
        Установка значения конфигурации.
        
        Args:
            key: Ключ конфигурации (можно использовать точечную нотацию)
            value: Новое значение
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save_config()
    
    def save(self):
        """Сохранение текущей конфигурации в файл."""
        self._save_config()
    
    @property
    def audio_sample_rate(self):
        """Частота дискретизации аудио."""
        return self.get("audio.sample_rate", 16000)
    
    @property
    def audio_chunk_size(self):
        """Размер чанка аудио."""
        return self.get("audio.chunk_size", 4000)
    
    @property
    def audio_channels(self):
        """Количество каналов аудио."""
        return self.get("audio.channels", 1)
    
    @property
    def vosk_model_path(self):
        """Путь к модели Vosk."""
        return self.get("vosk.model_path", "models/vosk-model-small-ru-0.22")
    
    @property
    def vosk_words(self):
        """Включать информацию о словах в результатах Vosk."""
        return self.get("vosk.words", True)
    
    @property
    def vosk_partial_words(self):
        """Включать информацию о словах в частичных результатах Vosk."""
        return self.get("vosk.partial_words", True)
    
    @property
    def hotkey_toggle(self):
        """Горячая клавиша для включения/выключения."""
        return self.get("hotkeys.toggle", "ctrl+shift+v")
    
    @property
    def hotkey_pause(self):
        """Горячая клавиша для паузы."""
        return self.get("hotkeys.pause", "ctrl+shift+p")
    
    @property
    def voice_commands(self):
        """Словарь голосовых команд."""
        return self.get("voice_commands", {})
    
    @property
    def input_method(self):
        """Способ ввода текста: clipboard или typing."""
        return self.get("input.method", "clipboard")

    @property
    def auto_start(self):
        """Автозапуск при старте."""
        return self.get("auto_start", False)
    
    @property
    def log_level(self):
        """Уровень логирования."""
        return self.get("log_level", "INFO")

