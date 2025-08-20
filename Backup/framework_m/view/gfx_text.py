# view/gfx_text.py
import pygame
from typing import Literal, Tuple
from view.renderer import Renderer

Anchor = Literal["topleft","topright","bottomleft","bottomright","center",
                 "midtop","midbottom","midleft","midright"]

def draw_text(r: Renderer, font: pygame.font.Font, text: str,
              color: Tuple[int,int,int], pos, *, anchor: Anchor="topleft",
              use_camera=False, bg=None):
    surf = font.render(text, True, color, bg)
    rect = surf.get_rect()
    setattr(rect, anchor, r._to_screen(pos, use_camera))
    r.surface.blit(surf, rect)
