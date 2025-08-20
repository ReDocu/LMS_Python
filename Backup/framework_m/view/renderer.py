# view/renderer.py
import pygame
from typing import Optional, Tuple
from modules.camera import Camera

Color = Tuple[int, int, int]

class Renderer:
    """
    모든 그리기의 '입구' 역할.
    - surface: pygame 화면
    - camera : 월드↔스크린 변환 담당(없으면 UI 전용처럼 동작)
    """
    def __init__(self, surface: pygame.Surface, camera: Optional[Camera] = None):
        self.surface = surface
        self.camera = camera

    def clear(self, color: Color = (0, 0, 0)):
        self.surface.fill(color)

    # 내부 공용: 카메라 적용 좌표
    def _to_screen(self, pos, use_camera: bool):
        if self.camera and use_camera:
            return self.camera.world_to_screen(pos)
        return pygame.math.Vector2(pos)

    # --- 기본 그리기 ---
    def blit(self, image: pygame.Surface, pos, *, use_camera=True, anchor="topleft"):
        p = self._to_screen(pos, use_camera)
        rect = image.get_rect()
        setattr(rect, anchor, (p.x, p.y))
        self.surface.blit(image, rect)

    def draw_rect(self, color: Color, rect, width=0, *, use_camera=True):
        if self.camera and use_camera:
            tl = self.camera.world_to_screen((rect[0], rect[1]))
            w = rect[2] * (self.camera.zoom if use_camera else 1)
            h = rect[3] * (self.camera.zoom if use_camera else 1)
            pygame.draw.rect(self.surface, color, (tl.x, tl.y, w, h), width)
        else:
            pygame.draw.rect(self.surface, color, rect, width)

    def draw_line(self, color: Color, a, b, width=1, *, use_camera=True):
        a2 = self._to_screen(a, use_camera)
        b2 = self._to_screen(b, use_camera)
        pygame.draw.line(self.surface, color, a2, b2, width)

    def draw_circle(self, color: Color, center, radius, width=0, *, use_camera=True):
        c = self._to_screen(center, use_camera)
        r = int(radius * (self.camera.zoom if (self.camera and use_camera) else 1))
        pygame.draw.circle(self.surface, color, (int(c.x), int(c.y)), r, width)
