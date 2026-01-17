"""
Модуль первого запуска — показывает туториал новым пользователям.
"""
import logging
import threading

logger = logging.getLogger(__name__)


def should_show_tutorial(config) -> bool:
    """Проверяет, нужно ли показать туториал."""
    return not config.get("tutorial_shown", False)


def mark_tutorial_shown(config):
    """Отмечает, что туториал был показан."""
    config.set("tutorial_shown", True)


def show_tutorial(config, on_complete=None):
    """
    Показать окно туториала.
    
    Args:
        config: Объект конфигурации
        on_complete: Callback после закрытия туториала
    """
    
    def _show():
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            logger.error("Tkinter недоступен для туториала")
            if on_complete:
                on_complete()
            return
        
        root = tk.Tk()
        root.title("Добро пожаловать в VoiceInput!")
        root.resizable(False, False)
        
        # Основной фрейм
        main = ttk.Frame(root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(
            main,
            text="🎤 VoiceInput",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(0, 5))
        
        ttk.Label(
            main,
            text="Голосовой ввод текста для Windows",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 15))
        
        # Инструкции
        instructions_frame = ttk.LabelFrame(main, text="Как пользоваться", padding=10)
        instructions_frame.pack(fill=tk.X, pady=5)
        
        steps = [
            "1️⃣  Нажмите Win+H для включения/выключения",
            "2️⃣  Говорите — текст появится в активном окне",
            "3️⃣  Голосовые команды: «точка», «запятая», «новая строка»",
            "4️⃣  Иконка в трее показывает статус:",
            "      🟢 Активен   ⚪ Готов   🔴 Ошибка",
        ]
        
        for step in steps:
            ttk.Label(
                instructions_frame,
                text=step,
                anchor="w"
            ).pack(fill=tk.X, pady=1)
        
        # Советы
        tips_frame = ttk.LabelFrame(main, text="💡 Советы", padding=10)
        tips_frame.pack(fill=tk.X, pady=10)
        
        tips = [
            "• Говорите чётко и не слишком быстро",
            "• Откройте Настройки для выбора микрофона",
            "• Скачайте большую модель для лучшего качества",
            "• Режим зажатия: держите клавишу пока говорите"
        ]
        
        for tip in tips:
            ttk.Label(tips_frame, text=tip, anchor="w").pack(fill=tk.X)
        
        # Чекбокс "больше не показывать"
        dont_show_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main,
            text="Больше не показывать",
            variable=dont_show_var
        ).pack(pady=10)
        
        def on_close():
            if dont_show_var.get():
                mark_tutorial_shown(config)
            root.destroy()
            if on_complete:
                on_complete()
        
        ttk.Button(
            main,
            text="Начать работу",
            command=on_close
        ).pack(pady=10)
        
        root.protocol("WM_DELETE_WINDOW", on_close)
        
        # Центрирование окна
        root.update_idletasks()
        w, h = root.winfo_width(), root.winfo_height()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 2
        root.geometry(f"+{x}+{y}")
        
        # Поверх других окон
        root.attributes('-topmost', True)
        
        root.mainloop()
    
    threading.Thread(target=_show, daemon=True).start()
