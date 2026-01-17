"""
Voice Activity Detection — фильтр тишины.

Использует webrtcvad для обнаружения голосовой активности,
что снижает нагрузку на CPU при отсутствии речи.
"""
import logging
import collections

logger = logging.getLogger(__name__)

# Lazy import для graceful fallback
_webrtcvad = None


def _get_vad():
    """Ленивая загрузка webrtcvad с обработкой ошибки импорта."""
    global _webrtcvad
    if _webrtcvad is None:
        try:
            import webrtcvad
            _webrtcvad = webrtcvad
            logger.info("webrtcvad успешно загружен")
        except ImportError:
            logger.warning("webrtcvad не установлен, VAD отключён")
    return _webrtcvad


class VoiceActivityDetector:
    """
    Детектор голосовой активности на основе webrtcvad.
    
    Используется для фильтрации тишины, чтобы не нагружать
    модель распознавания бессмысленными данными.
    """
    
    def __init__(self, sample_rate=16000, aggressiveness=2, enabled=True):
        """
        Инициализация VAD.
        
        Args:
            sample_rate: Частота дискретизации (8000, 16000, 32000, или 48000)
            aggressiveness: Агрессивность фильтрации 0-3 (3 = максимальная фильтрация)
            enabled: Включить/отключить VAD
        """
        self.sample_rate = sample_rate
        self.enabled = enabled
        self.aggressiveness = aggressiveness
        
        webrtcvad = _get_vad()
        if webrtcvad and enabled:
            try:
                self.vad = webrtcvad.Vad(aggressiveness)
                logger.info(f"VAD инициализирован: aggressiveness={aggressiveness}")
            except Exception as e:
                logger.error(f"Ошибка инициализации VAD: {e}")
                self.vad = None
                self.enabled = False
        else:
            self.vad = None
            self.enabled = False
        
        # Ring buffer для сглаживания решений (гистерезис)
        # Увеличен для более плавной работы — не обрезает речь
        self._ring_buffer = collections.deque(maxlen=30)
        self._triggered = False
        self._silence_frames = 0  # Счётчик тишины после речи
        self._silence_threshold = 50  # Сколько фреймов тишины нужно для отключения
        
        # Размер фрейма для webrtcvad: 10, 20, или 30 мс
        # 30 мс даёт лучший баланс точности и производительности
        self._frame_duration_ms = 30
        # Размер фрейма в байтах (16-bit audio = 2 bytes per sample)
        self._frame_size = int(sample_rate * self._frame_duration_ms / 1000) * 2
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Проверяет, содержит ли аудио-чанк речь.
        
        Args:
            audio_chunk: Аудио данные в формате 16-bit PCM
        
        Returns:
            True если обнаружена речь, False если тишина
        """
        if not self.enabled or not self.vad:
            return True  # VAD отключён — пропускаем всё (как будто есть речь)
        
        # Анализируем фреймы внутри чанка
        speech_frames = 0
        total_frames = 0
        offset = 0
        
        while offset + self._frame_size <= len(audio_chunk):
            frame = audio_chunk[offset:offset + self._frame_size]
            try:
                if self.vad.is_speech(frame, self.sample_rate):
                    speech_frames += 1
            except Exception:
                # Игнорируем ошибки отдельных фреймов
                pass
            total_frames += 1
            offset += self._frame_size
        
        if total_frames == 0:
            return True  # Нет данных для анализа — пропускаем
        
        # Решение с гистерезисом для плавности
        # Порог снижен для лучшего обнаружения начала речи
        is_speech = speech_frames / total_frames > 0.2
        self._ring_buffer.append(is_speech)
        
        if not self._triggered:
            # Включаемся быстро — если 40% буфера показывает речь
            if len(self._ring_buffer) >= 2 and sum(self._ring_buffer) > 0.4 * len(self._ring_buffer):
                self._triggered = True
                self._silence_frames = 0
                logger.debug("VAD: речь обнаружена")
        else:
            # Выключаемся медленно — нужно много тишины подряд
            if is_speech:
                self._silence_frames = 0  # Сброс при любой речи
            else:
                self._silence_frames += 1
            
            # Отключаемся только после долгой тишины
            if self._silence_frames >= self._silence_threshold:
                self._triggered = False
                self._silence_frames = 0
                logger.debug("VAD: тишина (после паузы)")
        
        return self._triggered
    
    def reset(self):
        """Сброс состояния VAD (например, при перезапуске распознавания)."""
        self._ring_buffer.clear()
        self._triggered = False
        self._silence_frames = 0
        logger.debug("VAD: состояние сброшено")
    
    @property
    def is_available(self) -> bool:
        """Проверяет, доступен ли VAD."""
        return self.vad is not None and self.enabled
