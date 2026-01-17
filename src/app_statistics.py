"""
Модуль статистики использования приложения.

Сохраняет данные между сессиями в JSON-файле.
"""
import json
import logging
import time
from pathlib import Path
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


class Statistics:
    """Класс для сбора и хранения статистики использования."""
    
    def __init__(self, stats_file: Optional[Path] = None):
        """
        Инициализация статистики.
        
        Args:
            stats_file: Путь к файлу статистики (по умолчанию stats.json рядом с config)
        """
        if stats_file is None:
            # По умолчанию в той же директории что и config
            import sys
            if getattr(sys, 'frozen', False):
                base_path = Path(sys.executable).parent
            else:
                base_path = Path(__file__).parent.parent
            stats_file = base_path / 'stats.json'
        
        self.stats_file = Path(stats_file)
        self._data = self._load()
        
        # Текущая сессия
        self._session_start: Optional[float] = None
        self._session_words = 0
    
    def _load(self) -> dict:
        """Загрузка статистики из файла."""
        default = {
            "total_words": 0,
            "total_time_seconds": 0,
            "sessions_count": 0,
            "first_use": None,
            "last_use": None,
            "daily": {}  # "2024-01-15": {"words": 100, "time": 3600}
        }
        
        if not self.stats_file.exists():
            return default
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Merge с defaults для обратной совместимости
            for key, value in default.items():
                if key not in data:
                    data[key] = value
            return data
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
            return default
    
    def _save(self):
        """Сохранение статистики в файл."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")
    
    def start_session(self):
        """Начало новой сессии."""
        self._session_start = time.time()
        self._session_words = 0
        self._data["sessions_count"] += 1
        
        now = datetime.now().isoformat()
        if self._data["first_use"] is None:
            self._data["first_use"] = now
        self._data["last_use"] = now
        
        logger.info(f"Сессия #{self._data['sessions_count']} начата")
    
    def end_session(self):
        """Завершение сессии."""
        if self._session_start is None:
            return
        
        session_time = time.time() - self._session_start
        self._data["total_time_seconds"] += int(session_time)
        
        # Обновляем дневную статистику
        today = date.today().isoformat()
        if today not in self._data["daily"]:
            self._data["daily"][today] = {"words": 0, "time": 0}
        self._data["daily"][today]["time"] += int(session_time)
        
        self._save()
        
        logger.info(f"Сессия завершена: {self._session_words} слов за {int(session_time)} сек")
        self._session_start = None
    
    def add_words(self, count: int):
        """
        Добавить распознанные слова.
        
        Args:
            count: Количество слов
        """
        if count <= 0:
            return
        
        self._session_words += count
        self._data["total_words"] += count
        
        # Обновляем дневную статистику
        today = date.today().isoformat()
        if today not in self._data["daily"]:
            self._data["daily"][today] = {"words": 0, "time": 0}
        self._data["daily"][today]["words"] += count
        
        # Сохраняем каждые 10 слов
        if self._session_words % 10 == 0:
            self._save()
    
    @property
    def session_words(self) -> int:
        """Слов в текущей сессии."""
        return self._session_words
    
    @property
    def session_time(self) -> int:
        """Время текущей сессии в секундах."""
        if self._session_start is None:
            return 0
        return int(time.time() - self._session_start)
    
    @property
    def total_words(self) -> int:
        """Всего слов за всё время."""
        return self._data["total_words"]
    
    @property
    def total_time(self) -> int:
        """Всего времени за всё время (секунды)."""
        return self._data["total_time_seconds"]
    
    @property
    def sessions_count(self) -> int:
        """Количество сессий."""
        return self._data["sessions_count"]
    
    @property
    def today_words(self) -> int:
        """Слов за сегодня."""
        today = date.today().isoformat()
        return self._data["daily"].get(today, {}).get("words", 0)
    
    @property
    def today_time(self) -> int:
        """Время за сегодня (секунды)."""
        today = date.today().isoformat()
        return self._data["daily"].get(today, {}).get("time", 0)
    
    def get_summary(self) -> dict:
        """
        Получить сводку статистики.
        
        Returns:
            Словарь с ключевыми метриками
        """
        return {
            "session_words": self.session_words,
            "session_time": self.session_time,
            "today_words": self.today_words,
            "today_time": self.today_time,
            "total_words": self.total_words,
            "total_time": self.total_time,
            "sessions_count": self.sessions_count
        }
    
    def format_time(self, seconds: int) -> str:
        """
        Форматирование времени для отображения.
        
        Args:
            seconds: Время в секундах
            
        Returns:
            Строка в формате "Xч Yм" или "Yм Zс"
        """
        if seconds < 60:
            return f"{seconds}с"
        elif seconds < 3600:
            m = seconds // 60
            s = seconds % 60
            return f"{m}м {s}с"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h}ч {m}м"
