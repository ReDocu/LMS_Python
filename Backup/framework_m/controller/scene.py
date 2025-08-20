# controller/scene.py
import pygame
from typing import List, Optional
from modules.camera import Camera
from model.assets_model import AssetsModel
from view.renderer import Renderer
from view.gfx_images import draw_image
from view.gfx_text import draw_text
from view.gfx_shapes import rect as draw_rect

from modules.input import InputMap, Move, Zoom, ToggleVignette
from modules.background import BackgroundManager, ColorLayer, TiledImageLayer, ScreenSpaceImageLayer

# ===== 공통 인터페이스 =====
class Scene:
    def __init__(self, model: AssetsModel, renderer: Renderer, camera: Camera):
        self.model = model
        self.renderer = renderer
        self.camera = camera

    def handle_event(self, e: pygame.event.Event): ...
    def update(self, dt: float): ...
    def render(self): ...

# ===== 스택형 씬 매니저 =====
class SceneManager:
    def __init__(self):
        self.stack: List[Scene] = []

    def push(self, scene: Scene): self.stack.append(scene)
    def pop(self): 
        if self.stack: self.stack.pop()
    def current(self) -> Optional[Scene]:
        return self.stack[-1] if self.stack else None

    def handle_event(self, e):
        cur = self.current()
        if cur: cur.handle_event(e)

    def update(self, dt: float):
        cur = self.current()
        if cur: cur.update(dt)

    def render(self):
        cur = self.current()
        if cur: cur.render()


# ===== 데모 씬 =====
class DemoScene(Scene):
    def __init__(self, model, renderer, camera):
        super().__init__(model, renderer, camera)

        # --- 배경 설정 (기존과 동일) ---
        self.bg = BackgroundManager()
        # ... (생성 코드 동일) ...
        vignette = pygame.Surface(self.renderer.surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0,0,0,70), vignette.get_rect())
        self.vignette_layer = ScreenSpaceImageLayer(vignette, (0, 0), depth=9999)
        self.show_vignette = True

        self.bg.add(ColorLayer((8, 12, 20), depth=-10_000))
        # 주의: scroll_speed 오타 수정!
        # self.bg.add(TiledImageLayer(near_tex, parallax=(0.80, 0.00), scroll_speed(-25, 0), depth=-100))
        # 올바른 코드:
        # self.bg.add(TiledImageLayer(near_tex, parallax=(0.80, 0.00), scroll_speed=(-25, 0), depth=-100))
        # ...나머지 레이어 추가...
        self.bg.add(self.vignette_layer)

        # --- 에셋/플레이어 (기존과 동일) ---
        # ...

        # --- 입력 바인딩 ---
        self.input = InputMap()\
            .bind_hold(pygame.K_a, Move(-1,  0))\
            .bind_hold(pygame.K_d, Move( 1,  0))\
            .bind_hold(pygame.K_w, Move( 0, -1))\
            .bind_hold(pygame.K_s, Move( 0,  1))\
            .bind_hold(pygame.K_q, Zoom(-0.5))\
            .bind_hold(pygame.K_e, Zoom(+0.5))\
            .bind_down(pygame.K_v, ToggleVignette())

    def handle_event(self, e):
        self.input.handle_event(e, self)

    def update(self, dt):
        # 키 홀드 처리(프레임마다)
        self.input.tick(self, dt)

        # 카메라 추적
        W, H = self.renderer.surface.get_size()
        self.camera.pos.xy = (
            self.pos.x - W/2 / max(0.0001, self.camera.zoom),
            self.pos.y - H/2 / max(0.0001, self.camera.zoom)
        )
        self.bg.update(dt, self.camera)

    def render(self):
        r = self.renderer
        self.bg.render(r.surface, self.camera)

        # 월드/플레이어/UI (기존 동일)
        # 비네트 토글 반영
        self.vignette_layer.image.set_alpha(70 if self.show_vignette else 0)
