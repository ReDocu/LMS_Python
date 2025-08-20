# gfx/text.py
import pygame
from typing import Literal, Tuple
from core.renderer import Renderer

Anchor = Literal["topleft", "topright", "bottomleft", "bottomright", "center", "midtop", "midbottom", "midleft", "midright"]

def draw_text(
    r: Renderer, font: pygame.font.Font, text: str, color: Tuple[int,int,int],
    pos, anchor: Anchor="topleft", use_camera=False, bg=None
):
    # 텍스트는 보통 UI니까 기본값 use_camera=False
    surf = font.render(text, True, color, bg)
    rect = getattr(surf.get_rect(), "copy")()
    setattr(rect, anchor, r._to_screen(pos, use_camera))
    r.surface.blit(surf, rect)