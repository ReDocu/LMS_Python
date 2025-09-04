# core/clipboard.py
import pygame

# 시도 순서: pygame.scrap -> pyperclip
_HAS_SCRAP = False
try:
    import pygame.scrap as scrap
    _HAS_SCRAP = True
except Exception:
    _HAS_SCRAP = False

try:
    import pyperclip
    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False


def init():
    """윈도우가 생성된 뒤(= display.set_mode 이후) 한 번만 호출."""
    if _HAS_SCRAP:
        try:
            if not scrap.get_init():
                scrap.init()
        except Exception:
            pass


def set_text(text: str):
    if _HAS_SCRAP:
        try:
            scrap.put(scrap.SCRAP_TEXT, text.encode("utf-8"))
            return
        except Exception:
            pass
    if _HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return
        except Exception:
            pass
    # 실패해도 조용히 무시 (환경에 따라 클립보드가 아예 없을 수 있음)


def get_text() -> str:
    if _HAS_SCRAP:
        try:
            raw = scrap.get(scrap.SCRAP_TEXT)
            if raw:
                try:
                    return raw.decode("utf-8")
                except Exception:
                    return raw.decode(errors="ignore")
        except Exception:
            pass
    if _HAS_PYPERCLIP:
        try:
            return pyperclip.paste() or ""
        except Exception:
            pass
    return ""
