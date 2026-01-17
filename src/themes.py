"""
Модуль управления темами UI.

Современная цветовая палитра в стиле Apple/Discord.
"""
import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# 🎨 СОВРЕМЕННАЯ ТЁМНАЯ ТЕМА (Apple-style)
# =============================================================================
# Многослойные оттенки для глубины, один акцентный цвет
# =============================================================================

DARK_THEME = {
    # Фоны — слоистость для визуальной глубины
    'bg': '#161618',              # Основной фон окна (не чёрный!)
    'bg_secondary': '#1C1C1E',    # Карточки, приподнятые панели
    'bg_hover': '#2C2C2E',        # При наведении
    
    # Текст
    'fg': '#FFFFFF',              # Основной текст
    'fg_secondary': '#8E8E93',    # Второстепенный текст
    'label_fg': '#EBEBF5',        # Надписи (чуть мягче белого)
    
    # Интерактивные элементы
    'select_bg': '#3A3A3C',       # Выделение
    'select_fg': '#FFFFFF',
    'button_bg': '#2C2C2E',       # Кнопки
    'button_fg': '#FFFFFF',
    'button_hover': '#3A3A3C',    # Кнопка при наведении
    
    # Поля ввода
    'entry_bg': '#1C1C1E',        # Фон полей
    'entry_fg': '#FFFFFF',
    'entry_border': '#3A3A3C',    # Граница полей
    
    # Рамки
    'frame_bg': '#1C1C1E',        # Фон секций
    'border': '#38383A',          # Границы
    
    # Акцент (Apple Blue)
    'accent': '#0A84FF',          # Главный акцентный цвет
    'accent_hover': '#0066CC',    # Акцент при наведении
    
    # Состояния
    'success': '#30D158',         # Зелёный (Apple Green)
    'warning': '#FFD60A',         # Жёлтый (Apple Yellow)
    'error': '#FF453A',           # Красный (Apple Red)
    
    # Дополнительные
    'tooltip_bg': '#2C2C2E',      # Фон тултипов
    'tooltip_fg': '#FFFFFF',      # Текст тултипов
    'divider': '#38383A',         # Разделители
}

# =============================================================================
# ☀️ СОВРЕМЕННАЯ СВЕТЛАЯ ТЕМА
# =============================================================================

LIGHT_THEME = {
    # Фоны
    'bg': '#F2F2F7',              # Основной фон
    'bg_secondary': '#FFFFFF',    # Карточки
    'bg_hover': '#E5E5EA',        # При наведении
    
    # Текст
    'fg': '#000000',
    'fg_secondary': '#8E8E93',
    'label_fg': '#1C1C1E',
    
    # Интерактивные элементы
    'select_bg': '#0A84FF',
    'select_fg': '#FFFFFF',
    'button_bg': '#E5E5EA',
    'button_fg': '#000000',
    'button_hover': '#D1D1D6',
    
    # Поля ввода
    'entry_bg': '#FFFFFF',
    'entry_fg': '#000000',
    'entry_border': '#C6C6C8',
    
    # Рамки
    'frame_bg': '#FFFFFF',
    'border': '#C6C6C8',
    
    # Акцент
    'accent': '#007AFF',
    'accent_hover': '#0056B3',
    
    # Состояния
    'success': '#34C759',
    'warning': '#FF9500',
    'error': '#FF3B30',
    
    # Дополнительные
    'tooltip_bg': '#1C1C1E',
    'tooltip_fg': '#FFFFFF',
    'divider': '#C6C6C8',
}

# =============================================================================
# 📐 ОТСТУПЫ И РАЗМЕРЫ
# =============================================================================

SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 16,
    'lg': 24,
    'xl': 32,
}

CORNER_RADIUS = {
    'sm': 4,
    'md': 8,
    'lg': 12,
}

# =============================================================================
# 🔤 ШРИФТЫ
# =============================================================================

FONTS = {
    'heading': ('Segoe UI', 20, 'bold'),      # Заголовок окна
    'title': ('Segoe UI', 14, 'bold'),        # Заголовки секций
    'body': ('Segoe UI', 11, 'normal'),       # Основной текст
    'caption': ('Segoe UI', 9, 'normal'),     # Мелкий текст, footer
}


def apply_theme(root: tk.Tk, dark: bool = True):
    """
    Применить тему к окну Tkinter.
    
    Args:
        root: Главное окно Tkinter
        dark: True для тёмной темы, False для светлой
    """
    theme = DARK_THEME if dark else LIGHT_THEME
    
    # Настройка основного окна
    root.configure(bg=theme['bg'])
    
    # Настройка стиля ttk
    style = ttk.Style(root)
    
    # Выбираем базовую тему
    try:
        if dark:
            style.theme_use('clam')  # clam лучше подходит для кастомизации
        else:
            style.theme_use('vista')  # vista для светлой на Windows
    except:
        style.theme_use('default')
    
    # =================================================================
    # Настраиваем стили TTK
    # =================================================================
    
    # Frame
    style.configure('TFrame', background=theme['bg'])
    style.configure('Card.TFrame', background=theme['bg_secondary'])  # Карточки
    
    # LabelFrame (секции)
    style.configure('TLabelframe', 
                    background=theme['bg_secondary'],
                    bordercolor=theme['border'],
                    lightcolor=theme['border'],
                    darkcolor=theme['border'])
    style.configure('TLabelframe.Label', 
                    background=theme['bg_secondary'], 
                    foreground=theme['label_fg'],
                    font=FONTS['title'])
    
    # Label
    style.configure('TLabel', 
                    background=theme['bg'], 
                    foreground=theme['fg'])
    style.configure('Card.TLabel',
                    background=theme['bg_secondary'],
                    foreground=theme['fg'])
    style.configure('Secondary.TLabel',
                    background=theme['bg'],
                    foreground=theme['fg_secondary'])
    style.configure('Heading.TLabel',
                    background=theme['bg'],
                    foreground=theme['fg'],
                    font=FONTS['heading'])
    
    # Button — обычная
    style.configure('TButton',
                    background=theme['button_bg'],
                    foreground=theme['button_fg'],
                    borderwidth=0,
                    focuscolor=theme['accent'],
                    padding=(SPACING['md'], SPACING['sm']))
    style.map('TButton',
              background=[('active', theme['button_hover']), 
                         ('pressed', theme['accent'])],
              foreground=[('active', theme['fg']), 
                         ('pressed', '#ffffff')])
    
    # Button — акцентная (для главных действий)
    style.configure('Accent.TButton',
                    background=theme['accent'],
                    foreground='#ffffff',
                    borderwidth=0,
                    padding=(SPACING['md'], SPACING['sm']))
    style.map('Accent.TButton',
              background=[('active', theme['accent_hover']), 
                         ('pressed', theme['accent_hover'])])
    
    # Entry
    style.configure('TEntry',
                    fieldbackground=theme['entry_bg'],
                    foreground=theme['entry_fg'],
                    insertcolor=theme['fg'],
                    bordercolor=theme['entry_border'],
                    lightcolor=theme['entry_border'],
                    darkcolor=theme['entry_border'])
    
    # Combobox
    style.configure('TCombobox',
                    fieldbackground=theme['entry_bg'],
                    background=theme['button_bg'],
                    foreground=theme['entry_fg'],
                    arrowcolor=theme['fg'],
                    bordercolor=theme['entry_border'])
    style.map('TCombobox',
              fieldbackground=[('readonly', theme['entry_bg'])],
              selectbackground=[('readonly', theme['select_bg'])],
              selectforeground=[('readonly', theme['select_fg'])],
              background=[('active', theme['button_hover'])])
    
    # Checkbutton
    style.configure('TCheckbutton',
                    background=theme['bg'],
                    foreground=theme['fg'])
    style.map('TCheckbutton',
              background=[('active', theme['bg_hover'])],
              foreground=[('active', theme['fg'])])
    
    # Radiobutton
    style.configure('TRadiobutton',
                    background=theme['bg'],
                    foreground=theme['fg'])
    style.map('TRadiobutton',
              background=[('active', theme['bg_hover'])],
              foreground=[('active', theme['fg'])])
    
    # Scale
    style.configure('TScale',
                    background=theme['bg'],
                    troughcolor=theme['entry_bg'])
    
    # Progressbar
    style.configure('TProgressbar',
                    background=theme['accent'],
                    troughcolor=theme['entry_bg'])
    
    # Notebook (tabs)
    style.configure('TNotebook',
                    background=theme['bg'],
                    borderwidth=0)
    style.configure('TNotebook.Tab',
                    background=theme['button_bg'],
                    foreground=theme['fg'],
                    padding=[SPACING['md'], SPACING['sm']])
    style.map('TNotebook.Tab',
              background=[('selected', theme['accent'])],
              foreground=[('selected', '#ffffff')])
    
    # Separator
    style.configure('TSeparator',
                    background=theme['divider'])
    
    # =================================================================
    # Настраиваем обычные виджеты tk
    # =================================================================
    root.option_add('*Background', theme['bg'])
    root.option_add('*Foreground', theme['fg'])
    root.option_add('*Entry.Background', theme['entry_bg'])
    root.option_add('*Entry.Foreground', theme['entry_fg'])
    root.option_add('*Button.Background', theme['button_bg'])
    root.option_add('*Button.Foreground', theme['button_fg'])
    root.option_add('*Button.activeBackground', theme['button_hover'])
    root.option_add('*Listbox.Background', theme['entry_bg'])
    root.option_add('*Listbox.Foreground', theme['entry_fg'])
    root.option_add('*Text.Background', theme['entry_bg'])
    root.option_add('*Text.Foreground', theme['entry_fg'])
    root.option_add('*Font', FONTS['body'])
    
    logger.debug(f"Применена {'тёмная' if dark else 'светлая'} тема")
    
    return theme


def style_tk_widget(widget, theme: dict, widget_type: str = 'default'):
    """
    Применить тему к обычному tk виджету.
    
    Args:
        widget: Виджет tk
        theme: Словарь с цветами темы
        widget_type: Тип виджета (button, entry, label, frame, card)
    """
    try:
        if widget_type == 'button':
            widget.configure(
                bg=theme['button_bg'],
                fg=theme['button_fg'],
                activebackground=theme['button_hover'],
                activeforeground=theme['fg'],
                relief='flat',
                borderwidth=0,
                padx=SPACING['md'],
                pady=SPACING['sm']
            )
        elif widget_type == 'accent_button':
            widget.configure(
                bg=theme['accent'],
                fg='#ffffff',
                activebackground=theme['accent_hover'],
                activeforeground='#ffffff',
                relief='flat',
                borderwidth=0,
                padx=SPACING['md'],
                pady=SPACING['sm']
            )
        elif widget_type == 'entry':
            widget.configure(
                bg=theme['entry_bg'],
                fg=theme['entry_fg'],
                insertbackground=theme['fg'],
                relief='flat',
                highlightthickness=1,
                highlightbackground=theme['entry_border'],
                highlightcolor=theme['accent']
            )
        elif widget_type == 'label':
            widget.configure(
                bg=theme['bg'],
                fg=theme['fg']
            )
        elif widget_type == 'card_label':
            widget.configure(
                bg=theme['bg_secondary'],
                fg=theme['fg']
            )
        elif widget_type == 'frame':
            widget.configure(bg=theme['bg'])
        elif widget_type == 'card':
            widget.configure(bg=theme['bg_secondary'])
        else:
            widget.configure(bg=theme['bg'])
    except tk.TclError:
        pass  # Виджет не поддерживает эти опции


def create_tooltip(widget, text: str, theme: dict = None):
    """
    Создать современный тёмный тултип для виджета.
    
    Args:
        widget: Виджет, к которому привязать тултип
        text: Текст тултипа
        theme: Тема (по умолчанию DARK_THEME)
    """
    if theme is None:
        theme = DARK_THEME
    
    tooltip = None
    
    def show_tooltip(event):
        nonlocal tooltip
        if tooltip:
            return
            
        # Создаём окно тултипа
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        
        # Позиция — справа от курсора
        x = event.x_root + 12
        y = event.y_root + 8
        tooltip.wm_geometry(f"+{x}+{y}")
        
        # Контейнер с отступами
        frame = tk.Frame(
            tooltip,
            bg=theme['tooltip_bg'],
            padx=SPACING['sm'],
            pady=SPACING['xs']
        )
        frame.pack()
        
        # Текст тултипа
        label = tk.Label(
            frame,
            text=text,
            background=theme['tooltip_bg'],
            foreground=theme['tooltip_fg'],
            font=FONTS['caption'],
            justify='left'
        )
        label.pack()
        
        # Автоскрытие через 4 секунды
        widget.after(4000, hide_tooltip)
    
    def hide_tooltip(event=None):
        nonlocal tooltip
        if tooltip:
            try:
                tooltip.destroy()
            except:
                pass
            tooltip = None
    
    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)
    widget.bind("<Button>", hide_tooltip)


def get_current_theme(dark: bool = True) -> dict:
    """
    Получить текущую тему без применения к окну.
    
    Args:
        dark: True для тёмной темы
    
    Returns:
        Словарь с цветами темы
    """
    return DARK_THEME if dark else LIGHT_THEME
