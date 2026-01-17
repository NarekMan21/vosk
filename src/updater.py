"""
Модуль проверки обновлений через GitHub Releases.
"""
import logging
import threading
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request, urlretrieve
from urllib.error import URLError
from typing import Optional, Tuple, Callable

logger = logging.getLogger(__name__)

# Настройки GitHub репозитория
GITHUB_REPO = "NarekMan21/vosk"
CURRENT_VERSION = "1.1.0"


def get_releases_url(repo: str) -> str:
    """Получить URL API для releases."""
    return f"https://api.github.com/repos/{repo}/releases/latest"


def parse_version(version: str) -> Tuple[int, ...]:
    """Парсинг версии в кортеж чисел для сравнения."""
    # Убираем 'v' в начале если есть
    version = version.lstrip('vV')
    parts = version.split('.')
    result = []
    for p in parts:
        # Извлекаем только цифры
        digits = ''.join(c for c in p if c.isdigit())
        if digits:
            result.append(int(digits))
    return tuple(result) if result else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    """Проверяет, новее ли latest чем current."""
    try:
        return parse_version(latest) > parse_version(current)
    except Exception:
        return False


class UpdateChecker:
    """Проверка обновлений на GitHub."""
    
    def __init__(self, current_version: str = CURRENT_VERSION, 
                 github_repo: str = GITHUB_REPO):
        """
        Инициализация проверки обновлений.
        
        Args:
            current_version: Текущая версия приложения
            github_repo: Репозиторий GitHub (owner/repo)
        """
        self.current_version = current_version
        self.github_repo = github_repo
        self._check_thread: Optional[threading.Thread] = None
    
    def check_for_updates(
        self,
        on_result: Optional[Callable[[bool, str, str, str, Optional[str]], None]] = None,
        silent: bool = False
    ):
        """
        Проверить наличие обновлений в фоне.
        
        Args:
            on_result: Callback(has_update, version, url, notes, installer_url)
            silent: Если True, не показывать ошибки при неудаче
        """
        def _check():
            try:
                url = get_releases_url(self.github_repo)
                request = Request(
                    url,
                    headers={
                        'User-Agent': 'VoiceInput UpdateChecker',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
                
                with urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get('tag_name', '')
                release_url = data.get('html_url', '')
                release_notes = data.get('body', '')
                
                # Получаем URL установщика
                installer_url = get_installer_download_url(data)
                
                # Ограничиваем длину заметок
                if len(release_notes) > 500:
                    release_notes = release_notes[:500] + "..."
                
                has_update = is_newer_version(latest_version, self.current_version)
                
                logger.info(
                    f"Проверка обновлений: текущая={self.current_version}, "
                    f"последняя={latest_version}, обновление={'да' if has_update else 'нет'}"
                )
                if installer_url:
                    logger.info(f"URL установщика: {installer_url}")
                
                if on_result:
                    on_result(has_update, latest_version, release_url, release_notes, installer_url)
                    
            except URLError as e:
                logger.debug(f"Не удалось проверить обновления (сеть): {e}")
                if on_result and not silent:
                    on_result(False, "", "", "", None)
            except Exception as e:
                logger.debug(f"Ошибка проверки обновлений: {e}")
                if on_result and not silent:
                    on_result(False, "", "", "", None)
        
        self._check_thread = threading.Thread(target=_check, daemon=True)
        self._check_thread.start()
    
    def show_update_dialog(self, version: str, url: str, notes: str, 
                           installer_url: Optional[str] = None):
        """Показать диалог с информацией об обновлении."""
        def _show():
            try:
                import tkinter as tk
                from tkinter import ttk
                import webbrowser
            except ImportError:
                return
            
            root = tk.Tk()
            root.title("Доступно обновление")
            root.resizable(False, False)
            
            # Попробуем применить тёмную тему
            try:
                from themes import apply_theme
                apply_theme(root, dark=True)
            except:
                pass
            
            frame = ttk.Frame(root, padding=20)
            frame.pack()
            
            ttk.Label(
                frame,
                text="🎉 Доступна новая версия!",
                font=("Segoe UI", 12, "bold")
            ).pack(pady=(0, 10))
            
            ttk.Label(
                frame,
                text=f"Текущая версия: {self.current_version}"
            ).pack()
            
            ttk.Label(
                frame,
                text=f"Новая версия: {version}",
                foreground="#4ec9b0"  # Зелёный для тёмной темы
            ).pack(pady=(0, 10))
            
            if notes:
                notes_frame = ttk.LabelFrame(frame, text="Что нового", padding=10)
                notes_frame.pack(fill=tk.X, pady=10)
                
                # Ограничиваем ширину и высоту текста
                display_notes = notes[:300] + ("..." if len(notes) > 300 else "")
                notes_label = ttk.Label(
                    notes_frame,
                    text=display_notes,
                    wraplength=350
                )
                notes_label.pack()
            
            # Прогресс-бар (скрыт по умолчанию)
            progress_frame = ttk.Frame(frame)
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(
                progress_frame, 
                variable=progress_var,
                maximum=100,
                length=350
            )
            progress_label = ttk.Label(progress_frame, text="")
            
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(pady=15)
            
            def auto_update():
                """Автоматическое скачивание и установка."""
                if not installer_url:
                    webbrowser.open(url)
                    root.destroy()
                    return
                
                # Показываем прогресс
                progress_frame.pack(fill=tk.X, pady=10)
                progress_bar.pack(fill=tk.X)
                progress_label.pack()
                
                # Скрываем кнопки
                btn_frame.pack_forget()
                
                def on_progress(downloaded, total):
                    if total > 0:
                        percent = (downloaded / total) * 100
                        progress_var.set(percent)
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        progress_label.config(
                            text=f"Скачано: {mb_downloaded:.1f} / {mb_total:.1f} МБ"
                        )
                        root.update()
                
                def do_download():
                    try:
                        download_and_install_update(installer_url, on_progress)
                    except Exception as e:
                        logger.error(f"Ошибка автообновления: {e}")
                        root.after(0, lambda: progress_label.config(text=f"Ошибка: {e}"))
                
                threading.Thread(target=do_download, daemon=True).start()
            
            def open_download():
                webbrowser.open(url)
                root.destroy()
            
            # Кнопка автообновления (если есть installer_url)
            if installer_url:
                ttk.Button(
                    btn_frame,
                    text="⬇️ Установить сейчас",
                    command=auto_update
                ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                btn_frame,
                text="🌐 Открыть в браузере",
                command=open_download
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                btn_frame,
                text="Позже",
                command=root.destroy
            ).pack(side=tk.LEFT, padx=5)
            
            # Центрирование
            root.update_idletasks()
            w, h = root.winfo_width(), root.winfo_height()
            x = (root.winfo_screenwidth() - w) // 2
            y = (root.winfo_screenheight() - h) // 2
            root.geometry(f"+{x}+{y}")
            
            root.mainloop()
        
        threading.Thread(target=_show, daemon=True).start()


def download_and_install_update(download_url: str, on_progress: Optional[Callable[[int, int], None]] = None):
    """
    Скачать и запустить установщик обновления.
    
    Args:
        download_url: URL для скачивания установщика
        on_progress: Callback(downloaded_bytes, total_bytes)
    
    Returns:
        True если успешно запущена установка
    """
    try:
        # Создаём временную директорию
        temp_dir = Path(tempfile.gettempdir()) / "VoiceInput_Update"
        temp_dir.mkdir(exist_ok=True)
        
        # Имя файла из URL
        filename = download_url.split('/')[-1]
        if not filename.endswith('.exe'):
            filename = "VoiceInput-Setup.exe"
        
        installer_path = temp_dir / filename
        
        logger.info(f"Скачивание обновления: {download_url}")
        logger.info(f"Сохранение в: {installer_path}")
        
        # Скачиваем с прогрессом
        def reporthook(block_num, block_size, total_size):
            if on_progress and total_size > 0:
                downloaded = block_num * block_size
                on_progress(downloaded, total_size)
        
        urlretrieve(download_url, str(installer_path), reporthook)
        
        logger.info("Скачивание завершено, запуск установщика...")
        
        # Запускаем установщик
        # /SILENT для тихой установки, /CLOSEAPPLICATIONS для закрытия приложения
        subprocess.Popen(
            [str(installer_path), '/SILENT', '/CLOSEAPPLICATIONS'],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        logger.info("Установщик запущен, завершаем приложение...")
        
        # Даём время на запуск установщика
        import time
        time.sleep(1)
        
        # Завершаем текущее приложение
        os._exit(0)
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при скачивании/установке обновления: {e}")
        return False


def get_installer_download_url(release_data: dict) -> Optional[str]:
    """
    Получить URL установщика из данных релиза.
    
    Args:
        release_data: Данные релиза от GitHub API
    
    Returns:
        URL установщика или None
    """
    assets = release_data.get('assets', [])
    
    for asset in assets:
        name = asset.get('name', '').lower()
        if 'setup' in name and name.endswith('.exe'):
            return asset.get('browser_download_url')
    
    # Если не нашли Setup, ищем любой exe
    for asset in assets:
        name = asset.get('name', '').lower()
        if name.endswith('.exe'):
            return asset.get('browser_download_url')
    
    return None


def check_updates_on_startup(config, notifications=None, 
                             current_version: str = CURRENT_VERSION,
                             github_repo: str = GITHUB_REPO):
    """
    Проверить обновления при запуске (если включено в настройках).
    
    Args:
        config: Объект конфигурации
        notifications: Объект уведомлений (опционально)
        current_version: Текущая версия
        github_repo: Репозиторий GitHub
    """
    logger.info(f"Запуск проверки обновлений: версия={current_version}, репо={github_repo}")
    
    check_enabled = config.get("check_updates", True)
    logger.info(f"Настройка check_updates: {check_enabled}")
    
    if not check_enabled:
        logger.info("Проверка обновлений отключена в настройках")
        return
    
    checker = UpdateChecker(current_version, github_repo)
    
    def on_result(has_update, version, url, notes, installer_url=None):
        logger.info(f"Результат проверки: has_update={has_update}, version={version}")
        if has_update:
            logger.info(f"Доступно обновление: {version}")
            if notifications:
                notifications.show(
                    "VoiceInput",
                    f"🆕 Доступна версия {version}"
                )
            checker.show_update_dialog(version, url, notes, installer_url)
        else:
            logger.info("Обновлений не найдено или уже установлена последняя версия")
    
    logger.info("Запускаем фоновую проверку обновлений...")
    checker.check_for_updates(on_result=on_result, silent=True)
