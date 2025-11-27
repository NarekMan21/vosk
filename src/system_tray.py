"""
Модуль системного трея с иконкой и меню управления.
"""
import logging
import threading
from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)

class SystemTray:
    """Класс для управления иконкой в системном трее."""
    
    def __init__(self, on_toggle=None, on_exit=None, on_settings=None):
        """
        Инициализация системного трея.
        
        Args:
            on_toggle: Функция для включения/выключения
            on_exit: Функция для выхода
            on_settings: Функция для открытия настроек
        """
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.on_settings = on_settings
        self.icon = None
        self.is_active = False
        self.is_paused = False
        self.icon_image = self._create_icon('stopped')
    
    def _create_icon(self, state='stopped'):
        """
        Создание иконки для системного трея.
        
        Args:
            state: 'active' - зеленый, 'paused' - оранжевый, 'stopped' - белый
        """
        # Определяем цвет фона в зависимости от состояния
        if state == 'active':
            bg_color = 'green'
        elif state == 'paused':
            bg_color = 'orange'
        else:  # stopped
            bg_color = 'white'
        
        # Создаем иконку с микрофоном
        image = Image.new('RGB', (64, 64), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Рисуем простой микрофон
        # Корпус микрофона
        draw.ellipse([20, 15, 44, 45], fill='black')
        # Подставка
        draw.rectangle([28, 45, 36, 50], fill='black')
        # Ножка
        draw.rectangle([30, 50, 34, 55], fill='black')
        
        return image
    
    def update_icon(self, state='stopped'):
        """
        Обновление иконки в зависимости от состояния.
        
        Args:
            state: 'active' - зеленый, 'paused' - оранжевый, 'stopped' - белый
        """
        if self.icon:
            new_image = self._create_icon(state)
            self.icon.icon = new_image
    
    def _create_menu(self):
        """Создание контекстного меню."""
        menu_items = []
        
        # Переключатель активности
        status_text = "Включить" if not self.is_active else "Выключить"
        menu_items.append(
            pystray.MenuItem(status_text, self._on_toggle_clicked)
        )
        
        menu_items.append(pystray.Menu.SEPARATOR)
        
        # Настройки
        if self.on_settings:
            menu_items.append(
                pystray.MenuItem("Настройки", self._on_settings_clicked)
            )
        
        menu_items.append(pystray.Menu.SEPARATOR)
        
        # Выход
        menu_items.append(
            pystray.MenuItem("Выход", self._on_exit_clicked)
        )
        
        return pystray.Menu(*menu_items)
    
    def _on_toggle_clicked(self, icon, item):
        """Обработчик клика по переключателю."""
        if self.on_toggle:
            self.on_toggle()
    
    def _on_exit_clicked(self, icon, item):
        """Обработчик клика по выходу."""
        if self.on_exit:
            self.on_exit()
        self.stop()
    
    def _on_settings_clicked(self, icon, item):
        """Обработчик клика по настройкам."""
        if self.on_settings:
            self.on_settings()
    
    def set_active(self, active, paused=False):
        """
        Установка состояния активности.
        
        Args:
            active: True если активно, False иначе
            paused: True если на паузе, False иначе
        """
        self.is_active = active
        self.is_paused = paused
        
        if self.icon:
            # Обновляем меню
            self.icon.menu = self._create_menu()
            
            # Определяем состояние для иконки
            if active and not paused:
                state = 'active'
            elif active and paused:
                state = 'paused'
            else:
                state = 'stopped'
            
            # Обновляем иконку
            self.update_icon(state)
    
    def start(self):
        """Запуск иконки в системном трее."""
        if self.icon:
            logger.warning("Иконка уже запущена")
            return
        
        menu = self._create_menu()
        self.icon = pystray.Icon("VoiceInput", self.icon_image, "Голосовой ввод", menu)
        
        # Запуск в отдельном потоке
        self.thread = threading.Thread(target=self._run_icon, daemon=True)
        self.thread.start()
        logger.info("Иконка системного трея запущена")
    
    def _run_icon(self):
        """Запуск иконки (вызывается в отдельном потоке)."""
        try:
            self.icon.run()
        except Exception as e:
            logger.error(f"Ошибка при работе иконки: {e}")
    
    def stop(self):
        """Остановка иконки."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logger.error(f"Ошибка при остановке иконки: {e}")
            finally:
                self.icon = None
        logger.info("Иконка системного трея остановлена")
    
    def update_tooltip(self, text):
        """
        Обновление подсказки иконки.
        
        Args:
            text: Текст подсказки
        """
        if self.icon:
            self.icon.title = text

