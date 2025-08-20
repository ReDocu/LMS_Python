# modules/background.py
import pygame
from typing import List, Tuple, Optional

Vec2 = pygame.math.Vector2
Surface = pygame.Surface

class CameraProto:
    pos: Vec2
    zoom: float

class BackgroundLayer:
    def __init__(self, depth: int = 0):
        self.depth = depth  # 낮을수록 뒤쪽(먼 배경)

    def update(self, dt: float, camera: CameraProto): ...
    def render(self, surface: Surface, camera: CameraProto): ...

class ColorLayer(BackgroundLayer):
    def __init__(self, color: Tuple[int,int,int], depth: int = -10_000):
        super().__init__(depth)
        self.color = color

    def render(self, surface: Surface, camera: CameraProto):
        surface.fill(self.color)

class TiledImageLayer(BackgroundLayer):
    """
    무한 타일링 + 패럴랙스 + 자가 스크롤
    parallax=(0..1): 0은 카메라 영향 거의 없음(하늘), 1은 월드와 동기
    """
    def __init__(
        self,
        image: Surface,
        parallax: Tuple[float, float] = (0.5, 0.0),
        scroll_speed: Tuple[float, float] = (0.0, 0.0),
        depth: int = 0,
        alpha: Optional[int] = None
    ):
        super().__init__(depth)
        self.tex = image.convert_alpha()
        if alpha is not None:
            self.tex.set_alpha(alpha)
        self.tw, self.th = self.tex.get_size()
        self.parallax = Vec2(parallax)
        self.scroll_speed = Vec2(scroll_speed)
        self.offset = Vec2(0, 0)  # 자가 스크롤 누적

    def update(self, dt: float, camera: CameraProto):
        self.offset += self.scroll_speed * dt

    def render(self, surface: Surface, camera: CameraProto):
        sw, sh = surface.get_size()

        # 카메라 시차 오프셋(카메라가 +x로 가면 배경은 -x로 보임)
        par = Vec2(
            -camera.pos.x * self.parallax.x,
            -camera.pos.y * self.parallax.y
        )
        total = self.offset + par

        # 시작 타일 정렬
        start_x = int(total.x) % self.tw - self.tw
        start_y = int(total.y) % self.th - self.th

        x = start_x
        while x < sw:
            y = start_y
            while y < sh:
                surface.blit(self.tex, (x, y))
                y += self.th
            x += self.tw

class ScreenSpaceImageLayer(BackgroundLayer):
    """카메라 무시하고 화면 기준으로 그리는 레이어(비네트/노이즈/UI 장식 등)"""
    def __init__(self, image: Surface, pos=(0,0), depth: int = 10_000, alpha: Optional[int] = None):
        super().__init__(depth)
        self.image = image.convert_alpha()
        if alpha is not None:
            self.image.set_alpha(alpha)
        self.pos = pos

    def render(self, surface: Surface, camera: CameraProto):
        surface.blit(self.image, self.pos)

class BackgroundManager:
    def __init__(self):
        self.layers: List[BackgroundLayer] = []
        self._dirty = True

    def add(self, layer: BackgroundLayer):
        self.layers.append(layer)
        self._dirty = True

    def _sort(self):
        if self._dirty:
            self.layers.sort(key=lambda L: L.depth)
            self._dirty = False

    def update(self, dt: float, camera: CameraProto):
        self._sort()
        for L in self.layers:
            L.update(dt, camera)

    def render(self, surface: Surface, camera: CameraProto):
        self._sort()
        for L in self.layers:
            L.render(surface, camera)
