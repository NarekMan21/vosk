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
        self._create_icon()
    
    def _create_icon(self):
        """Создание иконки для системного трея."""
        # Создаем простую иконку с микрофоном
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        
        # Рисуем простой микрофон
        # Корпус микрофона
        draw.ellipse([20, 15, 44, 45], fill='black')
        # Подставка
        draw.rectangle([28, 45, 36, 50], fill='black')
        # Ножка
        draw.rectangle([30, 50, 34, 55], fill='black')
        
        self.icon_image = image
    
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
    
    def set_active(self, active):
        """
        Установка состояния активности.
        
        Args:
            active: True если активно, False иначе
        """
        self.is_active = active
        if self.icon:
            # Обновляем меню
            self.icon.menu = self._create_menu()
            # Можно изменить иконку в зависимости от состояния
            # Например, сделать ее зеленой когда активно
    
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

