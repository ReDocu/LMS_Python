from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
import math
import os

import pygame

Color = Tuple[int, int, int]


@dataclass
class _BaseText:
    id: str
    text: str
    x: float
    y: float
    size: int
    color: Color
    font_alias: Optional[str]
    antialias: bool = True
    visible: bool = True
    layer: int = 0
    _surface: Optional[pygame.Surface] = field(default=None, init=False, repr=False)
    _dirty: bool = field(default=True, init=False, repr=False)

    def mark_dirty(self) -> None:
        self._dirty = True


@dataclass
class _MovingText(_BaseText):
    start: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))
    end: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))
    speed: float = 0.0  # px/sec (dt 제공시) 또는 px/frame (dt 미제공시)
    done: bool = False

    def reset(self) -> None:
        self.x, self.y = self.start
        self.done = False


class TextManager:
    def __init__(self) -> None:
        pygame.font.init()
        self._font_files: Dict[str, str] = {}
        self._font_cache: Dict[Tuple[str, int], pygame.font.Font] = {}
        self._current_font_alias: Optional[str] = None
        self._entries: Dict[str, _BaseText] = {}
        self._order: list[str] = []  # 그리기 순서 관리

    # --------------------------- Font API ---------------------------
    def SetFont(self, alias: str, font_path: str) -> None:
        """폰트 파일을 별칭(alias)에 등록하고, 이후 기본 폰트로 설정합니다.
        예: SetFont("title2", "Dongle-Light.ttf")
        """
        if not os.path.isfile(font_path):
            # 경로가 상대/절대 혼용될 수 있어, pygame의 폰트 검색은 직접 하지 않음.
            # 파일이 없다면 이후 SysFont(None)로 폴백됩니다.
            pass
        self._font_files[alias] = font_path
        self._current_font_alias = alias
        # 해당 alias로 캐시된 폰트는 크기별로 따로 만들어지므로, 지금은 파일만 등록.

    def UseFont(self, alias: str) -> None:
        """그릴 때 기본으로 사용할 폰트 alias를 전환합니다."""
        if alias not in self._font_files:
            raise KeyError(f"등록되지 않은 폰트 alias: {alias}")
        self._current_font_alias = alias

    def _get_font(self, alias: Optional[str], size: int) -> pygame.font.Font:
        alias = alias or self._current_font_alias
        key = (alias or "__sys__", size)
        if key in self._font_cache:
            return self._font_cache[key]

        if alias and alias in self._font_files and os.path.isfile(self._font_files[alias]):
            f = pygame.font.Font(self._font_files[alias], size)
        else:
            # 폴백: 시스템 기본 폰트 (한글 지원 TTF가 등록되지 않은 경우 대비)
            f = pygame.font.SysFont(None, size)
        self._font_cache[key] = f
        return f

    # --------------------------- Create / Update ---------------------------
    def SetText(
        self,
        id: str,
        x: float,
        y: float,
        text: str,
        size: int,
        color: Color,
        *,
        font_alias: Optional[str] = None,
        antialias: bool = True,
        layer: int = 0,
    ) -> None:
        """정적 텍스트 생성/갱신 (동일 id면 교체)
        
        질문의 사용 예시와 동일한 시그니처:
            SetText("intro_power", 240, 150, "Power", 24, (196,196,96))
        """
        entry = _BaseText(id=id, text=text, x=x, y=y, size=size, color=color,
                          font_alias=font_alias, antialias=antialias, layer=layer)
        self._entries[id] = entry
        if id not in self._order:
            self._order.append(id)
        entry.mark_dirty()

    def SetTextMove(
        self,
        id: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        text: str,
        size: int,
        speed: float,
        color: Color,
        *,
        font_alias: Optional[str] = None,
        antialias: bool = True,
        layer: int = 0,
        restart_if_exists: bool = True,
    ) -> None:
        """이동 텍스트 생성/갱신.
        - speed 단위: Update(dt)를 초 단위로 호출하면 px/sec. dt 미제공시 px/frame.
        - restart_if_exists=True면 동일 id가 있을 때 애니메이션을 처음부터 재시작.
        """
        entry = _MovingText(
            id=id, text=text, x=x1, y=y1, size=size, color=color,
            font_alias=font_alias, antialias=antialias, layer=layer,
            start=(x1, y1), end=(x2, y2), speed=speed,
        )
        if (not restart_if_exists) and (id in self._entries) and isinstance(self._entries[id], _MovingText):
            # 기존 진행 유지: 텍스트/색/크기만 갱신
            old = self._entries[id]
            entry.x, entry.y = old.x, old.y
        self._entries[id] = entry
        if id not in self._order:
            self._order.append(id)
        entry.mark_dirty()

    # --------------------------- Mutators ---------------------------
    def SetTextContent(self, id: str, text: str) -> None:
        e = self._entries[id]
        e.text = text
        e.mark_dirty()

    def SetTextColor(self, id: str, color: Color) -> None:
        e = self._entries[id]
        e.color = color
        e.mark_dirty()

    def SetTextSize(self, id: str, size: int) -> None:
        e = self._entries[id]
        e.size = size
        e.mark_dirty()

    def Remove(self, id: str) -> None:
        if id in self._entries:
            del self._entries[id]
        if id in self._order:
            self._order.remove(id)

    def Clear(self) -> None:
        self._entries.clear()
        self._order.clear()

    # --------------------------- Query ---------------------------
    def Exists(self, id: str) -> bool:
        return id in self._entries

    def GetRect(self, id: str) -> pygame.Rect:
        e = self._entries[id]
        surf = self._ensure_surface(e)
        r = surf.get_rect()
        r.topleft = (int(e.x), int(e.y))
        return r

    def Measure(self, text: str, size: int, font_alias: Optional[str] = None) -> Tuple[int, int]:
        f = self._get_font(font_alias, size)
        return f.size(text)

    # --------------------------- Runtime ---------------------------
    def Update(self, dt: Optional[float] = None) -> None:
        """모든 이동 텍스트를 업데이트.
        dt가 주어지면 speed=px/sec. dt가 None이면 speed=px/frame.
        """
        if dt is None:
            dt = 1.0  # 프레임 단위
        for e in self._entries.values():
            if isinstance(e, _MovingText) and not e.done:
                sx, sy = e.x, e.y
                ex, ey = e.end
                dx, dy = ex - sx, ey - sy
                dist = math.hypot(dx, dy)
                if dist == 0:
                    e.done = True
                    continue
                step = e.speed * dt
                if step >= dist:
                    e.x, e.y = ex, ey
                    e.done = True
                else:
                    nx = sx + dx / dist * step
                    ny = sy + dy / dist * step
                    e.x, e.y = nx, ny
                # 위치만 바뀌면 surface는 그대로

    def Draw(self, surface: pygame.Surface) -> None:
        # layer와 삽입 순서 기준으로 그리기 정렬
        ordered = sorted(self._order, key=lambda i: (self._entries[i].layer, self._order.index(i)))
        for id_ in ordered:
            e = self._entries[id_]
            if not e.visible:
                continue
            surf = self._ensure_surface(e)
            surface.blit(surf, (int(e.x), int(e.y)))

    # --------------------------- Internals ---------------------------
    def _ensure_surface(self, e: _BaseText) -> pygame.Surface:
        if e._surface is not None and not e._dirty:
            return e._surface
        font = self._get_font(e.font_alias, e.size)
        e._surface = font.render(e.text, e.antialias, e.color)
        e._dirty = False
        return e._surface


# ---------------------------------------------------------------------------
# 간단 데모 (직접 실행 시)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    pygame.init()
    screen = pygame.display.set_mode((960, 540))
    pygame.display.set_caption("TextManager Demo")
    clock = pygame.time.Clock()

    tm = TextManager()
    tm.SetFont("title2", "Dongle-Light.ttf")
    tm.SetText("intro_power", 40, 40, "Power", 36, (196,196,96))
    tm.SetTextMove("Stage03", -400, 200, 300, 200, "산악 지대", 54, 180, (255,128,0))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        dt = clock.get_time() / 1000.0
        tm.Update(dt)

        screen.fill((12,12,16))
        tm.Draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()
