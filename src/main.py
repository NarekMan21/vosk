"""
Главный модуль приложения голосового ввода.
"""
import sys
import logging
import threading
import time
import os
from pathlib import Path

# Добавляем путь к модулям
# В exe файле __file__ указывает на временную директорию PyInstaller
if getattr(sys, 'frozen', False):
    # Запущено как .exe
    # Модули должны быть в sys.path автоматически благодаря pathex в spec
    pass
else:
    # Запущено как скрипт
    sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from audio_capture import AudioCapture
from speech_recognition import SpeechRecognition
from text_input import TextInput
from voice_commands import VoiceCommands
from system_tray import SystemTray
from hotkey_manager import HotkeyManager


def get_base_path():
    """
    Определяет базовую директорию приложения.
    Работает как при запуске из скрипта, так и из .exe файла.
    """
    if getattr(sys, 'frozen', False):
        # Запущено как .exe (PyInstaller)
        # sys._MEIPASS - временная директория с распакованными файлами
        # sys.executable - путь к .exe файлу
        base_path = Path(sys.executable).parent
    else:
        # Запущено как скрипт
        base_path = Path(__file__).parent.parent
    
    return base_path


# Определяем базовую директорию
BASE_PATH = get_base_path()

# Настройка логирования
log_file = BASE_PATH / 'voice_input.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class VoiceInputApp:
    """Главный класс приложения голосового ввода."""
    
    def __init__(self):
        """Инициализация приложения."""
        # Используем базовую директорию для поиска config.json
        config_path = BASE_PATH / 'config.json'
        self.config = Config(str(config_path))
        self.audio_capture = None
        self.speech_recognition = None
        self.text_input = TextInput(self.config.input_method)
        self.voice_commands = VoiceCommands(self.config.voice_commands)
        self.system_tray = None
        self.hotkey_manager = HotkeyManager()
        self.settings_window_open = False
        
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
                on_settings=self.open_settings
            )
            self.system_tray.start()
            
            # Инициализация распознавания речи (ДО регистрации горячих клавиш!)
            model_path = Path(self.config.vosk_model_path)
            if not model_path.is_absolute():
                # Ищем модель относительно базовой директории
                # В exe файле модель будет в той же директории что и exe
                model_path = BASE_PATH / model_path
                
                # Если не найдено, пробуем в sys._MEIPASS (для PyInstaller)
                if not model_path.exists() and hasattr(sys, '_MEIPASS'):
                    model_path = Path(sys._MEIPASS) / self.config.vosk_model_path
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Модель Vosk не найдена по пути: {model_path}\n"
                    f"Убедитесь, что модель находится в директории: {BASE_PATH / 'models'}"
                )
            
            logger.info(f"Используется модель: {model_path}")
            self.speech_recognition = SpeechRecognition(
                str(model_path),
                self.config.audio_sample_rate,
                words=self.config.vosk_words,
                partial_words=self.config.vosk_partial_words
            )
            
            # Инициализация горячих клавиш ПОСЛЕ загрузки модели
            self.hotkey_manager.start()
            self._register_hotkeys()
            
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
                self.system_tray.set_active(True, False)
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
            self.system_tray.set_active(False, False)
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
            self.system_tray.set_active(True, self.is_paused)
            tooltip = f"Голосовой ввод: {'Приостановлен' if self.is_paused else 'Активен'}"
            self.system_tray.update_tooltip(tooltip)
    
    def _process_audio(self):
        """Обработка аудиопотока в отдельном потоке."""
        if not self.speech_recognition:
            logger.error("Распознавание речи не инициализировано!")
            self.stop()
            return
        
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
                        
                        # Сохраняем текст ДО добавления пробела для корректного сравнения в следующей итерации
                        last_final_text = processed_text
                        
                        # Вводим текст
                        if processed_text:
                            # Добавляем пробел в конце, если текст не заканчивается на пробел или перевод строки
                            if not processed_text.endswith((' ', '\n', '\r')):
                                processed_text = processed_text + ' '
                            
                            self.text_input.send_text(processed_text)
                            # Безопасное логирование текста
                            text_preview = processed_text[:100] + ('...' if len(processed_text) > 100 else '')
                            logger.info(f"Введен текст: '{text_preview}' (длина: {len(processed_text)} символов)")
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

    def _register_hotkeys(self):
        """Регистрация горячих клавиш согласно текущей конфигурации."""
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

    def open_settings(self):
        """Открытие окна настроек горячих клавиш и метода ввода."""
        if self.settings_window_open:
            logger.info("Окно настроек уже открыто")
            return

        def _show_settings():
            try:
                import tkinter as tk
                from tkinter import ttk, messagebox
            except ImportError:
                logger.error("Tkinter недоступен, окно настроек открыть нельзя")
                return

            self.settings_window_open = True

            root = tk.Tk()
            root.title("Настройки горячих клавиш")
            root.resizable(False, False)

            def on_close():
                self.settings_window_open = False
                root.destroy()

            root.protocol("WM_DELETE_WINDOW", on_close)

            tk.Label(root, text="Включение/выключение:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
            toggle_var = tk.StringVar(value=self.config.hotkey_toggle)
            tk.Entry(root, textvariable=toggle_var, width=20).grid(row=0, column=1, padx=10, pady=5)

            tk.Label(root, text="Пауза:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
            pause_var = tk.StringVar(value=self.config.hotkey_pause)
            tk.Entry(root, textvariable=pause_var, width=20).grid(row=1, column=1, padx=10, pady=5)

            tk.Label(root, text="Метод ввода:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
            method_var = tk.StringVar(value=self.config.input_method)
            ttk.Combobox(
                root,
                textvariable=method_var,
                values=("clipboard", "typing"),
                state="readonly",
                width=17
            ).grid(row=2, column=1, padx=10, pady=5)

            def save_settings():
                new_toggle = toggle_var.get().strip()
                new_pause = pause_var.get().strip()
                new_method = method_var.get().strip()

                if not new_toggle or not new_pause:
                    messagebox.showerror("Ошибка", "Горячие клавиши не должны быть пустыми.")
                    return

                try:
                    self.config.set("hotkeys.toggle", new_toggle)
                    self.config.set("hotkeys.pause", new_pause)
                    self.config.set("input.method", new_method)
                    self.text_input.input_method = new_method

                    self.hotkey_manager.unregister_all()
                    self._register_hotkeys()

                    messagebox.showinfo("Готово", "Настройки сохранены.")
                    on_close()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")

            button_frame = tk.Frame(root)
            button_frame.grid(row=3, column=0, columnspan=2, pady=10)

            tk.Button(button_frame, text="Сохранить", command=save_settings, width=12).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Отмена", command=on_close, width=12).pack(side=tk.LEFT, padx=5)

            # Позиционирование окна в правом нижнем углу экрана (ближе к трею)
            # Обновляем окно для получения корректных размеров
            root.update_idletasks()
            window_width = root.winfo_width()
            window_height = root.winfo_height()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            # Позиция: правый нижний угол с небольшим отступом (50px от правого края, 100px от нижнего)
            x = screen_width - window_width - 50
            y = screen_height - window_height - 100
            
            root.geometry(f"+{x}+{y}")

            root.mainloop()

        threading.Thread(target=_show_settings, daemon=True).start()

def main():
    """Точка входа в приложение."""
    app = VoiceInputApp()
    app.run()

if __name__ == "__main__":
    main()

