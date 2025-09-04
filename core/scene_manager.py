import pygame
from typing import Optional, Set

class Scene:
    def __init__(self, app):
        self.app = app

    def enter(self, **kwargs): pass
    def exit(self): pass
    def handle_events(self, events): pass
    def update(self, dt): pass
    def draw(self, screen): pass


class SceneManager:
    """
    - add(scene) / remove(scene) / has(scene): 등록/해제/조회
    - switch(scene, with_fade=True, **kwargs): 페이드 전환(아웃→인)
    - set_fade(duration): 페이드 시간 조절
    - is_transitioning: 전환 중 여부
    * 기존 페이드 구현의 동작은 그대로 유지
    """
    def __init__(self):
        self.current: Optional[Scene] = None
        self._registry: Set[Scene] = set()

        # --- fade state ---
        self._phase = "idle"     # idle | fading_out | fading_in
        self._alpha = 0.0
        self._dur = 0.35         # seconds
        self._next_scene: Optional[Scene] = None
        self._next_kwargs = {}

    # ---------- registry ----------
    def add(self, scene: Scene) -> None:
        """씬을 레지스트리에 추가 (enter 호출 안 함)."""
        self._registry.add(scene)

    def remove(self, scene: Scene) -> None:
        """레지스트리에서 제거. 현재 씬이면 exit() 후 해제."""
        if scene is self.current:
            try:
                scene.exit()
            finally:
                self.current = None
                self._phase = "idle"
                self._alpha = 0.0
        self._registry.discard(scene)

    def has(self, scene: Scene) -> bool:
        return scene in self._registry

    # ---------- config ----------
    def set_fade(self, duration: float) -> None:
        """페이드 지속시간(초). 0 또는 음수면 즉시 전환처럼 동작."""
        self._dur = max(0.0, float(duration))

    @property
    def is_transitioning(self) -> bool:
        return self._phase != "idle"

    # ---------- switching ----------
    def switch(self, scene: Scene, with_fade: bool = True, **kwargs) -> None:
        """
        씬 전환.
        - with_fade=True: 페이드 아웃 → 인
        - False: 즉시 전환
        레지스트리에 없으면 자동으로 add() 해서 사용 가능하도록 함.
        """
        if scene not in self._registry:
            self.add(scene)

        # 페이드 없이 즉시 전환하거나, 아직 current가 없는 첫 진입이면 즉시 전환
        if (not with_fade) or (self.current is None) or self._dur <= 0.0:
            if self.current:
                self.current.exit()
            self.current = scene
            self.current.enter(**kwargs)
            self._phase, self._alpha = "idle", 0.0
            return

        # 페이드 아웃부터 시작
        self._next_scene = scene
        self._next_kwargs = kwargs
        self._phase = "fading_out"
        self._alpha = 0.0  # 0 -> 255

    # ---------- external loop API ----------
    def handle_events(self, events) -> None:
        # 전환 중엔 입력 막기
        if self._phase != "idle":
            return
        if self.current:
            self.current.handle_events(events)

    def update(self, dt: float) -> None:
        if self._phase == "idle":
            if self.current:
                self.current.update(dt)
            return

        # 페이드 스텝 계산 (0~255 범위 보장)
        step = 255.0 * (dt / max(self._dur, 1e-6))

        if self._phase == "fading_out":
            self._alpha += step
            if self._alpha >= 255.0:
                self._alpha = 255.0
                # 장면 스위치
                if self.current:
                    self.current.exit()
                self.current = self._next_scene
                if self.current:
                    self.current.enter(**self._next_kwargs)
                self._phase = "fading_in"

        elif self._phase == "fading_in":
            self._alpha -= step
            if self._alpha <= 0.0:
                self._alpha = 0.0
                self._phase = "idle"

        # 전환 중에는 새로 들어온 씬만 최소 업데이트(페이드 인 동안)
        if self.current and self._phase == "fading_in":
            self.current.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        if self.current:
            self.current.draw(screen)

        if self._phase != "idle":
            # 알파 오버레이
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            # clamp 후 int로
            a = max(0, min(255, int(self._alpha)))
            overlay.fill((0, 0, 0, a))
            screen.blit(overlay, (0, 0))
