"""
Модуль системного трея с иконкой и меню управления.
"""
import logging
import threading
import time
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
        
        # Анимация
        self._animation_thread = None
        self._animation_running = False
        self._is_speaking = False
    
    def _create_icon(self, state='stopped', pulse_intensity=0):
        """
        Создание иконки для системного трея.
        
        Args:
            state: 'active' - зеленый, 'paused' - оранжевый, 
                   'loading' - жёлтый, 'error' - красный, 'stopped' - белый,
                   'speaking' - ярко-зеленый с пульсацией
            pulse_intensity: Интенсивность пульсации 0.0-1.0 (для анимации)
        """
        # Определяем цвет фона в зависимости от состояния
        if state == 'speaking':
            # Пульсация от зелёного к ярко-зелёному/белому
            base_g = 180
            pulse_add = int(75 * pulse_intensity)
            bg_color = (50 + int(50 * pulse_intensity), base_g + pulse_add, 50)
        elif state == 'active':
            bg_color = (0, 180, 0)  # Зелёный
        elif state == 'paused':
            bg_color = (255, 165, 0)  # Оранжевый
        elif state == 'loading':
            bg_color = (255, 255, 0)  # Жёлтый
        elif state == 'error':
            bg_color = (255, 0, 0)  # Красный
        else:  # stopped
            bg_color = (240, 240, 240)  # Светло-серый
        
        # Создаем иконку с микрофоном
        image = Image.new('RGB', (64, 64), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Рисуем простой микрофон
        mic_color = 'black'
        
        # Корпус микрофона
        draw.ellipse([20, 15, 44, 45], fill=mic_color)
        # Подставка
        draw.rectangle([28, 45, 36, 50], fill=mic_color)
        # Ножка
        draw.rectangle([30, 50, 34, 55], fill=mic_color)
        
        # Если говорит — добавляем волны
        if state == 'speaking' and pulse_intensity > 0.3:
            wave_color = (100, 255, 100)
            # Левая волна
            draw.arc([10, 20, 22, 40], start=120, end=240, fill=wave_color, width=2)
            # Правая волна
            draw.arc([42, 20, 54, 40], start=-60, end=60, fill=wave_color, width=2)
        
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
    
    def set_loading(self, message="Загрузка..."):
        """
        Установить состояние загрузки.
        
        Args:
            message: Текст для tooltip
        """
        self.update_icon('loading')
        self.update_tooltip(f"VoiceInput: {message}")
    
    def set_error(self, message="Ошибка"):
        """
        Установить состояние ошибки.
        
        Args:
            message: Текст для tooltip
        """
        self.update_icon('error')
        self.update_tooltip(f"VoiceInput: {message}")
    
    def set_ready(self):
        """Установить состояние готовности (остановлен, но готов к работе)."""
        self.is_active = False
        self.is_paused = False
        self.stop_animation()
        self.update_icon('stopped')
        self.update_tooltip("VoiceInput: Готов к работе")
    
    def set_speaking(self, is_speaking: bool):
        """
        Установить состояние говорения (для анимации).
        
        Args:
            is_speaking: True если обнаружена речь
        """
        if is_speaking and not self._is_speaking:
            self._is_speaking = True
            self._start_animation()
        elif not is_speaking and self._is_speaking:
            self._is_speaking = False
            self._stop_animation()
            # Возвращаем обычное активное состояние
            if self.is_active:
                self.update_icon('active')
    
    def _start_animation(self):
        """Запуск анимации пульсации."""
        if self._animation_running:
            return
        
        self._animation_running = True
        self._animation_thread = threading.Thread(target=self._animate_pulse, daemon=True)
        self._animation_thread.start()
    
    def _stop_animation(self):
        """Остановка анимации."""
        self._animation_running = False
        if self._animation_thread:
            self._animation_thread = None
    
    def stop_animation(self):
        """Публичный метод остановки анимации."""
        self._is_speaking = False
        self._stop_animation()
    
    def _animate_pulse(self):
        """Поток анимации пульсации."""
        import math
        
        frame = 0
        while self._animation_running and self.icon:
            try:
                # Синусоидальная пульсация
                intensity = (math.sin(frame * 0.3) + 1) / 2  # 0.0 to 1.0
                
                new_icon = self._create_icon('speaking', pulse_intensity=intensity)
                self.icon.icon = new_icon
                
                frame += 1
                time.sleep(0.05)  # ~20 FPS
            except Exception as e:
                logger.debug(f"Ошибка анимации: {e}")
                break
        
        # Возврат к нормальному состоянию
        if self.icon and self.is_active:
            try:
                self.icon.icon = self._create_icon('active')
            except:
                pass

