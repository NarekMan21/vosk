"""
Главный модуль приложения голосового ввода.
"""
import sys
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
import os
import ctypes
import signal
import atexit
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
from notifications import Notifications
from audio_feedback import AudioFeedback
from vad import VoiceActivityDetector
from autostart import is_autostart_enabled, set_autostart
from statistics import Statistics
from model_manager import ModelManager


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

# Настройка логирования с ротацией
log_file = BASE_PATH / 'voice_input.log'

# RotatingFileHandler: макс 5 МБ на файл, хранить 3 backup
file_handler = RotatingFileHandler(
    str(log_file),
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
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
        self.notifications = Notifications(enabled=self.config.notifications_enabled)
        self.audio_feedback = AudioFeedback(enabled=self.config.sound_enabled)
        self.vad = VoiceActivityDetector(
            sample_rate=self.config.audio_sample_rate,
            aggressiveness=self.config.vad_aggressiveness,
            enabled=self.config.vad_enabled
        )
        self.settings_window_open = False
        
        self.is_active = False
        self.is_paused = False
        self.processing_thread = None
        self.running = True
        self._shutdown_in_progress = False
        
        # Статистика сессии
        self.statistics = Statistics(BASE_PATH / 'stats.json')
        
        # Менеджер моделей
        self.model_manager = ModelManager(BASE_PATH / 'models')
        
        # Настройка уровня логирования
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
        
        # Регистрация обработчиков для graceful shutdown
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self):
        """Инициализация всех компонентов с гибридной загрузкой моделей."""
        try:
            logger.info("Инициализация приложения...")
            
            # Инициализация системного трея
            self.system_tray = SystemTray(
                on_toggle=self.toggle,
                on_exit=self.shutdown,
                on_settings=self.open_settings
            )
            self.system_tray.start()
            
            # Показываем индикатор загрузки
            self.system_tray.set_loading("Загрузка модели...")
            self.notifications.show_loading("Загрузка модели распознавания...")
            
            # === Гибридная загрузка моделей ===
            # Ищем маленькую и большую модели
            small_model = None
            large_model = None
            configured_model = None
            
            for model in self.model_manager.get_available_models():
                if model['is_downloaded']:
                    model_path = BASE_PATH / 'models' / model['id']
                    if model['quality'] == 'basic':
                        small_model = model_path
                    elif model['quality'] == 'high':
                        large_model = model_path
            
            # Настроенная модель
            model_path = Path(self.config.vosk_model_path)
            if not model_path.is_absolute():
                model_path = BASE_PATH / model_path
                if not model_path.exists() and hasattr(sys, '_MEIPASS'):
                    model_path = Path(sys._MEIPASS) / self.config.vosk_model_path
            
            if model_path.exists():
                configured_model = model_path
            
            # Стратегия загрузки:
            # 1. Если есть маленькая И большая — загружаем маленькую, потом большую в фоне
            # 2. Если есть только настроенная — загружаем её
            # 3. Если ничего нет — ошибка
            
            initial_model = None
            use_hybrid = False
            
            if small_model and large_model and small_model != large_model:
                # Гибридный режим: сначала маленькая, потом большая
                initial_model = small_model
                use_hybrid = True
                logger.info("Гибридная загрузка: сначала быстрая модель")
            elif configured_model:
                initial_model = configured_model
            elif small_model:
                initial_model = small_model
            elif large_model:
                initial_model = large_model
            else:
                raise FileNotFoundError(
                    f"Модель Vosk не найдена.\n"
                    f"Откройте настройки и скачайте модель."
                )
            
            # Загрузка начальной модели
            logger.info(f"Загрузка модели: {initial_model.name}")
            self.speech_recognition = SpeechRecognition(
                str(initial_model),
                self.config.audio_sample_rate,
                words=self.config.vosk_words,
                partial_words=self.config.vosk_partial_words
            )
            
            # Инициализация горячих клавиш ПОСЛЕ загрузки модели
            self.hotkey_manager.start()
            self._register_hotkeys()
            
            # Обновляем иконку трея
            if use_hybrid:
                self.system_tray.update_tooltip("VoiceInput: Готов (быстрая модель)")
                self.notifications.show("VoiceInput", "Готов! Загрузка качественной модели в фоне...")
                # Запускаем фоновую загрузку большой модели
                self._load_large_model_background(large_model)
            else:
                self.system_tray.set_ready()
                self.notifications.show_ready()
            
            self.audio_feedback.play_ready()
            
            logger.info("Инициализация завершена")
            
            # Автозапуск если настроено
            if self.config.auto_start:
                self.toggle()
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации: {e}", exc_info=True)
            if self.system_tray:
                self.system_tray.set_error("Ошибка инициализации")
            self.audio_feedback.play_error()
            self.notifications.show_error(f"Ошибка инициализации: {e}")
            raise
    
    def _load_large_model_background(self, model_path: Path):
        """Загрузка большой модели в фоновом потоке."""
        def _load():
            try:
                logger.info(f"Фоновая загрузка модели: {model_path.name}")
                
                # Обновляем статус
                if self.system_tray:
                    self.system_tray.update_tooltip("VoiceInput: Загрузка качественной модели...")
                
                # Загружаем большую модель
                import vosk
                large_model = vosk.Model(str(model_path))
                
                # Переключаемся на большую модель
                if self.speech_recognition:
                    if self.speech_recognition.switch_model(str(model_path)):
                        logger.info("Переключено на качественную модель")
                        
                        # Обновляем конфиг
                        self.config.set("vosk.model_path", f"models/{model_path.name}")
                        
                        # Уведомление
                        if self.system_tray:
                            self.system_tray.set_ready()
                            self.system_tray.update_tooltip("VoiceInput: Готов (высокое качество)")
                        self.notifications.show("VoiceInput", "✓ Переключено на качественную модель")
                    else:
                        logger.warning("Не удалось переключиться на большую модель")
                        
            except Exception as e:
                logger.error(f"Ошибка фоновой загрузки модели: {e}")
                # Оставляем маленькую модель
        
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
    
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
                channels=self.config.audio_channels,
                device_index=self.config.audio_device_index,
                on_error=self._on_audio_error
            )
            self.audio_capture.start()
            
            # Сброс VAD для нового сеанса
            self.vad.reset()
            
            self.is_active = True
            self.is_paused = False
            self.statistics.start_session()
            
            # Обновление иконки
            if self.system_tray:
                self.system_tray.set_active(True, False)
                self._update_tooltip()
            
            # Запуск потока обработки
            self.processing_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.processing_thread.start()
            
            logger.info("Голосовой ввод запущен")
            
            # Обратная связь
            self.audio_feedback.play_start()
            self.notifications.show_start()
            
        except Exception as e:
            logger.error(f"Ошибка при запуске: {e}", exc_info=True)
            self.notifications.show_error(str(e))
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
            self.system_tray.stop_animation()
            self.system_tray.set_active(False, False)
            self.system_tray.update_tooltip("Голосовой ввод: Неактивен")
        
        # Завершение сессии статистики
        self.statistics.end_session()
        
        logger.info("Голосовой ввод остановлен")
        
        # Обратная связь
        self.audio_feedback.play_stop()
        self.notifications.show_stop()
    
    def pause(self):
        """Пауза/возобновление обработки."""
        if not self.is_active:
            return
        
        self.is_paused = not self.is_paused
        status = "приостановлен" if self.is_paused else "возобновлён"
        logger.info(f"Голосовой ввод {status}")
        
        if self.system_tray:
            self.system_tray.set_active(True, self.is_paused)
            if self.is_paused:
                self.system_tray.stop_animation()
            self._update_tooltip()
    
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
                
                # VAD фильтр — пропускаем тишину для экономии CPU
                is_speech = self.vad.is_speech(audio_chunk)
                
                # Обновляем анимацию трея
                if self.system_tray:
                    self.system_tray.set_speaking(is_speech)
                
                if not is_speech:
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
                            
                            # Подсчёт слов и обновление статистики
                            word_count = self._count_words(processed_text)
                            self.statistics.add_words(word_count)
                            self._update_tooltip()
                            
                            # Безопасное логирование текста
                            text_preview = processed_text[:100] + ('...' if len(processed_text) > 100 else '')
                            logger.info(f"Введен текст: '{text_preview}' (слов: {word_count}, всего сессия: {self.statistics.session_words})")
                    # Частичные результаты можно использовать для отображения в UI
                
            except Exception as e:
                logger.error(f"Ошибка при обработке аудио: {e}", exc_info=True)
                time.sleep(0.1)
    
    def shutdown(self):
        """Завершение работы приложения."""
        if self._shutdown_in_progress:
            return
        self._shutdown_in_progress = True
        
        logger.info("Завершение работы приложения...")
        self.running = False
        self.stop()
        
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        
        if self.system_tray:
            self.system_tray.stop()
        
        logger.info("Приложение завершено")
        sys.exit(0)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown."""
        logger.info(f"Получен сигнал {signum}, завершение...")
        self.shutdown()
    
    def _cleanup(self):
        """Финальная очистка ресурсов при завершении."""
        if self._shutdown_in_progress:
            return  # shutdown уже обработал
        
        logger.info("Очистка ресурсов (atexit)...")
        
        # Остановка распознавания
        if self.is_active:
            try:
                self.stop()
            except:
                pass
        
        # Освобождение mutex
        try:
            release_mutex()
        except:
            pass
        
        # Закрытие аудио
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except:
                pass
        
        # Остановка горячих клавиш
        if self.hotkey_manager:
            try:
                self.hotkey_manager.stop()
            except:
                pass
        
        # Остановка трея
        if self.system_tray:
            try:
                self.system_tray.stop()
            except:
                pass
        
        logger.info("Ресурсы освобождены")
    
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

    def _on_audio_error(self, error_msg: str):
        """Обработчик ошибок аудио захвата."""
        logger.error(f"Ошибка аудио: {error_msg}")
        self.notifications.show_error(error_msg)
        self.audio_feedback.play_error()
        if self.system_tray:
            self.system_tray.set_error("Ошибка микрофона")
    
    def _update_tooltip(self):
        """Обновление tooltip с информацией о статусе и статистике."""
        if not self.system_tray:
            return
        
        lines = ["VoiceInput"]
        
        # Статус
        if self.is_active:
            if self.is_paused:
                lines.append("⏸ Пауза")
            else:
                lines.append("🎤 Активен")
        else:
            lines.append("⏹ Неактивен")
        
        # Статистика сессии
        stats = self.statistics.get_summary()
        
        if self.is_active:
            # Слов в сессии
            lines.append(f"Сессия: {stats['session_words']} слов")
            # Время сессии
            lines.append(f"Время: {self.statistics.format_time(stats['session_time'])}")
        
        # Статистика за сегодня
        lines.append(f"Сегодня: {stats['today_words']} слов")
        
        # Всего
        lines.append(f"Всего: {stats['total_words']} слов")
        
        tooltip = "\n".join(lines)
        self.system_tray.update_tooltip(tooltip)
    
    def _count_words(self, text: str) -> int:
        """Подсчёт слов в тексте."""
        if not text:
            return 0
        # Простой подсчёт — разделение по пробелам
        words = [w for w in text.split() if w.strip()]
        return len(words)
    
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
        """Открытие окна настроек с выбором микрофона, горячих клавиш и метода ввода."""
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
            root.title("Настройки VoiceInput")
            root.resizable(False, False)

            def on_close():
                self.settings_window_open = False
                root.destroy()

            root.protocol("WM_DELETE_WINDOW", on_close)
            
            # Функция для создания tooltip
            def create_tooltip(widget, text):
                def show_tooltip(event):
                    tooltip = tk.Toplevel(widget)
                    tooltip.wm_overrideredirect(True)
                    tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
                    label = tk.Label(tooltip, text=text, background="#ffffe0", 
                                    relief="solid", borderwidth=1, padx=5, pady=2)
                    label.pack()
                    widget._tooltip = tooltip
                    widget.after(3000, lambda: tooltip.destroy() if tooltip.winfo_exists() else None)
                
                def hide_tooltip(event):
                    if hasattr(widget, '_tooltip') and widget._tooltip.winfo_exists():
                        widget._tooltip.destroy()
                
                widget.bind("<Enter>", show_tooltip)
                widget.bind("<Leave>", hide_tooltip)
            
            # === Секция: Качество (предустановки) ===
            quality_frame = ttk.LabelFrame(root, text="🎯 Качество распознавания", padding=10)
            quality_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
            
            # Определяем текущее качество на основе настроек
            current_vad = self.config.vad_aggressiveness
            current_chunk = self.config.audio_chunk_size
            if current_vad >= 3 and current_chunk >= 8000:
                current_quality = "fast"
            elif current_vad <= 1:
                current_quality = "quality"
            else:
                current_quality = "balanced"
            
            quality_var = tk.StringVar(value=current_quality)
            
            qualities = [
                ("⚡ Быстрое", "fast", "Меньше нагрузка CPU, базовое качество"),
                ("⚖️ Сбалансированное", "balanced", "Оптимальный баланс скорости и качества"),
                ("🎯 Точное", "quality", "Максимальное качество, выше нагрузка CPU")
            ]
            
            for i, (label, value, desc) in enumerate(qualities):
                rb = ttk.Radiobutton(
                    quality_frame,
                    text=label,
                    variable=quality_var,
                    value=value
                )
                rb.grid(row=0, column=i, padx=10, pady=5)
                create_tooltip(rb, desc)
            
            # === Секция: Микрофон ===
            mic_frame = ttk.LabelFrame(root, text="🎤 Микрофон", padding=10)
            mic_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
            
            # Получаем список устройств
            devices = AudioCapture.list_devices()
            device_names = ["По умолчанию"] + [d['name'] for d in devices]
            device_indices = [None] + [d['index'] for d in devices]
            
            # Текущий выбор
            current_device_index = self.config.audio_device_index
            current_selection = 0
            if current_device_index is not None:
                for i, idx in enumerate(device_indices):
                    if idx == current_device_index:
                        current_selection = i
                        break
            
            tk.Label(mic_frame, text="Устройство:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            device_var = tk.StringVar(value=device_names[current_selection])
            device_combo = ttk.Combobox(
                mic_frame,
                textvariable=device_var,
                values=device_names,
                state="readonly",
                width=35
            )
            device_combo.grid(row=0, column=1, padx=5, pady=5)
            
            def test_microphone():
                """Тест выбранного микрофона."""
                selected = device_combo.current()
                test_device_index = device_indices[selected]
                
                try:
                    test_capture = AudioCapture(
                        sample_rate=self.config.audio_sample_rate,
                        chunk_size=self.config.audio_chunk_size,
                        device_index=test_device_index
                    )
                    test_capture.start()
                    
                    # Читаем несколько чанков
                    chunks_read = 0
                    for _ in range(5):
                        chunk = test_capture.read_chunk(timeout=0.5)
                        if chunk:
                            chunks_read += 1
                    
                    test_capture.stop()
                    
                    if chunks_read > 0:
                        messagebox.showinfo("Тест микрофона", "✓ Микрофон работает!")
                    else:
                        messagebox.showwarning("Тест микрофона", "Микрофон не передаёт данные")
                        
                except Exception as e:
                    messagebox.showerror("Тест микрофона", f"Ошибка: {e}")
            
            tk.Button(mic_frame, text="Тест", command=test_microphone, width=8).grid(row=0, column=2, padx=5, pady=5)
            
            # === Секция: Горячие клавиши ===
            hotkey_frame = ttk.LabelFrame(root, text="⌨️ Горячие клавиши", padding=10)
            hotkey_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

            tk.Label(hotkey_frame, text="Включение/выключение:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            toggle_var = tk.StringVar(value=self.config.hotkey_toggle)
            tk.Entry(hotkey_frame, textvariable=toggle_var, width=20).grid(row=0, column=1, padx=5, pady=5)

            tk.Label(hotkey_frame, text="Пауза:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            pause_var = tk.StringVar(value=self.config.hotkey_pause)
            tk.Entry(hotkey_frame, textvariable=pause_var, width=20).grid(row=1, column=1, padx=5, pady=5)
            
            # === Секция: Ввод ===
            input_frame = ttk.LabelFrame(root, text="📝 Ввод текста", padding=10)
            input_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

            tk.Label(input_frame, text="Способ:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            method_var = tk.StringVar(value=self.config.input_method)
            ttk.Combobox(
                input_frame,
                textvariable=method_var,
                values=("clipboard", "typing"),
                state="readonly",
                width=17
            ).grid(row=0, column=1, padx=5, pady=5)
            
            # === Секция: Уведомления ===
            notif_frame = ttk.LabelFrame(root, text="🔔 Уведомления", padding=10)
            notif_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
            
            notif_var = tk.BooleanVar(value=self.config.notifications_enabled)
            notif_cb = ttk.Checkbutton(
                notif_frame,
                text="Показывать уведомления Windows",
                variable=notif_var
            )
            notif_cb.grid(row=0, column=0, padx=5, pady=2, sticky="w")
            create_tooltip(notif_cb, "Toast-уведомления при включении/выключении")
            
            sound_var = tk.BooleanVar(value=self.config.sound_enabled)
            sound_cb = ttk.Checkbutton(
                notif_frame,
                text="Звуковые сигналы",
                variable=sound_var
            )
            sound_cb.grid(row=1, column=0, padx=5, pady=2, sticky="w")
            create_tooltip(sound_cb, "Бип при включении/выключении распознавания")
            
            # === Секция: Система ===
            system_frame = ttk.LabelFrame(root, text="⚙️ Система", padding=10)
            system_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
            
            autostart_var = tk.BooleanVar(value=is_autostart_enabled())
            ttk.Checkbutton(
                system_frame,
                text="Запускать при старте Windows",
                variable=autostart_var
            ).grid(row=0, column=0, padx=5, pady=5, sticky="w")

            def save_settings():
                new_toggle = toggle_var.get().strip()
                new_pause = pause_var.get().strip()
                new_method = method_var.get().strip()
                selected_device = device_combo.current()
                new_device_index = device_indices[selected_device]
                new_autostart = autostart_var.get()
                new_quality = quality_var.get()
                new_notif = notif_var.get()
                new_sound = sound_var.get()

                if not new_toggle or not new_pause:
                    messagebox.showerror("Ошибка", "Горячие клавиши не должны быть пустыми.")
                    return

                try:
                    # Сохраняем настройки
                    self.config.set("hotkeys.toggle", new_toggle)
                    self.config.set("hotkeys.pause", new_pause)
                    self.config.set("input.method", new_method)
                    self.config.set("audio.device_index", new_device_index)
                    
                    # Применяем предустановку качества
                    if new_quality == "fast":
                        self.config.set("vad.aggressiveness", 3)
                        self.config.set("audio.chunk_size", 8000)
                    elif new_quality == "balanced":
                        self.config.set("vad.aggressiveness", 2)
                        self.config.set("audio.chunk_size", 8000)
                    elif new_quality == "quality":
                        self.config.set("vad.aggressiveness", 1)
                        self.config.set("audio.chunk_size", 4000)
                    
                    self.text_input.input_method = new_method

                    self.hotkey_manager.unregister_all()
                    self._register_hotkeys()
                    
                    # Обновляем VAD с новыми настройками
                    self.vad = VoiceActivityDetector(
                        sample_rate=self.config.audio_sample_rate,
                        aggressiveness=self.config.vad_aggressiveness,
                        enabled=self.config.vad_enabled
                    )
                    
                    # Уведомления
                    self.config.set("notifications.enabled", new_notif)
                    self.config.set("notifications.sound_enabled", new_sound)
                    self.notifications.enabled = new_notif
                    self.audio_feedback.enabled = new_sound
                    
                    # Автозапуск
                    if new_autostart != is_autostart_enabled():
                        if set_autostart(new_autostart):
                            status = "включён" if new_autostart else "отключён"
                            logger.info(f"Автозапуск {status}")
                        else:
                            messagebox.showwarning("Предупреждение", "Не удалось изменить настройку автозапуска")

                    messagebox.showinfo("Готово", "Настройки сохранены.\nИзменения применятся при следующем запуске распознавания.")
                    on_close()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")

            # Кнопка управления моделями
            tk.Button(
                root,
                text="📦 Управление моделями...",
                command=lambda: [on_close(), self.open_model_manager()]
            ).grid(row=6, column=0, columnspan=2, pady=5)
            
            button_frame = tk.Frame(root)
            button_frame.grid(row=7, column=0, columnspan=2, pady=10)

            tk.Button(button_frame, text="Сохранить", command=save_settings, width=12).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Отмена", command=on_close, width=12).pack(side=tk.LEFT, padx=5)

            # Позиционирование окна в правом нижнем углу экрана (ближе к трею)
            root.update_idletasks()
            window_width = root.winfo_width()
            window_height = root.winfo_height()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            x = screen_width - window_width - 50
            y = screen_height - window_height - 100
            
            root.geometry(f"+{x}+{y}")

            root.mainloop()

        threading.Thread(target=_show_settings, daemon=True).start()
    
    def open_model_manager(self):
        """Открытие окна управления моделями."""
        def _show_model_manager():
            try:
                import tkinter as tk
                from tkinter import ttk, messagebox
            except ImportError:
                logger.error("Tkinter недоступен")
                return
            
            root = tk.Tk()
            root.title("Управление моделями")
            root.resizable(False, False)
            
            # Основной фрейм
            main_frame = ttk.Frame(root, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Получаем список моделей
            models = self.model_manager.get_available_models()
            current_model = self.config.vosk_model_path
            
            # Список моделей
            for i, model in enumerate(models):
                model_frame = ttk.LabelFrame(
                    main_frame,
                    text=model['name'],
                    padding=10
                )
                model_frame.pack(fill=tk.X, pady=5)
                
                # Описание
                desc_label = ttk.Label(
                    model_frame,
                    text=model['description'],
                    wraplength=350
                )
                desc_label.grid(row=0, column=0, columnspan=3, sticky="w")
                
                # Размер
                size_text = f"Размер: {model['size_mb']} МБ"
                ttk.Label(model_frame, text=size_text).grid(row=1, column=0, sticky="w", pady=5)
                
                # Статус и кнопки
                button_frame = ttk.Frame(model_frame)
                button_frame.grid(row=1, column=1, columnspan=2, sticky="e")
                
                model_id = model['id']
                model_path = f"models/{model_id}"
                is_active = current_model.endswith(model_id)
                
                if model['is_downloaded']:
                    # Модель скачана
                    if is_active:
                        ttk.Label(button_frame, text="✓ Активна", foreground="green").pack(side=tk.LEFT, padx=5)
                    else:
                        def make_active(mid=model_id, mp=model_path):
                            self.config.set("vosk.model_path", mp)
                            messagebox.showinfo(
                                "Модель выбрана",
                                f"Модель будет использована при следующем запуске распознавания."
                            )
                            root.destroy()
                        
                        ttk.Button(
                            button_frame,
                            text="Сделать активной",
                            command=make_active
                        ).pack(side=tk.LEFT, padx=2)
                    
                    # Кнопка удаления (если не активна)
                    if not is_active:
                        def delete_model(mid=model_id, mname=model['name']):
                            if messagebox.askyesno(
                                "Удалить модель?",
                                f"Удалить модель {mname}?"
                            ):
                                if self.model_manager.delete_model(mid):
                                    messagebox.showinfo("Готово", "Модель удалена")
                                    root.destroy()
                                    self.open_model_manager()  # Перезагрузить окно
                                else:
                                    messagebox.showerror("Ошибка", "Не удалось удалить модель")
                        
                        ttk.Button(
                            button_frame,
                            text="Удалить",
                            command=delete_model
                        ).pack(side=tk.LEFT, padx=2)
                else:
                    # Модель не скачана
                    ttk.Label(button_frame, text="Не скачана", foreground="gray").pack(side=tk.LEFT, padx=5)
                    
                    def download_model(mid=model_id, mname=model['name']):
                        # Открыть окно скачивания
                        root.destroy()
                        self._show_download_dialog(mid, mname)
                    
                    ttk.Button(
                        button_frame,
                        text="Скачать",
                        command=download_model
                    ).pack(side=tk.LEFT, padx=2)
            
            # Кнопка закрытия
            ttk.Button(
                main_frame,
                text="Закрыть",
                command=root.destroy
            ).pack(pady=10)
            
            # Центрирование
            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            x = (root.winfo_screenwidth() - w) // 2
            y = (root.winfo_screenheight() - h) // 2
            root.geometry(f"+{x}+{y}")
            
            root.mainloop()
        
        threading.Thread(target=_show_model_manager, daemon=True).start()
    
    def _show_download_dialog(self, model_id: str, model_name: str):
        """Показать диалог скачивания модели с прогресс-баром."""
        def _download():
            try:
                import tkinter as tk
                from tkinter import ttk, messagebox
            except ImportError:
                return
            
            root = tk.Tk()
            root.title(f"Скачивание: {model_name}")
            root.resizable(False, False)
            root.protocol("WM_DELETE_WINDOW", lambda: None)  # Запретить закрытие
            
            frame = ttk.Frame(root, padding=20)
            frame.pack()
            
            ttk.Label(frame, text=f"Скачивание модели: {model_name}").pack(pady=5)
            
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(
                frame,
                variable=progress_var,
                maximum=100,
                length=300,
                mode='determinate'
            )
            progress_bar.pack(pady=10)
            
            status_var = tk.StringVar(value="Подключение...")
            status_label = ttk.Label(frame, textvariable=status_var)
            status_label.pack(pady=5)
            
            cancel_pressed = [False]
            
            def on_cancel():
                cancel_pressed[0] = True
                self.model_manager.cancel_download()
                status_var.set("Отмена...")
            
            cancel_btn = ttk.Button(frame, text="Отмена", command=on_cancel)
            cancel_btn.pack(pady=10)
            
            def on_progress(progress: float, status: str):
                progress_var.set(progress * 100)
                status_var.set(status)
                root.update_idletasks()
            
            def on_complete(success: bool, message: str):
                root.destroy()
                if success:
                    self.notifications.show("VoiceInput", f"Модель {model_name} скачана!")
                    # Переоткрыть менеджер моделей
                    self.open_model_manager()
                else:
                    if not cancel_pressed[0]:
                        import tkinter as tk
                        from tkinter import messagebox
                        temp_root = tk.Tk()
                        temp_root.withdraw()
                        messagebox.showerror("Ошибка скачивания", message)
                        temp_root.destroy()
            
            # Центрирование
            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            x = (root.winfo_screenwidth() - w) // 2
            y = (root.winfo_screenheight() - h) // 2
            root.geometry(f"+{x}+{y}")
            
            # Запуск скачивания
            self.model_manager.download_model(
                model_id,
                on_progress=on_progress,
                on_complete=on_complete
            )
            
            root.mainloop()
        
        threading.Thread(target=_download, daemon=True).start()


# === Single Instance (Mutex) ===
_mutex_handle = None

def check_single_instance():
    """
    Проверяет, что запущен только один экземпляр приложения.
    Returns: True если это единственный экземпляр, False если уже есть другой.
    """
    global _mutex_handle
    
    MUTEX_NAME = "VoiceInput_SingleInstance_Mutex"
    
    # CreateMutexW
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    
    return True

def release_mutex():
    """Освобождает mutex при завершении."""
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None


def main():
    """Точка входа в приложение."""
    # Проверка single instance
    if not check_single_instance():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                "VoiceInput",
                "Приложение уже запущено.\nПроверьте иконку в системном трее."
            )
            root.destroy()
        except:
            print("VoiceInput уже запущен!")
        return
    
    try:
        app = VoiceInputApp()
        app.run()
    finally:
        release_mutex()

if __name__ == "__main__":
    main()

