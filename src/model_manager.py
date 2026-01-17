"""
Модуль управления моделями распознавания речи.

Позволяет скачивать, удалять и переключать модели Vosk.
"""
import json
import logging
import os
import shutil
import threading
import zipfile
from pathlib import Path
from typing import Optional, Callable, List, Dict
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Каталог моделей Vosk для русского языка
AVAILABLE_MODELS = [
    {
        "id": "vosk-model-small-ru-0.22",
        "name": "Быстрая (Small)",
        "description": "Быстрая модель, базовое качество. Рекомендуется для слабых ПК.",
        "size_mb": 45,
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
        "quality": "basic"
    },
    {
        "id": "vosk-model-ru-0.42",
        "name": "Качественная (Large)",
        "description": "Высокое качество распознавания. Требует больше RAM (~2 ГБ).",
        "size_mb": 1800,
        "url": "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip",
        "quality": "high"
    }
]


class ModelManager:
    """Менеджер моделей распознавания речи."""
    
    def __init__(self, models_dir: Path):
        """
        Инициализация менеджера моделей.
        
        Args:
            models_dir: Директория для хранения моделей
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._download_thread: Optional[threading.Thread] = None
        self._download_cancel = False
        self._download_progress = 0.0
        self._download_status = ""
    
    def get_available_models(self) -> List[Dict]:
        """
        Получить список доступных моделей.
        
        Returns:
            Список словарей с информацией о моделях
        """
        models = []
        for model_info in AVAILABLE_MODELS:
            model = model_info.copy()
            model_path = self.models_dir / model["id"]
            model["is_downloaded"] = model_path.exists()
            model["path"] = str(model_path) if model["is_downloaded"] else None
            models.append(model)
        return models
    
    def get_downloaded_models(self) -> List[Dict]:
        """
        Получить список скачанных моделей.
        
        Returns:
            Список словарей со скачанными моделями
        """
        return [m for m in self.get_available_models() if m["is_downloaded"]]
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """Проверить, скачана ли модель."""
        model_path = self.models_dir / model_id
        return model_path.exists()
    
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """
        Получить путь к модели.
        
        Returns:
            Path если модель скачана, None иначе
        """
        model_path = self.models_dir / model_id
        return model_path if model_path.exists() else None
    
    def download_model(
        self,
        model_id: str,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ):
        """
        Скачать модель в фоне.
        
        Args:
            model_id: ID модели для скачивания
            on_progress: Callback(progress: 0.0-1.0, status: str)
            on_complete: Callback(success: bool, message: str)
        """
        # Найти модель в каталоге
        model_info = None
        for m in AVAILABLE_MODELS:
            if m["id"] == model_id:
                model_info = m
                break
        
        if not model_info:
            if on_complete:
                on_complete(False, f"Модель {model_id} не найдена")
            return
        
        # Уже скачана?
        if self.is_model_downloaded(model_id):
            if on_complete:
                on_complete(True, "Модель уже скачана")
            return
        
        # Уже идёт скачивание?
        if self._download_thread and self._download_thread.is_alive():
            if on_complete:
                on_complete(False, "Уже идёт скачивание другой модели")
            return
        
        # Запуск скачивания в фоне
        self._download_cancel = False
        self._download_thread = threading.Thread(
            target=self._download_worker,
            args=(model_info, on_progress, on_complete),
            daemon=True
        )
        self._download_thread.start()
    
    def _download_worker(
        self,
        model_info: Dict,
        on_progress: Optional[Callable],
        on_complete: Optional[Callable]
    ):
        """Рабочий поток скачивания."""
        model_id = model_info["id"]
        url = model_info["url"]
        zip_path = self.models_dir / f"{model_id}.zip"
        extract_path = self.models_dir / model_id
        
        try:
            # Скачивание
            self._download_status = "Подключение..."
            if on_progress:
                on_progress(0.0, self._download_status)
            
            request = Request(url, headers={'User-Agent': 'VoiceInput/1.0'})
            response = urlopen(request, timeout=30)
            
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 MB
            
            with open(zip_path, 'wb') as f:
                while True:
                    if self._download_cancel:
                        raise InterruptedError("Скачивание отменено")
                    
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = downloaded / total_size
                        speed_mb = downloaded / 1024 / 1024
                        total_mb = total_size / 1024 / 1024
                        self._download_status = f"Скачано: {speed_mb:.1f} / {total_mb:.1f} МБ"
                        self._download_progress = progress
                        if on_progress:
                            on_progress(progress * 0.9, self._download_status)  # 90% на скачивание
            
            # Распаковка
            self._download_status = "Распаковка..."
            if on_progress:
                on_progress(0.9, self._download_status)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.models_dir)
            
            # Удаление zip
            zip_path.unlink()
            
            # Проверка
            if extract_path.exists():
                self._download_status = "Готово"
                if on_progress:
                    on_progress(1.0, self._download_status)
                if on_complete:
                    on_complete(True, f"Модель {model_info['name']} успешно скачана")
                logger.info(f"Модель {model_id} успешно скачана")
            else:
                raise FileNotFoundError("Модель не найдена после распаковки")
                
        except InterruptedError as e:
            # Отмена — очистка
            if zip_path.exists():
                zip_path.unlink()
            if on_complete:
                on_complete(False, str(e))
            logger.info(f"Скачивание {model_id} отменено")
            
        except Exception as e:
            # Ошибка — очистка
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except:
                    pass
            error_msg = f"Ошибка скачивания: {e}"
            if on_complete:
                on_complete(False, error_msg)
            logger.error(error_msg)
    
    def cancel_download(self):
        """Отменить текущее скачивание."""
        self._download_cancel = True
    
    def is_downloading(self) -> bool:
        """Проверить, идёт ли скачивание."""
        return self._download_thread is not None and self._download_thread.is_alive()
    
    @property
    def download_progress(self) -> float:
        """Прогресс скачивания (0.0 - 1.0)."""
        return self._download_progress
    
    @property
    def download_status(self) -> str:
        """Статус скачивания."""
        return self._download_status
    
    def delete_model(self, model_id: str) -> bool:
        """
        Удалить модель.
        
        Args:
            model_id: ID модели для удаления
            
        Returns:
            True если успешно, False иначе
        """
        model_path = self.models_dir / model_id
        
        if not model_path.exists():
            logger.warning(f"Модель {model_id} не найдена для удаления")
            return False
        
        try:
            shutil.rmtree(model_path)
            logger.info(f"Модель {model_id} удалена")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления модели {model_id}: {e}")
            return False
    
    def get_model_size_on_disk(self, model_id: str) -> int:
        """
        Получить размер модели на диске (байты).
        
        Returns:
            Размер в байтах или 0 если модель не найдена
        """
        model_path = self.models_dir / model_id
        if not model_path.exists():
            return 0
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(model_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        
        return total_size
