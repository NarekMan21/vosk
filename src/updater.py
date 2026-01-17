"""
Модуль проверки обновлений через GitHub Releases.
"""
import logging
import threading
import json
from urllib.request import urlopen, Request
from urllib.error import URLError
from typing import Optional, Tuple, Callable

logger = logging.getLogger(__name__)

# Настройки GitHub репозитория
GITHUB_REPO = "NarekMan21/vosk"
CURRENT_VERSION = "1.0.1"


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
        on_result: Optional[Callable[[bool, str, str, str], None]] = None,
        silent: bool = False
    ):
        """
        Проверить наличие обновлений в фоне.
        
        Args:
            on_result: Callback(has_update, version, url, notes)
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
                
                # Ограничиваем длину заметок
                if len(release_notes) > 500:
                    release_notes = release_notes[:500] + "..."
                
                has_update = is_newer_version(latest_version, self.current_version)
                
                logger.info(
                    f"Проверка обновлений: текущая={self.current_version}, "
                    f"последняя={latest_version}, обновление={'да' if has_update else 'нет'}"
                )
                
                if on_result:
                    on_result(has_update, latest_version, release_url, release_notes)
                    
            except URLError as e:
                logger.debug(f"Не удалось проверить обновления (сеть): {e}")
                if on_result and not silent:
                    on_result(False, "", "", "")
            except Exception as e:
                logger.debug(f"Ошибка проверки обновлений: {e}")
                if on_result and not silent:
                    on_result(False, "", "", "")
        
        self._check_thread = threading.Thread(target=_check, daemon=True)
        self._check_thread.start()
    
    def show_update_dialog(self, version: str, url: str, notes: str):
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
                foreground="green"
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
            
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(pady=15)
            
            def open_download():
                webbrowser.open(url)
                root.destroy()
            
            ttk.Button(
                btn_frame,
                text="Скачать",
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
    if not config.get("check_updates", True):
        logger.info("Проверка обновлений отключена в настройках")
        return
    
    checker = UpdateChecker(current_version, github_repo)
    
    def on_result(has_update, version, url, notes):
        if has_update:
            logger.info(f"Доступно обновление: {version}")
            if notifications:
                notifications.show(
                    "VoiceInput",
                    f"🆕 Доступна версия {version}"
                )
            checker.show_update_dialog(version, url, notes)
    
    checker.check_for_updates(on_result=on_result, silent=True)
