"""
Модуль первого запуска — показывает туториал новым пользователям.
Современный Welcome Screen на CustomTkinter.
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
            import customtkinter as ctk
        except ImportError:
            # Fallback на обычный Tkinter
            _show_fallback()
            return
        
        # =================================================================
        # 🎨 НАСТРОЙКА
        # =================================================================
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        COLORS = {
            'bg': '#0D0D0D',
            'card': '#1C1C1E',
            'border': '#38383A',
            'accent': '#0A84FF',
            'accent_hover': '#0066CC',
            'success': '#30D158',
            'fg': '#FFFFFF',
            'fg_secondary': '#8E8E93',
        }
        
        root = ctk.CTk()
        root.title("Добро пожаловать!")
        root.resizable(False, False)
        root.configure(fg_color=COLORS['bg'])
        
        def on_close():
            if dont_show_var.get():
                mark_tutorial_shown(config)
            root.destroy()
            if on_complete:
                on_complete()
        
        root.protocol("WM_DELETE_WINDOW", on_close)
        
        # =================================================================
        # 📦 ФУНКЦИЯ СОЗДАНИЯ КАРТОЧКИ
        # =================================================================
        def create_card(parent, icon, title, items):
            """Создать карточку с иконкой и списком."""
            card = ctk.CTkFrame(
                parent,
                corner_radius=16,
                fg_color=COLORS['card'],
                border_width=1,
                border_color=COLORS['border']
            )
            card.pack(fill="x", pady=8, padx=4)
            
            # Заголовок с иконкой
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=(16, 8))
            
            ctk.CTkLabel(
                header,
                text=f"{icon} {title}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=COLORS['fg']
            ).pack(anchor="w")
            
            # Элементы списка
            for item in items:
                ctk.CTkLabel(
                    card,
                    text=item,
                    font=ctk.CTkFont(size=13),
                    text_color=COLORS['fg_secondary'],
                    anchor="w",
                    justify="left"
                ).pack(fill="x", padx=24, pady=2)
            
            # Нижний отступ
            ctk.CTkFrame(card, fg_color="transparent", height=12).pack()
            
            return card
        
        # =================================================================
        # 🎤 ЗАГОЛОВОК
        # =================================================================
        header_frame = ctk.CTkFrame(root, fg_color="transparent")
        header_frame.pack(fill="x", padx=32, pady=(32, 16))
        
        # Большая иконка
        ctk.CTkLabel(
            header_frame,
            text="🎤",
            font=ctk.CTkFont(size=48)
        ).pack()
        
        # Название
        ctk.CTkLabel(
            header_frame,
            text="VoiceInput",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS['fg']
        ).pack(pady=(8, 0))
        
        # Подзаголовок
        ctk.CTkLabel(
            header_frame,
            text="Голосовой ввод текста для Windows",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['fg_secondary']
        ).pack(pady=(4, 0))
        
        # =================================================================
        # 📋 КОНТЕНТ
        # =================================================================
        content = ctk.CTkFrame(root, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28)
        
        # Карточка: Как пользоваться
        create_card(
            content,
            "🚀",
            "Как пользоваться",
            [
                "1️⃣  Нажмите Win+H для включения/выключения",
                "2️⃣  Говорите — текст появится в активном окне",
                "3️⃣  Голосовые команды: «точка», «запятая», «новая строка»",
                "4️⃣  Иконка в трее: 🟢 Активен  ⚪ Готов  🔴 Ошибка",
            ]
        )
        
        # Карточка: Советы
        create_card(
            content,
            "💡",
            "Советы",
            [
                "• Говорите чётко и не слишком быстро",
                "• Откройте Настройки для выбора микрофона",
                "• Скачайте большую модель для лучшего качества",
                "• Режим зажатия: держите клавишу пока говорите",
            ]
        )
        
        # =================================================================
        # ✅ ЧЕКБОКС И КНОПКА
        # =================================================================
        footer = ctk.CTkFrame(root, fg_color="transparent")
        footer.pack(fill="x", padx=32, pady=(16, 32))
        
        dont_show_var = ctk.BooleanVar(value=True)
        checkbox = ctk.CTkCheckBox(
            footer,
            text="Больше не показывать",
            variable=dont_show_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS['fg_secondary'],
            fg_color=COLORS['accent'],
            hover_color=COLORS['accent_hover']
        )
        checkbox.pack(pady=(0, 16))
        
        # Большая кнопка "Начать"
        start_btn = ctk.CTkButton(
            footer,
            text="🚀 Начать работу",
            command=on_close,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS['accent'],
            hover_color=COLORS['accent_hover']
        )
        start_btn.pack(fill="x")
        
        # =================================================================
        # 📍 ПОЗИЦИОНИРОВАНИЕ И АНИМАЦИЯ
        # =================================================================
        root.update_idletasks()
        w, h = root.winfo_width(), root.winfo_height()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 2
        root.geometry(f"+{x}+{y}")
        
        # Поверх других окон
        root.attributes('-topmost', True)
        
        # Fade-in анимация
        root.attributes('-alpha', 0)
        
        def fade_in():
            alpha = 0.0
            def animate():
                nonlocal alpha
                alpha += 0.08
                if alpha >= 1.0:
                    root.attributes('-alpha', 1.0)
                    return
                root.attributes('-alpha', alpha)
                root.after(15, animate)
            animate()
        
        fade_in()
        
        root.mainloop()
    
    def _show_fallback():
        """Fallback на обычный Tkinter если CustomTkinter недоступен."""
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
        
        main = ttk.Frame(root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="🎤 VoiceInput", font=("Segoe UI", 18, "bold")).pack(pady=(0, 5))
        ttk.Label(main, text="Голосовой ввод текста для Windows", font=("Segoe UI", 10)).pack(pady=(0, 15))
        
        instructions_frame = ttk.LabelFrame(main, text="Как пользоваться", padding=10)
        instructions_frame.pack(fill=tk.X, pady=5)
        
        for step in [
            "1️⃣  Нажмите Win+H для включения/выключения",
            "2️⃣  Говорите — текст появится в активном окне",
            "3️⃣  Голосовые команды: «точка», «запятая»",
        ]:
            ttk.Label(instructions_frame, text=step, anchor="w").pack(fill=tk.X, pady=1)
        
        dont_show_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Больше не показывать", variable=dont_show_var).pack(pady=10)
        
        def on_close():
            if dont_show_var.get():
                mark_tutorial_shown(config)
            root.destroy()
            if on_complete:
                on_complete()
        
        ttk.Button(main, text="Начать работу", command=on_close).pack(pady=10)
        root.protocol("WM_DELETE_WINDOW", on_close)
        
        root.update_idletasks()
        w, h = root.winfo_width(), root.winfo_height()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 2
        root.geometry(f"+{x}+{y}")
        root.attributes('-topmost', True)
        
        root.mainloop()
    
    threading.Thread(target=_show, daemon=True).start()
