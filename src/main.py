"""
Главный модуль приложения голосового ввода.
"""
import sys
import logging
import threading
import time
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from audio_capture import AudioCapture
from speech_recognition import SpeechRecognition
from text_input import TextInput
from voice_commands import VoiceCommands
from system_tray import SystemTray
from hotkey_manager import HotkeyManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_input.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class VoiceInputApp:
    """Главный класс приложения голосового ввода."""
    
    def __init__(self):
        """Инициализация приложения."""
        self.config = Config()
        self.audio_capture = None
        self.speech_recognition = None
        self.text_input = TextInput()
        self.voice_commands = VoiceCommands(self.config.voice_commands)
        self.system_tray = None
        self.hotkey_manager = HotkeyManager()
        
        self.is_active = False
        self.is_paused = False
        self.processing_thread = None
        self.running = True
        
        # Настройка уровня логирования
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
    
    def initialize(self):
        """Инициализация всех компонентов."""
        try:
            logger.info("Инициализация приложения...")
            
            # Инициализация системного трея
            self.system_tray = SystemTray(
                on_toggle=self.toggle,
                on_exit=self.shutdown,
                on_settings=None  # Можно добавить позже
            )
            self.system_tray.start()
            
            # Инициализация горячих клавиш
            self.hotkey_manager.start()
            self.hotkey_manager.register_hotkey(
                self.config.hotkey_toggle,
                self.toggle,
                "Включить/выключить"
            )
            self.hotkey_manager.register_hotkey(
                self.config.hotkey_pause,
                self.pause,
                "Пауза"
            )
            
            # Инициализация распознавания речи
            model_path = Path(self.config.vosk_model_path)
            if not model_path.is_absolute():
                model_path = Path(__file__).parent.parent / model_path
            
            self.speech_recognition = SpeechRecognition(
                str(model_path),
                self.config.audio_sample_rate,
                words=self.config.vosk_words,
                partial_words=self.config.vosk_partial_words
            )
            
            logger.info("Инициализация завершена")
            
            # Автозапуск если настроено
            if self.config.auto_start:
                self.toggle()
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации: {e}", exc_info=True)
            raise
    
    def toggle(self):
        """Переключение состояния активности."""
        if self.is_active:
            self.stop()
        else:
            self.start()
    
    def start(self):
        """Запуск захвата и распознавания речи."""
        if self.is_active:
            logger.warning("Приложение уже активно")
            return
        
        try:
            logger.info("Запуск голосового ввода...")
            
            # Инициализация захвата аудио
            self.audio_capture = AudioCapture(
                sample_rate=self.config.audio_sample_rate,
                chunk_size=self.config.audio_chunk_size,
                channels=self.config.audio_channels
            )
            self.audio_capture.start()
            
            self.is_active = True
            self.is_paused = False
            
            # Обновление иконки
            if self.system_tray:
                self.system_tray.set_active(True)
                self.system_tray.update_tooltip("Голосовой ввод: Активен")
            
            # Запуск потока обработки
            self.processing_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.processing_thread.start()
            
            logger.info("Голосовой ввод запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Остановка захвата и распознавания речи."""
        if not self.is_active:
            return
        
        logger.info("Остановка голосового ввода...")
        
        self.is_active = False
        
        # Остановка захвата аудио
        if self.audio_capture:
            self.audio_capture.stop()
            self.audio_capture = None
        
        # Обновление иконки
        if self.system_tray:
            self.system_tray.set_active(False)
            self.system_tray.update_tooltip("Голосовой ввод: Неактивен")
        
        logger.info("Голосовой ввод остановлен")
    
    def pause(self):
        """Пауза/возобновление обработки."""
        if not self.is_active:
            return
        
        self.is_paused = not self.is_paused
        status = "приостановлен" if self.is_paused else "возобновлен"
        logger.info(f"Голосовой ввод {status}")
        
        if self.system_tray:
            tooltip = f"Голосовой ввод: {'Приостановлен' if self.is_paused else 'Активен'}"
            self.system_tray.update_tooltip(tooltip)
    
    def _process_audio(self):
        """Обработка аудиопотока в отдельном потоке."""
        last_final_text = ""
        
        while self.is_active and self.running:
            if self.is_paused:
                time.sleep(0.1)
                continue
            
            try:
                # Получаем аудио чанк
                audio_chunk = self.audio_capture.read_chunk(timeout=0.5)
                if not audio_chunk:
                    continue
                
                # Распознаем речь
                text, is_final = self.speech_recognition.recognize_chunk(audio_chunk)
                
                if text:
                    if is_final:
                        # Финальный результат - обрабатываем и вводим
                        processed_text = self.voice_commands.process_text(text)
                        
                        # Убираем предыдущий частичный текст если был
                        if last_final_text and last_final_text != processed_text:
                            # Можно добавить логику удаления, но это сложно
                            pass
                        
                        # Вводим текст
                        if processed_text:
                            self.text_input.send_text(processed_text)
                            logger.info(f"Введен текст: {repr(processed_text)}")
                        
                        last_final_text = processed_text
                    # Частичные результаты можно использовать для отображения в UI
                
            except Exception as e:
                logger.error(f"Ошибка при обработке аудио: {e}", exc_info=True)
                time.sleep(0.1)
    
    def shutdown(self):
        """Завершение работы приложения."""
        logger.info("Завершение работы приложения...")
        self.running = False
        self.stop()
        
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        
        if self.system_tray:
            self.system_tray.stop()
        
        logger.info("Приложение завершено")
        sys.exit(0)
    
    def run(self):
        """Запуск приложения."""
        try:
            self.initialize()
            
            # Основной цикл
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания")
            self.shutdown()
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            self.shutdown()

def main():
    """Точка входа в приложение."""
    app = VoiceInputApp()
    app.run()

if __name__ == "__main__":
    main()

