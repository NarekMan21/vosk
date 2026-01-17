"""
Модуль Windows Toast уведомлений.
"""
import logging
import threading

logger = logging.getLogger(__name__)

# Флаг доступности библиотеки
_toast_available = None


def _check_toast():
    """Проверяет доступность библиотеки toast."""
    global _toast_available
    if _toast_available is None:
        try:
            from win11toast import toast
            _toast_available = True
            logger.debug("win11toast доступен")
        except ImportError:
            logger.warning("win11toast не установлен, уведомления отключены")
            _toast_available = False
    return _toast_available


class Notifications:
    """Windows Toast уведомления."""
    
    APP_ID = "VoiceInput"
    
    def __init__(self, enabled=True):
        """
        Инициализация уведомлений.
        
        Args:
            enabled: Включить/выключить уведомления
        """
        self.enabled = enabled and _check_toast()
    
    def show(self, title: str, message: str, duration: str = "short"):
        """
        Показать уведомление.
        
        Args:
            title: Заголовок
            message: Текст сообщения
            duration: "short" (~5 сек) или "long" (~25 сек)
        """
        if not self.enabled:
            return
        
        def _show():
            try:
                from win11toast import toast
                toast(title, message, app_id=self.APP_ID, duration=duration)
            except Exception as e:
                logger.debug(f"Ошибка уведомления: {e}")
        
        # Асинхронно чтобы не блокировать
        threading.Thread(target=_show, daemon=True).start()
    
    def show_start(self):
        """Уведомление о включении распознавания."""
        self.show("VoiceInput", "🎤 Распознавание включено")
    
    def show_stop(self):
        """Уведомление о выключении распознавания."""
        self.show("VoiceInput", "⏹️ Распознавание выключено")
    
    def show_error(self, error: str):
        """Уведомление об ошибке."""
        self.show("VoiceInput — Ошибка", f"❌ {error}")
    
    def show_ready(self):
        """Уведомление о готовности."""
        self.show("VoiceInput", "✅ Готово к работе")
    
    def show_loading(self, message: str = "Загрузка модели..."):
        """Уведомление о загрузке."""
        self.show("VoiceInput", f"⏳ {message}")
    
    def show_microphone_error(self):
        """Уведомление об ошибке микрофона."""
        self.show("VoiceInput", "🎤 Микрофон не найден. Проверьте подключение.")
    
    def show_microphone_reconnected(self):
        """Уведомление о переподключении микрофона."""
        self.show("VoiceInput", "🎤 Микрофон подключён")


# Глобальный экземпляр для удобства
_notifications = None


def get_notifications(enabled=True) -> Notifications:
    """Получить глобальный экземпляр уведомлений."""
    global _notifications
    if _notifications is None:
        _notifications = Notifications(enabled=enabled)
    return _notifications
