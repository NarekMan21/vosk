# Инструкция по установке

## Быстрая установка

### Шаг 1: Установка Python

Убедитесь, что у вас установлен Python 3.8 или выше:
```bash
python --version
```

Если Python не установлен, скачайте его с [python.org](https://www.python.org/downloads/).

### Шаг 2: Установка зависимостей

```bash
pip install -r requirements.txt
```

**Важно:** Если возникают проблемы с установкой PyAudio:

1. Установите Microsoft Visual C++ Build Tools
2. Или используйте:
   ```bash
   pip install pipwin
   pipwin install pyaudio
   ```

### Шаг 3: Установка модели Vosk

1. Скачайте модель для русского языка:
   - Маленькая модель (рекомендуется для начала): [vosk-model-small-ru-0.22](https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip)
   - Большая модель (лучшая точность): [vosk-model-ru-0.22](https://alphacephei.com/vosk/models/vosk-model-ru-0.22.zip)

2. Распакуйте архив в папку `models/`:
   ```
   models/
   └── vosk-model-small-ru-0.22/
       ├── am/
       ├── graph/
       └── ...
   ```

3. Проверьте путь в `config.json`:
   ```json
   "vosk": {
     "model_path": "models/vosk-model-small-ru-0.22"
   }
   ```

### Шаг 4: Запуск

```bash
python src/main.py
```

## Сборка исполняемого файла

Для создания standalone .exe файла:

1. Установите PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Запустите сборку:
   ```bash
   pyinstaller build_exe.spec
   ```

3. Исполняемый файл будет в папке `dist/VoiceInput.exe`

## Автозапуск с Windows

Чтобы приложение запускалось автоматически при входе в Windows:

1. Создайте ярлык для `VoiceInput.exe` или `src/main.py`
2. Нажмите `Win+R`, введите `shell:startup`
3. Скопируйте ярлык в открывшуюся папку

Или используйте планировщик заданий Windows для более гибкой настройки.

## Обновление

Для обновления приложения:

1. Обновите код из репозитория
2. Переустановите зависимости:
   ```bash
   pip install -r requirements.txt --upgrade
   ```
3. При необходимости обновите модель Vosk

