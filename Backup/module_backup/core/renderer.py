# core/renderer.py
import pygame
from typing import Optional, Tuple
from .camera import Camera

Color = Tuple[int, int, int]

class Renderer:
    def __init__(self, surface: pygame.Surface, camera: Optional[Camera] = None):
        self.surface = surface
        self.camera = camera

    def set_camera(self, cam: Camera):
        self.camera = cam

    # ----- 기본 유틸 -----
    def clear(self, color: Color=(0, 0, 0)):
        self.surface.fill(color)

    def _to_screen(self, pos, use_camera=True):
        if self.camera and use_camera:
            return self.camera.world_to_screen(pos)
        return pygame.math.Vector2(pos)

    def blit(self, image: pygame.Surface, pos, use_camera=True):
        p = self._to_screen(pos, use_camera)
        self.surface.blit(image, p)

    def blit_center(self, image: pygame.Surface, center, use_camera=True):
        p = self._to_screen(center, use_camera)
        rect = image.get_rect(center=(p.x, p.y))
        self.surface.blit(image, rect)

    def draw_rect(self, color: Color, rect, width=0, use_camera=True):
        # rect는 월드 기준. 카메라/줌 반영
        if self.camera and use_camera:
            tl = self.camera.world_to_screen((rect[0], rect[1]))
            w, h = rect[2]*self.camera.zoom, rect[3]*self.camera.zoom
            pygame.draw.rect(self.surface, color, (tl.x, tl.y, w, h), width)
        else:
            pygame.draw.rect(self.surface, color, rect, width)

    def draw_circle(self, color: Color, center, radius, width=0, use_camera=True):
        p = self._to_screen(center, use_camera)
        r = int(radius*(self.camera.zoom if (self.camera and use_camera) else 1))
        pygame.draw.circle(self.surface, color, (int(p.x), int(p.y)), r, width)

    def draw_line(self, color: Color, start_pos, end_pos, width=1, use_camera=True):
        a = self._to_screen(start_pos, use_camera)
        b = self._to_screen(end_pos, use_camera)
        pygame.draw.line(self.surface, color, a, b, width)