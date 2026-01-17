"""
Модуль управления темами UI.
"""
import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

# Цвета тёмной темы
DARK_THEME = {
    'bg': '#1e1e1e',
    'fg': '#ffffff',
    'select_bg': '#3d3d3d',
    'select_fg': '#ffffff',
    'button_bg': '#3d3d3d',
    'button_fg': '#ffffff',
    'entry_bg': '#2d2d2d',
    'entry_fg': '#ffffff',
    'frame_bg': '#252526',
    'label_fg': '#cccccc',
    'accent': '#0078d4',
    'success': '#4ec9b0',
    'warning': '#dcdcaa',
    'error': '#f14c4c',
}

# Цвета светлой темы
LIGHT_THEME = {
    'bg': '#f0f0f0',
    'fg': '#000000',
    'select_bg': '#0078d4',
    'select_fg': '#ffffff',
    'button_bg': '#e1e1e1',
    'button_fg': '#000000',
    'entry_bg': '#ffffff',
    'entry_fg': '#000000',
    'frame_bg': '#ffffff',
    'label_fg': '#333333',
    'accent': '#0078d4',
    'success': '#107c10',
    'warning': '#ff8c00',
    'error': '#e81123',
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
    
    # Настраиваем стили
    
    # Frame
    style.configure('TFrame', background=theme['bg'])
    style.configure('TLabelframe', background=theme['bg'])
    style.configure('TLabelframe.Label', 
                    background=theme['bg'], 
                    foreground=theme['fg'])
    
    # Label
    style.configure('TLabel', 
                    background=theme['bg'], 
                    foreground=theme['fg'])
    
    # Button
    style.configure('TButton',
                    background=theme['button_bg'],
                    foreground=theme['button_fg'])
    style.map('TButton',
              background=[('active', theme['accent']), ('pressed', theme['accent'])],
              foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
    
    # Entry
    style.configure('TEntry',
                    fieldbackground=theme['entry_bg'],
                    foreground=theme['entry_fg'],
                    insertcolor=theme['fg'])
    
    # Combobox
    style.configure('TCombobox',
                    fieldbackground=theme['entry_bg'],
                    background=theme['button_bg'],
                    foreground=theme['entry_fg'],
                    arrowcolor=theme['fg'])
    style.map('TCombobox',
              fieldbackground=[('readonly', theme['entry_bg'])],
              selectbackground=[('readonly', theme['select_bg'])],
              selectforeground=[('readonly', theme['select_fg'])])
    
    # Checkbutton
    style.configure('TCheckbutton',
                    background=theme['bg'],
                    foreground=theme['fg'])
    style.map('TCheckbutton',
              background=[('active', theme['bg'])],
              foreground=[('active', theme['fg'])])
    
    # Radiobutton
    style.configure('TRadiobutton',
                    background=theme['bg'],
                    foreground=theme['fg'])
    style.map('TRadiobutton',
              background=[('active', theme['bg'])],
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
                    background=theme['bg'])
    style.configure('TNotebook.Tab',
                    background=theme['button_bg'],
                    foreground=theme['fg'],
                    padding=[10, 2])
    style.map('TNotebook.Tab',
              background=[('selected', theme['accent'])],
              foreground=[('selected', '#ffffff')])
    
    # Также настроим обычные виджеты tk
    root.option_add('*Background', theme['bg'])
    root.option_add('*Foreground', theme['fg'])
    root.option_add('*Entry.Background', theme['entry_bg'])
    root.option_add('*Entry.Foreground', theme['entry_fg'])
    root.option_add('*Button.Background', theme['button_bg'])
    root.option_add('*Button.Foreground', theme['button_fg'])
    root.option_add('*Listbox.Background', theme['entry_bg'])
    root.option_add('*Listbox.Foreground', theme['entry_fg'])
    root.option_add('*Text.Background', theme['entry_bg'])
    root.option_add('*Text.Foreground', theme['entry_fg'])
    
    logger.debug(f"Применена {'тёмная' if dark else 'светлая'} тема")
    
    return theme


def style_tk_widget(widget, theme: dict, widget_type: str = 'default'):
    """
    Применить тему к обычному tk виджету.
    
    Args:
        widget: Виджет tk
        theme: Словарь с цветами темы
        widget_type: Тип виджета (button, entry, label, frame)
    """
    try:
        if widget_type == 'button':
            widget.configure(
                bg=theme['button_bg'],
                fg=theme['button_fg'],
                activebackground=theme['accent'],
                activeforeground='#ffffff'
            )
        elif widget_type == 'entry':
            widget.configure(
                bg=theme['entry_bg'],
                fg=theme['entry_fg'],
                insertbackground=theme['fg']
            )
        elif widget_type == 'label':
            widget.configure(
                bg=theme['bg'],
                fg=theme['fg']
            )
        elif widget_type == 'frame':
            widget.configure(bg=theme['bg'])
        else:
            widget.configure(bg=theme['bg'])
    except tk.TclError:
        pass  # Виджет не поддерживает эти опции
