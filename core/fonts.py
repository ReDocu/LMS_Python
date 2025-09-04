# core/fonts.py
import pygame

_FONT_CANDIDATES = [
    # Windows
    "malgungothic", "맑은 고딕",
    # macOS
    "Apple SD Gothic Neo",
    # Linux / cross-platform
    "Noto Sans CJK KR", "NotoSansCJKkr", "Noto Sans KR", "NanumGothic",
    # fallback
    "Arial Unicode MS", "arial",
]

def _match_font():
    for name in _FONT_CANDIDATES:
        path = pygame.font.match_font(name)
        if path:
            return path
    return None

def load_font(size: int, bold: bool=False):
    path = _match_font()
    if path:
        f = pygame.font.Font(path, size)
    else:
        f = pygame.font.SysFont(None, size)  # 최후 수단
    f.set_bold(bold)
    return f
