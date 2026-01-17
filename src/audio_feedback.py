"""
Модуль звуковой обратной связи.
"""
import logging
import threading

logger = logging.getLogger(__name__)

# Проверяем доступность winsound (только Windows)
try:
    import winsound
    _winsound_available = True
except ImportError:
    _winsound_available = False
    logger.warning("winsound недоступен, звуковая обратная связь отключена")


class AudioFeedback:
    """Звуковые уведомления для пользователя."""
    
    # Частоты для разных событий (Гц)
    FREQ_START = 1000   # Высокий тон для включения
    FREQ_STOP = 500     # Низкий тон для выключения
    FREQ_ERROR = 300    # Очень низкий для ошибки
    FREQ_READY = 800    # Средний для готовности
    
    # Длительности (мс)
    DURATION_SHORT = 100
    DURATION_LONG = 200
    
    def __init__(self, enabled=True):
        """
        Инициализация звуковой обратной связи.
        
        Args:
            enabled: Включить/выключить звуки
        """
        self.enabled = enabled and _winsound_available
    
    def _play_async(self, frequency: int, duration: int):
        """
        Воспроизвести звук асинхронно.
        
        Args:
            frequency: Частота в Гц (37-32767)
            duration: Длительность в мс
        """
        if not self.enabled:
            return
        
        def _play():
            try:
                winsound.Beep(frequency, duration)
            except Exception as e:
                logger.debug(f"Ошибка воспроизведения звука: {e}")
        
        threading.Thread(target=_play, daemon=True).start()
    
    def play_start(self):
        """Звук включения распознавания."""
        self._play_async(self.FREQ_START, self.DURATION_SHORT)
    
    def play_stop(self):
        """Звук выключения распознавания."""
        self._play_async(self.FREQ_STOP, self.DURATION_SHORT)
    
    def play_error(self):
        """Звук ошибки."""
        self._play_async(self.FREQ_ERROR, self.DURATION_LONG)
    
    def play_ready(self):
        """Звук готовности."""
        # Два коротких бипа
        def _play_ready():
            try:
                winsound.Beep(self.FREQ_READY, 80)
                winsound.Beep(self.FREQ_READY + 200, 80)
            except:
                pass
        
        if self.enabled:
            threading.Thread(target=_play_ready, daemon=True).start()
    
    def play_pause(self):
        """Звук паузы."""
        self._play_async(700, self.DURATION_SHORT)
    
    def play_resume(self):
        """Звук возобновления."""
        self._play_async(900, self.DURATION_SHORT)


# Глобальный экземпляр
_audio_feedback = None


def get_audio_feedback(enabled=True) -> AudioFeedback:
    """Получить глобальный экземпляр звуковой обратной связи."""
    global _audio_feedback
    if _audio_feedback is None:
        _audio_feedback = AudioFeedback(enabled=enabled)
    return _audio_feedback
