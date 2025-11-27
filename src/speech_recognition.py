"""
Модуль распознавания речи через Vosk.
"""
import json
import logging
import os
from pathlib import Path
import vosk

logger = logging.getLogger(__name__)

class SpeechRecognition:
    """Класс для распознавания речи с использованием Vosk."""
    
    def __init__(self, model_path, sample_rate=16000, words=True, partial_words=True):
        """
        Инициализация распознавания речи.
        
        Args:
            model_path: Путь к модели Vosk
            sample_rate: Частота дискретизации аудио (должна совпадать с моделью)
            words: Включать информацию о словах в результатах (SetWords)
            partial_words: Включать информацию о словах в частичных результатах (SetPartialWords)
        """
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate
        self.words = words
        self.partial_words = partial_words
        self.model = None
        self.recognizer = None
        self._load_model()
    
    def _load_model(self):
        """Загрузка модели Vosk."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Модель Vosk не найдена по пути: {self.model_path}\n"
                f"Скачайте модель с https://alphacephei.com/vosk/models\n"
                f"Рекомендуется: vosk-model-small-ru-0.22"
            )
        
        try:
            logger.info(f"Загрузка модели Vosk из {self.model_path}")
            self.model = vosk.Model(str(self.model_path))
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
            
            # Настройка параметров распознавания согласно документации Vosk
            if self.words:
                self.recognizer.SetWords(True)
                logger.debug("Включена информация о словах в результатах")
            
            if self.partial_words:
                try:
                    # SetPartialWords доступен в новых версиях Vosk
                    self.recognizer.SetPartialWords(True)
                    logger.debug("Включена информация о словах в частичных результатах")
                except AttributeError:
                    logger.debug("SetPartialWords не поддерживается в этой версии Vosk")
            
            logger.info("Модель Vosk загружена успешно")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели Vosk: {e}")
            raise
    
    def recognize_chunk(self, audio_chunk):
        """
        Распознавание текста из аудио чанка.
        
        Args:
            audio_chunk: Байты аудиоданных
        
        Returns:
            Кортеж (text, is_final) где text - распознанный текст, is_final - финальный ли результат
        """
        if not self.recognizer:
            return None, False
        
        try:
            # Принимаем аудиоданные
            if self.recognizer.AcceptWaveform(audio_chunk):
                # Финальный результат
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    logger.debug(f"Распознан текст (финальный): {text}")
                    return text, True
            else:
                # Частичный результат
                result = json.loads(self.recognizer.PartialResult())
                text = result.get("partial", "").strip()
                if text:
                    logger.debug(f"Распознан текст (частичный): {text}")
                    return text, False
            
            return None, False
            
        except Exception as e:
            logger.error(f"Ошибка при распознавании: {e}")
            return None, False
    
    def reset(self):
        """Сброс состояния распознавателя."""
        if self.recognizer:
            try:
                # Получаем финальный результат перед сбросом
                final_result = json.loads(self.recognizer.FinalResult())
                self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
                if self.words:
                    self.recognizer.SetWords(True)
                if self.partial_words:
                    try:
                        self.recognizer.SetPartialWords(True)
                    except AttributeError:
                        pass
                return final_result.get("text", "").strip()
            except Exception as e:
                logger.error(f"Ошибка при сбросе распознавателя: {e}")
                self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
                if self.words:
                    self.recognizer.SetWords(True)
                if self.partial_words:
                    try:
                        self.recognizer.SetPartialWords(True)
                    except AttributeError:
                        pass
                return ""
        return ""
    
    def process_audio_stream(self, audio_generator):
        """
        Обработка потока аудиоданных и генерация распознанного текста.
        
        Args:
            audio_generator: Генератор аудиоданных
        
        Yields:
            Кортеж (text, is_final) где text - распознанный текст, is_final - финальный ли результат
        """
        for audio_chunk in audio_generator:
            text, is_final = self.recognize_chunk(audio_chunk)
            if text:
                yield text, is_final

