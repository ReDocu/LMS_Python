#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pygame Scene Framework (단일 파일 버전)
=====================================

✔ 핵심 기능
- Scene 추상화: enter/exit/pause/resume, handle_event, update, draw
- SceneManager: push/pop/switch, 현재 Scene에 이벤트/업데이트/렌더 위임
- 전환 효과: 페이드 인/아웃(중간에 Scene 전환)
- 안정적인 메인 루프: dt(초) 기반 업데이트, 고정 FPS 제한(기본 60)
- 간단한 데모: TitleScene -> GameScene -> PauseScene

실행 방법
- `pip install pygame`
- `python pygame-scene-framework.py`

모듈 분리 가이드
- 실제 프로젝트에서는 아래 "# --- 파일 분리 예시 ---" 주석을 따라 core/, scenes/ 등으로 나누면 됩니다.

작성자: ChatGPT (GPT-5 Thinking)
"""
from __future__ import annotations
import sys
import pygame as pg
from typing import Optional, List, Type

# =============================================================
# 유틸 & 타입
# =============================================================
Color = tuple[int, int, int]

# =============================================================
# Scene 추상 클래스
# =============================================================
class Scene:
    """모든 Scene이 상속해야 하는 기본 클래스.

    수명주기 콜백:
      - enter(manager): Scene이 스택에 올라올 때 1회 호출
      - exit(): Scene이 스택에서 제거될 때 1회 호출
      - pause(): 다른 Scene이 push되어 비활성화 될 때 호출
      - resume(): 위의 Scene이 pop되어 다시 활성화될 때 호출

    메인 루프 콜백:
      - handle_event(event): 입력 이벤트 처리
      - update(dt): 논리 업데이트 (dt: 초)
      - draw(surface): 렌더링
    """
    def __init__(self) -> None:
        self.manager: Optional[SceneManager] = None

    # 수명주기 -------------------------------------------------
    def enter(self, manager: "SceneManager") -> None:
        self.manager = manager

    def exit(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def resume(self) -> None:
        pass

    # 루프 콜백 ------------------------------------------------
    def handle_event(self, event: pg.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pg.Surface) -> None:
        pass

# =============================================================
# 페이드 전환 컨트롤러
# =============================================================
class FadeTransition:
    """검은 오버레이로 페이드 인/아웃을 수행하며, 중간 지점에서 Scene을 교체.

    duration: 전체 전환 시간(초). 절반은 페이드 아웃, 나머지 절반은 페이드 인.
    on_midpoint: 중간(절반 경과) 지점에서 호출되는 콜백(보통 scene switch).
    """
    def __init__(self, duration: float, on_midpoint) -> None:
        self.duration = max(0.001, duration)
        self.half = self.duration * 0.5
        self.on_midpoint = on_midpoint
        self.t = 0.0
        self.done_mid = False
        self.finished = False

    def update(self, dt: float) -> None:
        if self.finished:
            return
        self.t += dt
        if not self.done_mid and self.t >= self.half:
            self.done_mid = True
            self.on_midpoint()
        if self.t >= self.duration:
            self.finished = True

    def draw(self, surface: pg.Surface) -> None:
        if self.finished:
            return
        # 0 -> half: alpha 0 -> 255 (페이드 아웃), half -> end: 255 -> 0 (페이드 인)
        if self.t <= self.half:
            alpha = int((self.t / self.half) * 255)
        else:
            alpha = int((1.0 - (self.t - self.half) / self.half) * 255)
        overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, max(0, min(255, alpha))))
        surface.blit(overlay, (0, 0))

# =============================================================
# SceneManager
# =============================================================
class SceneManager:
    def __init__(self, screen: pg.Surface) -> None:
        self.screen = screen
        self.scenes: List[Scene] = []
        self.transition: Optional[FadeTransition] = None

    # 스택 조작 -----------------------------------------------
    def push(self, scene: Scene) -> None:
        if self.scenes:
            self.scenes[-1].pause()
        self.scenes.append(scene)
        scene.enter(self)

    def pop(self) -> None:
        if not self.scenes:
            return
        top = self.scenes.pop()
        top.exit()
        if self.scenes:
            self.scenes[-1].resume()

    def switch(self, scene: Scene) -> None:
        # top 교체
        if self.scenes:
            old = self.scenes.pop()
            old.exit()
        self.scenes.append(scene)
        scene.enter(self)

    def switch_with_fade(self, scene_factory: Type[Scene] | Scene, duration: float = 0.6) -> None:
        """페이드 전환과 함께 scene 교체. scene_factory는 클래스타입 또는 인스턴스.
        """
        def do_switch():
            scene = scene_factory() if isinstance(scene_factory, type) else scene_factory
            self.switch(scene)
        self.transition = FadeTransition(duration, do_switch)

    # 루프 위임 -----------------------------------------------
    def handle_event(self, event: pg.event.Event) -> None:
        if self.scenes:
            self.scenes[-1].handle_event(event)

    def update(self, dt: float) -> None:
        if self.scenes:
            self.scenes[-1].update(dt)
        if self.transition:
            self.transition.update(dt)
            if self.transition.finished:
                self.transition = None

    def draw(self) -> None:
        if self.scenes:
            self.scenes[-1].draw(self.screen)
        if self.transition:
            self.transition.draw(self.screen)

# =============================================================
# 데모용 Scene들
# =============================================================
class TitleScene(Scene):
    def __init__(self) -> None:
        super().__init__()
        self.title_font: Optional[pg.font.Font] = None
        self.ui_font: Optional[pg.font.Font] = None
        self.blink_t = 0.0
        self.show_press = True

    def enter(self, manager: SceneManager) -> None:
        super().enter(manager)
        self.title_font = pg.font.SysFont("malgungothic", 64) or pg.font.Font(None, 64)
        self.ui_font = pg.font.SysFont("malgungothic", 24) or pg.font.Font(None, 24)

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_RETURN, pg.K_SPACE):
                # 페이드 전환으로 게임으로 이동
                self.manager.switch_with_fade(GameScene, duration=0.8)
            elif event.key == pg.K_ESCAPE:
                pg.event.post(pg.event.Event(pg.QUIT))

    def update(self, dt: float) -> None:
        self.blink_t += dt
        if self.blink_t >= 0.6:
            self.blink_t = 0.0
            self.show_press = not self.show_press

    def draw(self, surface: pg.Surface) -> None:
        surface.fill((18, 18, 24))
        w, h = surface.get_size()
        title = self.title_font.render("My Pygame Framework", True, (240, 240, 255))
        surface.blit(title, title.get_rect(center=(w//2, h//2 - 80)))
        if self.show_press:
            press = self.ui_font.render("Press ENTER/SPACE to Start", True, (200, 200, 210))
            surface.blit(press, press.get_rect(center=(w//2, h//2 + 10)))
        hint = self.ui_font.render("ESC to Quit", True, (140, 140, 150))
        surface.blit(hint, hint.get_rect(center=(w//2, h - 40)))

class GameScene(Scene):
    def __init__(self) -> None:
        super().__init__()
        self.player_pos = pg.Vector2(200, 200)
        self.player_vel = pg.Vector2(0, 0)
        self.speed = 280.0  # px/s
        self.bg_color: Color = (30, 32, 40)
        self.font: Optional[pg.font.Font] = None
        self.t = 0.0

    def enter(self, manager: SceneManager) -> None:
        super().enter(manager)
        self.font = pg.font.SysFont("malgungothic", 20) or pg.font.Font(None, 20)

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                # 일시정지 Scene을 push
                self.manager.push(PauseScene())

    def update(self, dt: float) -> None:
        keys = pg.key.get_pressed()
        self.player_vel.xy = 0, 0
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            self.player_vel.x = -1
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            self.player_vel.x = 1
        if keys[pg.K_UP] or keys[pg.K_w]:
            self.player_vel.y = -1
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            self.player_vel.y = 1
        if self.player_vel.length_squared() > 0:
            self.player_vel = self.player_vel.normalize() * self.speed
        self.player_pos += self.player_vel * dt
        self.t += dt

    def draw(self, surface: pg.Surface) -> None:
        surface.fill(self.bg_color)
        # 움직이는 원을 플레이어로 가정
        pg.draw.circle(surface, (90, 200, 255), self.player_pos, 22)
        # 화면 테두리
        pg.draw.rect(surface, (60, 70, 90), surface.get_rect(), 2)
        # HUD
        hud = self.font.render("ESC = Pause | Move = WASD/Arrows", True, (220, 230, 240))
        surface.blit(hud, (12, 10))

class PauseScene(Scene):
    def __init__(self) -> None:
        super().__init__()
        self.font_big: Optional[pg.font.Font] = None
        self.font_small: Optional[pg.font.Font] = None

    def enter(self, manager: SceneManager) -> None:
        super().enter(manager)
        self.font_big = pg.font.SysFont("malgungothic", 48) or pg.font.Font(None, 48)
        self.font_small = pg.font.SysFont("malgungothic", 22) or pg.font.Font(None, 22)

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_ESCAPE, pg.K_p):
                self.manager.pop()  # 게임으로 복귀
            elif event.key == pg.K_q:
                # 바로 타이틀로 전환(페이드)
                self.manager.switch_with_fade(TitleScene, duration=0.6)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pg.Surface) -> None:
        # 아래 Scene(GameScene)이 이미 그려진 상태라고 가정하지 않고
        # 안전하게 현재 SceneManager의 바로 아래 Scene을 요청하는 대신,
        # 일시정지 화면만 그리되, 투명 오버레이로 처리.
        # (실전에서는 SceneManager가 "아래 Scene 먼저 그리기"를 지원하도록 바꿔도 좋습니다.)
        surface.fill((0, 0, 0))
        w, h = surface.get_size()
        # 반투명 오버레이
        overlay = pg.Surface((w, h), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        # 텍스트
        text = self.font_big.render("PAUSED", True, (245, 245, 255))
        tip1 = self.font_small.render("ESC/P = Resume", True, (230, 230, 235))
        tip2 = self.font_small.render("Q = Quit to Title (Fade)", True, (230, 230, 235))
        surface.blit(text, text.get_rect(center=(w//2, h//2 - 20)))
        surface.blit(tip1, tip1.get_rect(center=(w//2, h//2 + 30)))
        surface.blit(tip2, tip2.get_rect(center=(w//2, h//2 + 58)))

# =============================================================
# GameApp
# =============================================================
class GameApp:
    def __init__(self, size=(960, 600), title: str = "Pygame Scene Framework", fps: int = 60) -> None:
        pg.init()
        pg.display.set_caption(title)
        self.screen = pg.display.set_mode(size)
        self.clock = pg.time.Clock()
        self.fps = fps
        self.manager = SceneManager(self.screen)
        self.running = True

    def run(self, first_scene: Optional[Scene] = None) -> None:
        if first_scene is None:
            first_scene = TitleScene()
        self.manager.push(first_scene)

        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0  # 초 단위
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                    break
                elif event.type == pg.KEYDOWN and event.key == pg.K_F11:
                    pg.display.toggle_fullscreen()
                else:
                    self.manager.handle_event(event)

            self.manager.update(dt)
            self.manager.draw()
            pg.display.flip()

        pg.quit()
        sys.exit(0)

# =============================================================
# 엔트리 포인트
# =============================================================
if __name__ == "__main__":
    app = GameApp(size=(1024, 640), title="My Pygame Framework", fps=60)
    app.run()

# =============================================================
# --- 파일 분리 예시 (권장 구조) ---
#
# project_root/
#   main.py                        -> GameApp 실행/설정
#   core/
#     scene.py                     -> Scene 추상 클래스
#     scene_manager.py             -> SceneManager & FadeTransition
#     transitions.py               -> 다른 전환 효과(슬라이드, 크로스페이드 등)
#   scenes/
#     title_scene.py               -> TitleScene
#     game_scene.py                -> GameScene
#     pause_scene.py               -> PauseScene
#   assets/
#     fonts/... images/...         -> 리소스
#   ui/ (옵션)
#     widgets.py                   -> 버튼/라벨 등 공용 위젯
#
# 각 파일 내용은 본 단일 파일의 대응 클래스를 복사해 나누면 됩니다.
# =============================================================
