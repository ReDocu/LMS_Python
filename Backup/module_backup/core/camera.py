# core/camera.py
import pygame
Vec2 = pygame.math.Vector2

class Camera:
    def __init__(self, pos=(0, 0), zoom=1.0):
        self.pos = Vec2(pos)    # 월드 좌표의 오프셋
        self.zoom = float(zoom) # 1.0이면 원본 크기

    def world_to_screen(self, p):
        # 카메라 적용: (월드 - 카메라) * 줌
        return (Vec2(p) - self.pos) * self.zoom

    def screen_to_world(self, p):
        return Vec2(p) / self.zoom + self.pos

    def move(self, dx, dy):
        self.pos.x += dx
        self.pos.y += dy