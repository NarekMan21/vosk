"""
Модуль захвата аудио с микрофона через PyAudio.
"""
import pyaudio
import logging
import threading
import time
from queue import Queue

logger = logging.getLogger(__name__)

class AudioCapture:
    """Класс для захвата аудио с микрофона в реальном времени."""
    
    def __init__(self, sample_rate=16000, chunk_size=4000, channels=1, 
                 device_index=None, on_error=None):
        """
        Инициализация захвата аудио.
        
        Args:
            sample_rate: Частота дискретизации (Гц)
            chunk_size: Размер чанка (количество фреймов)
            channels: Количество каналов (1 = моно)
            device_index: Индекс устройства (None = по умолчанию)
            on_error: Callback функция(error_message: str) при ошибках
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index
        self.on_error = on_error
        self.audio = None
        self.stream = None
        self.is_recording = False
        self.audio_queue = Queue()
        self.thread = None
        self._error_count = 0
        self._max_errors = 5
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback-функция для обработки аудиоданных с обработкой ошибок.
        
        Args:
            in_data: Входные аудиоданные
            frame_count: Количество фреймов
            time_info: Информация о времени
            status: Статус потока
        
        Returns:
            Кортеж (None, pyaudio.paContinue) или (None, pyaudio.paAbort)
        """
        if status:
            self._error_count += 1
            logger.warning(f"Ошибка аудио потока: {status} (#{self._error_count})")
            
            if self._error_count >= self._max_errors:
                error_msg = "Слишком много ошибок аудио. Проверьте микрофон."
                logger.error(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
                return (None, pyaudio.paAbort)
        else:
            # Сбрасываем счётчик при успешном чтении
            self._error_count = 0
        
        if self.is_recording and in_data:
            self.audio_queue.put(in_data)
        
        return (None, pyaudio.paContinue)
    
    def start(self):
        """Запуск захвата аудио с обработкой ошибок."""
        if self.is_recording:
            logger.warning("Захват аудио уже запущен")
            return
        
        self._error_count = 0
        
        try:
            self.audio = pyaudio.PyAudio()
            
            # Получаем информацию об устройстве
            try:
                if self.device_index is not None:
                    device_info = self.audio.get_device_info_by_index(self.device_index)
                else:
                    device_info = self.audio.get_default_input_device_info()
                # Исправляем кодировку названия устройства для корректного отображения
                device_name = AudioCapture._fix_device_name(device_info.get('name', 'Unknown'))
                logger.info(f"Используется устройство ввода: {device_name}")
            except OSError as e:
                error_msg = f"Микрофон не найден: {e}"
                logger.error(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
                raise
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_recording = True
            self.stream.start_stream()
            logger.info("Захват аудио запущен")
            
        except OSError as e:
            error_msg = f"Ошибка микрофона: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            self.stop()
            raise
        except Exception as e:
            error_msg = f"Неожиданная ошибка аудио: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
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
    
    def reconnect(self, max_attempts=5, initial_delay=1.0):
        """
        Попытка переподключения к микрофону с exponential backoff.
        
        Args:
            max_attempts: Максимальное количество попыток
            initial_delay: Начальная задержка между попытками (секунды)
        
        Returns:
            True если успешно, False если все попытки исчерпаны
        """
        delay = initial_delay
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Попытка переподключения {attempt}/{max_attempts}...")
            
            # Останавливаем предыдущее соединение
            self.stop()
            time.sleep(delay)
            
            # Проверяем доступность устройства
            if not self.is_device_available():
                logger.warning(f"Устройство недоступно, ждём {delay:.1f}с...")
                delay = min(delay * 2, 10.0)  # Exponential backoff, max 10s
                continue
            
            try:
                self.start()
                logger.info("Переподключение успешно!")
                return True
            except Exception as e:
                logger.warning(f"Попытка {attempt} не удалась: {e}")
                delay = min(delay * 2, 10.0)
        
        error_msg = "Все попытки переподключения исчерпаны"
        logger.error(error_msg)
        if self.on_error:
            self.on_error(error_msg)
        return False
    
    def is_device_available(self) -> bool:
        """
        Проверяет доступность аудиоустройства.
        
        Returns:
            True если устройство доступно, False иначе
        """
        test_audio = None
        try:
            test_audio = pyaudio.PyAudio()
            if self.device_index is not None:
                test_audio.get_device_info_by_index(self.device_index)
            else:
                test_audio.get_default_input_device_info()
            return True
        except (OSError, IOError):
            return False
        finally:
            if test_audio:
                try:
                    test_audio.terminate()
                except:
                    pass
    
    @staticmethod
    def _fix_device_name(name: str) -> str:
        """
        Исправление кодировки названия устройства.
        
        PyAudio на Windows возвращает названия устройств в кодировке CP1251,
        но Python интерпретирует их как Latin-1, что приводит к "иероглифам".
        Эта функция корректно перекодирует строку.
        
        Args:
            name: Название устройства от PyAudio
        
        Returns:
            Правильно декодированное название
        """
        if not name:
            return 'Unknown'
        
        try:
            # PyAudio возвращает строку, которая была декодирована как Latin-1
            # Нужно закодировать обратно в Latin-1 и декодировать как CP1251
            fixed_name = name.encode('latin-1').decode('cp1251')
            return fixed_name
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Если не получилось — возвращаем как есть
            return name
    
    @staticmethod
    def list_devices():
        """
        Получить список доступных устройств ввода.
        
        Returns:
            Список словарей с информацией об устройствах
        """
        devices = []
        audio = None
        try:
            audio = pyaudio.PyAudio()
            for i in range(audio.get_device_count()):
                try:
                    info = audio.get_device_info_by_index(i)
                    if info.get('maxInputChannels', 0) > 0:
                        # Исправляем кодировку названия устройства
                        raw_name = info.get('name', 'Unknown')
                        fixed_name = AudioCapture._fix_device_name(raw_name)
                        
                        devices.append({
                            'index': i,
                            'name': fixed_name,
                            'sample_rate': int(info.get('defaultSampleRate', 16000)),
                            'channels': info.get('maxInputChannels', 1)
                        })
                except:
                    pass
        finally:
            if audio:
                try:
                    audio.terminate()
                except:
                    pass
        return devices
    
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

