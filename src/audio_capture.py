"""
Модуль захвата аудио с микрофона через PyAudio.
"""
import pyaudio
import logging
import threading
from queue import Queue

logger = logging.getLogger(__name__)

class AudioCapture:
    """Класс для захвата аудио с микрофона в реальном времени."""
    
    def __init__(self, sample_rate=16000, chunk_size=4000, channels=1):
        """
        Инициализация захвата аудио.
        
        Args:
            sample_rate: Частота дискретизации (Гц)
            chunk_size: Размер чанка (количество фреймов)
            channels: Количество каналов (1 = моно)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.audio = None
        self.stream = None
        self.is_recording = False
        self.audio_queue = Queue()
        self.thread = None
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback-функция для обработки аудиоданных.
        
        Args:
            in_data: Входные аудиоданные
            frame_count: Количество фреймов
            time_info: Информация о времени
            status: Статус потока
        
        Returns:
            Кортеж (None, pyaudio.paContinue)
        """
        if status:
            logger.warning(f"Статус потока: {status}")
        
        if self.is_recording:
            self.audio_queue.put(in_data)
        
        return (None, pyaudio.paContinue)
    
    def start(self):
        """Запуск захвата аудио."""
        if self.is_recording:
            logger.warning("Захват аудио уже запущен")
            return
        
        try:
            self.audio = pyaudio.PyAudio()
            
            # Поиск устройства ввода по умолчанию
            default_input = self.audio.get_default_input_device_info()
            logger.info(f"Используется устройство ввода: {default_input['name']}")
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_recording = True
            self.stream.start_stream()
            logger.info("Захват аудио запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске захвата аудио: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Остановка захвата аудио."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Ошибка при остановке потока: {e}")
            finally:
                self.stream = None
        
        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"Ошибка при завершении PyAudio: {e}")
            finally:
                self.audio = None
        
        # Очистка очереди
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                pass
        
        logger.info("Захват аудио остановлен")
    
    def read_chunk(self, timeout=1.0):
        """
        Чтение чанка аудиоданных из очереди.
        
        Args:
            timeout: Таймаут ожидания (секунды)
        
        Returns:
            Байты аудиоданных или None
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except:
            return None
    
    def get_audio_generator(self):
        """
        Генератор для получения аудиоданных в реальном времени.
        
        Yields:
            Байты аудиоданных
        """
        while self.is_recording:
            chunk = self.read_chunk()
            if chunk:
                yield chunk
    
    def __enter__(self):
        """Контекстный менеджер: вход."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер: выход."""
        self.stop()

