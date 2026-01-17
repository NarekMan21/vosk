"""
Модуль управления конфигурацией приложения.
"""
import json
import os
import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """Класс для управления настройками приложения."""
    
    def __init__(self, config_path="config.json"):
        """
        Инициализация конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации (может быть относительным или абсолютным)
        """
        self.config_path = Path(config_path)
        # Если путь относительный и файл не найден, пробуем найти в текущей директории
        if not self.config_path.is_absolute() and not self.config_path.exists():
            # Пробуем найти в текущей рабочей директории
            current_dir = Path.cwd() / self.config_path
            if current_dir.exists():
                self.config_path = current_dir
        
        self.config = self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации с валидацией и восстановлением."""
        defaults = self._get_default_config()
        
        if not self.config_path.exists():
            logger.info(f"Файл конфигурации не найден: {self.config_path}")
            logger.info("Создаю файл с настройками по умолчанию")
            self._save_config(defaults)
            return defaults
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Пустой файл
            if not content:
                logger.warning("Файл конфигурации пуст, использую defaults")
                self._save_config(defaults)
                return defaults
            
            # Парсинг JSON
            loaded = json.loads(content)
            
            # Merge с defaults (заполняем недостающие поля)
            merged = self._deep_merge(defaults, loaded)
            
            # Проверяем, были ли добавлены недостающие поля
            if merged != loaded:
                logger.info("Конфигурация дополнена недостающими полями")
            
            logger.info(f"Конфигурация загружена из {self.config_path}")
            return merged
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в конфигурации: {e}")
            
            # Создаем backup битого файла
            backup_path = self.config_path.with_suffix('.json.broken')
            try:
                shutil.copy(self.config_path, backup_path)
                logger.info(f"Битый конфиг сохранён в {backup_path}")
            except Exception as backup_err:
                logger.warning(f"Не удалось сохранить backup: {backup_err}")
            
            logger.info("Использую настройки по умолчанию")
            self._save_config(defaults)
            return defaults
            
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            logger.info("Использую настройки по умолчанию")
            return defaults
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Глубокое слияние словарей.
        base - базовый словарь (defaults)
        override - словарь с переопределениями (loaded)
        Возвращает новый словарь с данными из override, дополненный из base.
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Рекурсивное слияние вложенных словарей
                result[key] = self._deep_merge(result[key], value)
            else:
                # Переопределение значения
                result[key] = value
        
        return result
    
    def _get_default_config(self):
        """Получение конфигурации по умолчанию."""
        return {
            "audio": {
                "sample_rate": 16000,
                "chunk_size": 8000,  # Увеличено для меньших накладных расходов
                "channels": 1,
                "device_index": None  # None = устройство по умолчанию
            },
            "vosk": {
                "model_path": "models/vosk-model-ru-0.42",
                "language": "ru"
            },
            "hotkeys": {
                "toggle": "win+h",
                "pause": "ctrl+shift+p",
                "hold_mode": False  # False = toggle, True = hold (push-to-talk)
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
            "vad": {
                "enabled": True,
                "aggressiveness": 2  # 0-3, где 3 = максимальная фильтрация
            },
            "notifications": {
                "enabled": True,       # Toast-уведомления
                "sound_enabled": True  # Звуковая обратная связь
            },
            "auto_start": False,
            "log_level": "INFO",
            "tutorial_shown": False,
            "check_updates": True,
            "dark_theme": True  # Тёмная тема по умолчанию
        }
    
    def _save_config(self, config=None):
        """
        Атомарное сохранение конфигурации в файл.
        Записывает во временный файл, затем делает atomic rename.
        """
        if config is None:
            config = self.config
        
        tmp_path = None
        try:
            # Создаём временный файл в той же директории
            dir_path = self.config_path.parent
            dir_path.mkdir(parents=True, exist_ok=True)
            
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json.tmp',
                dir=str(dir_path),
                delete=False,
                encoding='utf-8'
            ) as tmp:
                json.dump(config, tmp, ensure_ascii=False, indent=2)
                tmp_path = Path(tmp.name)
            
            # Атомарный rename (на Windows используем replace)
            tmp_path.replace(self.config_path)
            logger.info(f"Конфигурация сохранена в {self.config_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")
            # Удаляем временный файл если остался
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except:
                    pass
            raise
    
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
    def audio_device_index(self):
        """Индекс аудиоустройства (None = по умолчанию)."""
        return self.get("audio.device_index", None)
    
    @property
    def vosk_model_path(self):
        """Путь к модели Vosk."""
        return self.get("vosk.model_path", "models/vosk-model-ru-0.42")
    
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
    def hotkey_hold_mode(self):
        """Режим горячей клавиши: False = toggle, True = hold (зажатие)."""
        return self.get("hotkeys.hold_mode", False)
    
    @property
    def voice_commands(self):
        """Словарь голосовых команд."""
        return self.get("voice_commands", {})
    
    @property
    def input_method(self):
        """Способ ввода текста: clipboard или typing."""
        return self.get("input.method", "clipboard")

    @property
    def vad_enabled(self):
        """Включён ли VAD фильтр тишины."""
        return self.get("vad.enabled", True)
    
    @property
    def vad_aggressiveness(self):
        """Агрессивность VAD (0-3)."""
        return self.get("vad.aggressiveness", 2)
    
    @property
    def notifications_enabled(self):
        """Включены ли toast-уведомления."""
        return self.get("notifications.enabled", True)
    
    @property
    def sound_enabled(self):
        """Включена ли звуковая обратная связь."""
        return self.get("notifications.sound_enabled", True)
    
    @property
    def auto_start(self):
        """Автозапуск при старте."""
        return self.get("auto_start", False)
    
    @property
    def log_level(self):
        """Уровень логирования."""
        return self.get("log_level", "INFO")

