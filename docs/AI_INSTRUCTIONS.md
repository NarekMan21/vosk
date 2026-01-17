# 🤖 AI Agent Instructions — VoiceInput Improvements

## META

```yaml
project: VoiceInput
language: Python 3.10+
platform: Windows
base_path: d:\cursor\audio
src_path: d:\cursor\audio\src
config_path: d:\cursor\audio\config.json
```

## HOW TO USE THIS DOCUMENT

1. Read the `CURRENT_TASK` section
2. Follow `IMPLEMENTATION_STEPS` exactly
3. After each step, run `VERIFICATION` commands
4. Mark checkboxes in `CHECKLIST`
5. When all checkboxes ✅, update `CURRENT_TASK` to next improvement

---

## CURRENT_TASK

```yaml
wave: 10
improvement: 27
name: "Инсталлятор Inno Setup"
status: COMPLETED
last_completed: "2026-01-17"
version: "1.0.1"
```

## COMPLETED IN v1.0.1

```yaml
improvements:
  - id: 23
    name: "Туториал первого запуска"
    file: "src/first_run.py"
    status: COMPLETED
    
  - id: 24
    name: "Автопроверка обновлений"
    file: "src/updater.py"
    status: COMPLETED
    
  - id: 25
    name: "Режим зажатия горячих клавиш"
    files: ["src/hotkey_manager.py", "src/main.py"]
    status: COMPLETED
    
  - id: 26
    name: "Исправление бага настроек"
    file: "src/main.py"
    status: COMPLETED
    
  - id: 27
    name: "Инсталлятор Inno Setup"
    files: ["installer.iss", "build_installer.bat"]
    status: COMPLETED
```

## NEXT_TASK (optional)

```yaml
wave: 1
improvement: 1
name: "Ротация логов"
status: NOT_STARTED
```

---

# WAVE 1: FOUNDATION

## IMPROVEMENT #1: Log Rotation

### CONTEXT

```yaml
problem: "Log file grows indefinitely, can fill disk"
current_file: src/main.py
current_lines: 50-59
current_code: |
  log_file = BASE_PATH / 'voice_input.log'
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
      handlers=[
          logging.FileHandler(str(log_file), encoding='utf-8'),
          logging.StreamHandler()
      ]
  )
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: ADD_IMPORT
  file: src/main.py
  after_line: 5  # after "import logging"
  code: |
    from logging.handlers import RotatingFileHandler

step_2:
  action: REPLACE_CODE
  file: src/main.py
  old_code: |
    log_file = BASE_PATH / 'voice_input.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
  new_code: |
    log_file = BASE_PATH / 'voice_input.log'
    
    # Настройка ротации логов: макс 5 МБ, 3 backup файла
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
```

### VERIFICATION

```bash
# 1. Check syntax
python -m py_compile src/main.py

# 2. Run app briefly
python src/main.py
# Wait 5 seconds, then Ctrl+C

# 3. Check log file exists
dir voice_input.log

# 4. Verify RotatingFileHandler in code
findstr "RotatingFileHandler" src\main.py
```

### CHECKLIST

```yaml
- [ ] RotatingFileHandler imported
- [ ] maxBytes set to 5*1024*1024
- [ ] backupCount set to 3
- [ ] App starts without errors
- [ ] Log file is created
- [ ] No syntax errors
```

### ON_SUCCESS

```yaml
next_improvement: 2
update_status: COMPLETED
```

---

## IMPROVEMENT #2: Single Instance (Mutex)

### CONTEXT

```yaml
problem: "Multiple instances conflict for microphone and hotkeys"
current_file: src/main.py
insert_location: "Before main() function"
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: ADD_IMPORT
  file: src/main.py
  after_line: 8  # in imports section
  code: |
    import ctypes
    from ctypes import wintypes

step_2:
  action: ADD_FUNCTION
  file: src/main.py
  before: "def main():"
  code: |
    # === Single Instance ===
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

step_3:
  action: MODIFY_FUNCTION
  file: src/main.py
  function: main
  add_at_start: |
    # Проверка single instance
    if not check_single_instance():
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "VoiceInput",
            "Приложение уже запущено.\nПроверьте иконку в системном трее."
        )
        root.destroy()
        return
```

### VERIFICATION

```bash
# 1. Syntax check
python -m py_compile src/main.py

# 2. Run first instance (in background)
start python src/main.py

# 3. Try to run second instance
python src/main.py
# Should show warning dialog

# 4. Close both instances
```

### CHECKLIST

```yaml
- [ ] check_single_instance() function added
- [ ] release_mutex() function added
- [ ] main() checks single instance at start
- [ ] Warning dialog appears on second launch
- [ ] First instance continues working
- [ ] No errors in console
```

---

## IMPROVEMENT #5: Graceful Shutdown

### CONTEXT

```yaml
problem: "Resources not properly released on exit"
current_file: src/main.py
modify_class: VoiceInputApp
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: ADD_IMPORT
  file: src/main.py
  in_imports: true
  code: |
    import signal
    import atexit

step_2:
  action: MODIFY_METHOD
  file: src/main.py
  class: VoiceInputApp
  method: __init__
  add_at_end: |
        # Регистрация cleanup
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

step_3:
  action: ADD_METHOD
  file: src/main.py
  class: VoiceInputApp
  after_method: shutdown
  code: |
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown."""
        logger.info(f"Получен сигнал {signum}, завершение...")
        self.shutdown()
    
    def _cleanup(self):
        """Финальная очистка ресурсов."""
        logger.info("Очистка ресурсов...")
        
        # Остановка распознавания
        if self.is_active:
            self.stop()
        
        # Освобождение mutex
        release_mutex()
        
        # Закрытие аудио
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except:
                pass
        
        # Остановка трея
        if self.system_tray:
            try:
                self.system_tray.stop()
            except:
                pass
        
        logger.info("Ресурсы освобождены")
```

### VERIFICATION

```bash
# 1. Run app
python src/main.py

# 2. Press Ctrl+C
# Should see "Получен сигнал" and "Ресурсы освобождены" in log

# 3. Run app again
python src/main.py

# 4. Exit via tray menu
# Should exit cleanly

# 5. Check no zombie processes
tasklist | findstr python
```

### CHECKLIST

```yaml
- [ ] signal handlers registered
- [ ] atexit handler registered
- [ ] _signal_handler method added
- [ ] _cleanup method added
- [ ] Ctrl+C exits cleanly
- [ ] Tray exit works
- [ ] Log shows cleanup messages
- [ ] No zombie processes
```

---

# WAVE 2: ERROR HANDLING

## IMPROVEMENT #14: Config Validation

### CONTEXT

```yaml
problem: "Corrupted config.json crashes app"
current_file: src/config.py
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: MODIFY_METHOD
  file: src/config.py
  class: Config
  method: load
  replace_with: |
    def load(self):
        """Загрузка конфигурации с валидацией."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning("Config file is empty, using defaults")
                        self._config = self._get_defaults()
                    else:
                        loaded = json.loads(content)
                        self._config = self._merge_with_defaults(loaded)
                        logger.info("Config loaded successfully")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config: {e}")
                logger.info("Using default configuration")
                self._config = self._get_defaults()
                # Backup broken config
                backup_path = self.config_path.with_suffix('.json.broken')
                try:
                    shutil.copy(self.config_path, backup_path)
                    logger.info(f"Broken config backed up to {backup_path}")
                except:
                    pass
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self._config = self._get_defaults()
        else:
            logger.info("Config file not found, creating with defaults")
            self._config = self._get_defaults()
            self.save()
    
    def _merge_with_defaults(self, loaded: dict) -> dict:
        """Merge loaded config with defaults, filling missing values."""
        defaults = self._get_defaults()
        return self._deep_merge(defaults, loaded)
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dicts, override takes precedence."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

step_2:
  action: ADD_IMPORT
  file: src/config.py
  code: |
    import shutil
```

### VERIFICATION

```bash
# 1. Test with valid config
python src/main.py
# Should start normally

# 2. Test with broken config
echo "invalid json {{{" > config.json.test
copy config.json config.json.backup
copy config.json.test config.json
python src/main.py
# Should start with defaults, create .broken backup

# 3. Restore valid config
copy config.json.backup config.json
```

### CHECKLIST

```yaml
- [ ] Broken JSON handled gracefully
- [ ] Empty file handled
- [ ] Missing file creates defaults
- [ ] Broken config backed up
- [ ] Missing keys filled from defaults
- [ ] App starts in all cases
```

---

## IMPROVEMENT #15: Atomic Config Save

### CONTEXT

```yaml
problem: "Crash during save corrupts config"
current_file: src/config.py
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: ADD_IMPORT
  file: src/config.py
  code: |
    import tempfile

step_2:
  action: MODIFY_METHOD
  file: src/config.py
  class: Config
  method: save
  replace_with: |
    def save(self):
        """Атомарное сохранение конфигурации."""
        try:
            # Записываем во временный файл
            dir_path = self.config_path.parent
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                dir=str(dir_path),
                delete=False,
                encoding='utf-8'
            ) as tmp:
                json.dump(self._config, tmp, ensure_ascii=False, indent=4)
                tmp_path = Path(tmp.name)
            
            # Атомарный rename (на Windows нужен replace)
            tmp_path.replace(self.config_path)
            logger.info("Config saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            # Удаляем временный файл если остался
            if 'tmp_path' in locals() and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except:
                    pass
            raise
```

### VERIFICATION

```bash
# 1. Modify config via app settings
# 2. Check config.json is valid
python -c "import json; json.load(open('config.json'))"

# 3. No .tmp files in directory
dir *.tmp
```

### CHECKLIST

```yaml
- [ ] Uses tempfile
- [ ] Atomic replace
- [ ] Cleans up temp on error
- [ ] Config stays valid
```

---

## IMPROVEMENT #3: Microphone Error Handling

### CONTEXT

```yaml
problem: "App crashes when microphone disconnected"
current_file: src/audio_capture.py
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: MODIFY_CLASS
  file: src/audio_capture.py
  class: AudioCapture
  modify_init: |
    def __init__(self, sample_rate=16000, chunk_size=4000, channels=1, 
                 device_index=None, on_error=None):
        """
        Args:
            on_error: Callback function(error_message: str) called on errors
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index
        self.on_error = on_error  # NEW
        self.audio = None
        self.stream = None
        self.is_recording = False
        self.audio_queue = Queue()
        self.thread = None
        self._error_count = 0  # NEW
        self._max_errors = 5   # NEW

step_2:
  action: MODIFY_METHOD
  file: src/audio_capture.py
  class: AudioCapture
  method: _audio_callback
  replace_with: |
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback с обработкой ошибок."""
        if status:
            self._error_count += 1
            logger.warning(f"Audio stream status: {status} (error #{self._error_count})")
            
            if self._error_count >= self._max_errors:
                logger.error("Too many audio errors, stopping")
                if self.on_error:
                    self.on_error("Слишком много ошибок аудио. Проверьте микрофон.")
                return (None, pyaudio.paAbort)
        else:
            self._error_count = 0  # Reset on success
        
        if self.is_recording and in_data:
            self.audio_queue.put(in_data)
        
        return (None, pyaudio.paContinue)

step_3:
  action: MODIFY_METHOD
  file: src/audio_capture.py
  class: AudioCapture
  method: start
  wrap_in_try: true
  add_error_handling: |
    except OSError as e:
        error_msg = f"Ошибка микрофона: {e}"
        logger.error(error_msg)
        if self.on_error:
            self.on_error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Неожиданная ошибка аудио: {e}"
        logger.error(error_msg)
        if self.on_error:
            self.on_error(error_msg)
        raise
```

### VERIFICATION

```bash
# 1. Run app
python src/main.py

# 2. Start recognition
# 3. Disconnect microphone (physically or in Windows settings)
# 4. App should NOT crash, should show error

# 5. Reconnect microphone
# 6. Restart recognition
```

### CHECKLIST

```yaml
- [ ] on_error callback added
- [ ] Error counter implemented
- [ ] Callback handles status errors
- [ ] start() catches exceptions
- [ ] App doesn't crash on disconnect
```

---

## IMPROVEMENT #4: Microphone Reconnect

### CONTEXT

```yaml
problem: "Manual restart required after microphone error"
current_file: src/audio_capture.py
depends_on: [3]
```

### IMPLEMENTATION_STEPS

```yaml
step_1:
  action: ADD_METHOD
  file: src/audio_capture.py
  class: AudioCapture
  code: |
    def reconnect(self, max_attempts=5, initial_delay=1.0):
        """
        Попытка переподключения к микрофону.
        
        Args:
            max_attempts: Максимум попыток
            initial_delay: Начальная задержка между попытками (секунды)
        
        Returns:
            True если успешно, False если все попытки исчерпаны
        """
        import time
        
        delay = initial_delay
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Попытка переподключения {attempt}/{max_attempts}...")
            
            # Очистка предыдущего состояния
            self.stop()
            time.sleep(delay)
            
            try:
                self.start()
                logger.info("Переподключение успешно!")
                return True
            except Exception as e:
                logger.warning(f"Попытка {attempt} не удалась: {e}")
                delay = min(delay * 2, 10.0)  # Exponential backoff, max 10s
        
        logger.error("Все попытки переподключения исчерпаны")
        return False
    
    def is_device_available(self) -> bool:
        """Проверяет доступность аудиоустройства."""
        try:
            test_audio = pyaudio.PyAudio()
            try:
                if self.device_index is not None:
                    test_audio.get_device_info_by_index(self.device_index)
                else:
                    test_audio.get_default_input_device_info()
                return True
            finally:
                test_audio.terminate()
        except:
            return False
```

### VERIFICATION

```bash
# 1. Start app and recognition
# 2. Disconnect microphone
# 3. Wait for error
# 4. Reconnect microphone
# 5. App should auto-reconnect or show reconnect status
```

### CHECKLIST

```yaml
- [ ] reconnect() method added
- [ ] Exponential backoff implemented
- [ ] is_device_available() works
- [ ] Reconnection attempts logged
```

---

# NEW FILE TEMPLATES

## Template: src/audio_feedback.py (for #6)

```python
"""
Модуль звуковой обратной связи.
"""
import winsound
import threading
import logging

logger = logging.getLogger(__name__)


class AudioFeedback:
    """Звуковые уведомления для пользователя."""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
    
    def play_start(self):
        """Звук включения распознавания."""
        if self.enabled:
            self._play_async(frequency=1000, duration=100)
    
    def play_stop(self):
        """Звук выключения распознавания."""
        if self.enabled:
            self._play_async(frequency=500, duration=100)
    
    def play_error(self):
        """Звук ошибки."""
        if self.enabled:
            self._play_async(frequency=300, duration=200)
    
    def _play_async(self, frequency, duration):
        """Воспроизведение в фоновом потоке."""
        def _play():
            try:
                winsound.Beep(frequency, duration)
            except Exception as e:
                logger.debug(f"Sound error: {e}")
        
        threading.Thread(target=_play, daemon=True).start()
```

---

## Template: src/notifications.py (for #9)

```python
"""
Модуль Windows Toast уведомлений.
"""
import logging
import threading

logger = logging.getLogger(__name__)

# Lazy import для необязательной зависимости
_toast_available = None


def _check_toast():
    global _toast_available
    if _toast_available is None:
        try:
            from win11toast import toast
            _toast_available = True
        except ImportError:
            logger.warning("win11toast not installed, notifications disabled")
            _toast_available = False
    return _toast_available


class Notifications:
    """Windows Toast уведомления."""
    
    APP_ID = "VoiceInput"
    
    def __init__(self, enabled=True):
        self.enabled = enabled and _check_toast()
    
    def show(self, title: str, message: str):
        """Показать уведомление."""
        if not self.enabled:
            return
        
        def _show():
            try:
                from win11toast import toast
                toast(title, message, app_id=self.APP_ID)
            except Exception as e:
                logger.debug(f"Toast error: {e}")
        
        threading.Thread(target=_show, daemon=True).start()
    
    def show_start(self):
        self.show("VoiceInput", "Распознавание включено")
    
    def show_stop(self):
        self.show("VoiceInput", "Распознавание выключено")
    
    def show_error(self, error: str):
        self.show("VoiceInput — Ошибка", error)
    
    def show_ready(self):
        self.show("VoiceInput", "Готово к работе")
```

---

## Template: src/vad.py (for #11)

```python
"""
Voice Activity Detection — фильтр тишины.
"""
import logging
import collections

logger = logging.getLogger(__name__)

# Lazy import
_webrtcvad = None


def _get_vad():
    global _webrtcvad
    if _webrtcvad is None:
        try:
            import webrtcvad
            _webrtcvad = webrtcvad
        except ImportError:
            logger.warning("webrtcvad not installed, VAD disabled")
    return _webrtcvad


class VoiceActivityDetector:
    """Детектор голосовой активности."""
    
    def __init__(self, sample_rate=16000, aggressiveness=2, enabled=True):
        """
        Args:
            sample_rate: 8000, 16000, 32000, or 48000
            aggressiveness: 0-3 (3 = most aggressive filtering)
            enabled: Enable/disable VAD
        """
        self.sample_rate = sample_rate
        self.enabled = enabled
        self.aggressiveness = aggressiveness
        
        webrtcvad = _get_vad()
        if webrtcvad and enabled:
            self.vad = webrtcvad.Vad(aggressiveness)
        else:
            self.vad = None
            self.enabled = False
        
        # Для сглаживания решений
        self._ring_buffer = collections.deque(maxlen=10)
        self._triggered = False
        
        # Размер фрейма: 10, 20, или 30 мс
        self._frame_duration_ms = 30
        self._frame_size = int(sample_rate * self._frame_duration_ms / 1000) * 2
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Проверяет, содержит ли аудио речь.
        
        Returns:
            True если обнаружена речь, False если тишина
        """
        if not self.enabled or not self.vad:
            return True  # VAD отключён — пропускаем всё
        
        # Анализируем фреймы
        speech_frames = 0
        total_frames = 0
        offset = 0
        
        while offset + self._frame_size <= len(audio_chunk):
            frame = audio_chunk[offset:offset + self._frame_size]
            try:
                if self.vad.is_speech(frame, self.sample_rate):
                    speech_frames += 1
            except:
                pass
            total_frames += 1
            offset += self._frame_size
        
        if total_frames == 0:
            return True
        
        # Решение с гистерезисом
        is_speech = speech_frames / total_frames > 0.3
        self._ring_buffer.append(is_speech)
        
        if not self._triggered:
            # Включаемся если 70% буфера — речь
            if sum(self._ring_buffer) > 0.7 * len(self._ring_buffer):
                self._triggered = True
        else:
            # Выключаемся если 90% — тишина
            if sum(self._ring_buffer) < 0.1 * len(self._ring_buffer):
                self._triggered = False
        
        return self._triggered
    
    def reset(self):
        """Сброс состояния."""
        self._ring_buffer.clear()
        self._triggered = False
```

---

# QUICK COMMANDS

```bash
# Check syntax of all files
python -m py_compile src/main.py src/config.py src/audio_capture.py

# Run application
python src/main.py

# Build exe
.\build.bat

# Test exe
.\dist\VoiceInput.exe

# Check for running processes
tasklist | findstr -i "python voiceinput"

# Kill all Python processes (if stuck)
taskkill /f /im python.exe
```

---

# RULES FOR AI AGENT

1. **ONE improvement at a time** — complete fully before next
2. **Run VERIFICATION after each step** — don't skip
3. **Check ALL checklist items** — all must be ✅
4. **Test manually** — run the app, try the feature
5. **Commit after each improvement** — `git commit -m "Implement #N: Name"`
6. **If error occurs** — fix before continuing, don't proceed with broken code
7. **Update CURRENT_TASK** — after completing each improvement

---

# ERROR RECOVERY

```yaml
if_syntax_error:
  - Run: python -m py_compile <file>
  - Read error message
  - Fix the specific line
  - Verify again

if_runtime_error:
  - Check the log file: voice_input.log
  - Read traceback
  - Fix the issue
  - Test again

if_stuck:
  - Revert to last working state: git checkout -- <file>
  - Start the improvement again
  - Follow steps more carefully
```
