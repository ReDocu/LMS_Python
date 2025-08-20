# modules/camera.py
import pygame
Vec2 = pygame.math.Vector2

class Camera:
    """
    월드 좌표계를 스크린 좌표로 바꿔주는 작고 강한 카메라.
    - pos: 카메라의 월드 위치(왼쪽-위 모서리라고 생각하면 편함)
    - zoom: 배율(1.0 = 원본, 2.0 = 2배 확대)
    """
    def __init__(self, pos=(0, 0), zoom=1.0):
        self.pos = Vec2(pos)
        self.zoom = float(zoom)

    def world_to_screen(self, p) -> Vec2:
        return (Vec2(p) - self.pos) * self.zoom

    def screen_to_world(self, p) -> Vec2:
        return Vec2(p) / self.zoom + self.pos

    def move(self, dx: float, dy: float):
        self.pos.x += dx
        self.pos.y += dy
