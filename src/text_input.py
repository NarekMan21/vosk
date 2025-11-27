"""
Модуль эмуляции клавиатурного ввода через Windows API SendInput.
"""
import ctypes
import logging
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)

# Константы Windows API
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Структуры Windows API
# ULONG_PTR - размер зависит от архитектуры (4 байта на 32-bit, 8 байт на 64-bit)
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION)
    ]

class TextInput:
    """Класс для эмуляции клавиатурного ввода в активное окно."""
    
    def __init__(self):
        """Инициализация модуля ввода текста."""
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.send_input = self.user32.SendInput
        self.send_input.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        self.send_input.restype = wintypes.UINT
        self.get_last_error = self.kernel32.GetLastError
        self.get_last_error.restype = wintypes.DWORD
        
    def send_unicode_char(self, char):
        """
        Отправка одного Unicode символа.
        
        Args:
            char: Символ для ввода
        """
        # Получаем код символа
        vk = 0
        scan = ord(char)
        
        # Создаем структуру для нажатия клавиши
        inputs = (INPUT * 2)()
        
        # Нажатие клавиши
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = vk
        inputs[0].union.ki.wScan = scan
        inputs[0].union.ki.dwFlags = KEYEVENTF_UNICODE
        inputs[0].union.ki.time = 0
        inputs[0].union.ki.dwExtraInfo = 0
        
        # Отпускание клавиши
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = vk
        inputs[1].union.ki.wScan = scan
        inputs[1].union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        inputs[1].union.ki.time = 0
        inputs[1].union.ki.dwExtraInfo = 0
        
        # Отправка - передаем массив структур
        result = self.send_input(2, inputs, ctypes.sizeof(INPUT))
        if result != 2:
            error_code = self.get_last_error()
            # Логируем только если это реальная ошибка (не просто отсутствие активного окна)
            if error_code != 0:
                logger.warning(f"Не удалось отправить символ '{char}'. SendInput вернул: {result}, GetLastError: {error_code}")
            # Не логируем предупреждения для случая, когда просто нет активного окна
            return False
        return True
    
    def send_text_via_clipboard(self, text):
        """
        Отправка текста через буфер обмена (более надежный метод).
        
        Args:
            text: Текст для ввода
        """
        if not text:
            return False
        
        try:
            import win32clipboard
            import win32con
            
            # Сохраняем текущее содержимое буфера обмена
            old_data = None
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    old_data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass
            
            # Копируем текст в буфер обмена
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            
            # Увеличиваем задержку для надежности
            time.sleep(0.3)
            
            # Пробуем вставить через несколько методов
            success = False
            
            # Метод 1: pyautogui (самый надежный)
            try:
                import pyautogui
                logger.info(f"Попытка вставить текст через pyautogui: {repr(text)}")
                # Вставляем через Ctrl+V (без клика, чтобы не вызывать двойную вставку)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.15)  # Даем время на вставку
                success = True
                logger.info(f"Текст успешно вставлен через pyautogui: {repr(text)}")
            except ImportError:
                logger.warning("pyautogui не установлен, пробуем другие методы")
            except Exception as e:
                logger.warning(f"PyAutoGUI не смог вставить текст: {e}")
            
            # Метод 2: keyboard библиотека (если pyautogui не сработал)
            if not success:
                try:
                    import keyboard
                    logger.info("Попытка вставить текст через keyboard библиотеку")
                    keyboard.send('ctrl+v')
                    time.sleep(0.2)
                    success = True
                    logger.info(f"Текст вставлен через keyboard: {repr(text)}")
                except ImportError:
                    logger.warning("keyboard не установлен, пробуем SendInput")
                except Exception as e:
                    logger.warning(f"keyboard не смог вставить текст: {e}")
            
            # Метод 3: SendInput (последний вариант)
            if not success:
                logger.info("Попытка вставить текст через SendInput")
                if self.send_key_combination(0x56, ctrl=True):  # VK_V = 0x56
                    success = True
                    logger.info(f"Текст вставлен через SendInput: {repr(text)}")
                else:
                    logger.warning("Не удалось автоматически вставить текст через SendInput")
            
            # Если вставка прошла успешно, оставляем распознанный текст в буфере обмена,
            # чтобы пользователь мог повторно вставить его вручную при необходимости.
            if success:
                logger.debug("Распознанный текст оставлен в буфере обмена")
            else:
                # Если вставка не удалась, восстанавливаем старые данные
                time.sleep(0.1)
                if old_data is not None:
                    try:
                        win32clipboard.OpenClipboard()
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_data)
                        win32clipboard.CloseClipboard()
                    except:
                        pass
            
            if success:
                logger.info(f"Текст успешно отправлен через буфер обмена: {repr(text)}")
            else:
                logger.warning(f"Текст скопирован в буфер обмена, но автоматическая вставка не удалась. Нажмите Ctrl+V вручную. Текст: {repr(text)}")
            
            return success
            
        except ImportError:
            logger.warning("pywin32 не установлен, используем прямой ввод")
            return False
        except Exception as e:
            logger.error(f"Ошибка при отправке текста через буфер обмена: {e}", exc_info=True)
            return False
    
    def send_text(self, text):
        """
        Отправка текста посимвольно в активное окно.
        Пытается использовать буфер обмена, если прямой ввод не работает.
        
        Args:
            text: Текст для ввода
        """
        if not text:
            return
        
        try:
            # Сначала пробуем через буфер обмена (более надежно)
            if self.send_text_via_clipboard(text):
                return
            
            # Если не получилось, пробуем прямой ввод
            success_count = 0
            for char in text:
                if self.send_unicode_char(char):
                    success_count += 1
                # Небольшая задержка между символами для стабильности
                time.sleep(0.01)
            
            if success_count > 0:
                logger.debug(f"Текст отправлен: {repr(text)} ({success_count}/{len(text)} символов)")
            else:
                logger.warning(f"Не удалось отправить текст: {repr(text)}. Убедитесь, что активное окно принимает ввод текста.")
        except Exception as e:
            logger.error(f"Ошибка при отправке текста: {e}", exc_info=True)
    
    def send_key_combination(self, vk_code, ctrl=False, shift=False, alt=False):
        """
        Отправка комбинации клавиш.
        
        Args:
            vk_code: Виртуальный код клавиши
            ctrl: Нажать Ctrl
            shift: Нажать Shift
            alt: Нажать Alt
        
        Returns:
            True если успешно, False иначе
        """
        # Для Ctrl+V пробуем сначала через pyautogui (более надежно)
        # Но только если это не вызывается из send_text_via_clipboard (чтобы избежать двойной вставки)
        if ctrl and vk_code == 0x56:  # Ctrl+V
            try:
                import pyautogui
                logger.debug("Отправка Ctrl+V через pyautogui")
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.1)
                logger.debug("Ctrl+V успешно отправлен через pyautogui")
                return True
            except ImportError:
                logger.debug("pyautogui не установлен, используем SendInput")
            except Exception as e:
                logger.debug(f"PyAutoGUI не смог отправить Ctrl+V: {e}")
        
        inputs = []
        
        # Модификаторы - нажатие
        if ctrl:
            inputs.append(self._create_key_input(0x11, False))  # VK_CONTROL
        if shift:
            inputs.append(self._create_key_input(0x10, False))  # VK_SHIFT
        if alt:
            inputs.append(self._create_key_input(0x12, False))  # VK_MENU
        
        # Основная клавиша - нажатие и отпускание
        inputs.append(self._create_key_input(vk_code, False))
        inputs.append(self._create_key_input(vk_code, True))
        
        # Отпускание модификаторов
        if alt:
            inputs.append(self._create_key_input(0x12, True))
        if shift:
            inputs.append(self._create_key_input(0x10, True))
        if ctrl:
            inputs.append(self._create_key_input(0x11, True))
        
        # Отправка
        if len(inputs) == 0:
            return False
        
        input_array = (INPUT * len(inputs))(*inputs)
        result = self.send_input(len(inputs), input_array, ctypes.sizeof(INPUT))
        
        if result != len(inputs):
            error_code = self.get_last_error()
            if error_code != 0:
                logger.debug(f"SendInput вернул: {result}, GetLastError: {error_code}")
            return False
        
        return True
    
    def _create_key_input(self, vk_code, key_up):
        """
        Создание структуры INPUT для клавиши.
        
        Args:
            vk_code: Виртуальный код клавиши
            key_up: True для отпускания, False для нажатия
        
        Returns:
            Структура INPUT
        """
        input_struct = INPUT()
        input_struct.type = INPUT_KEYBOARD
        input_struct.union.ki.wVk = vk_code
        input_struct.union.ki.wScan = 0
        input_struct.union.ki.dwFlags = KEYEVENTF_KEYUP if key_up else 0
        input_struct.union.ki.time = 0
        input_struct.union.ki.dwExtraInfo = 0
        return input_struct

