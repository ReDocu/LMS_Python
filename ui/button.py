import pygame
from typing import Callable, Optional, Tuple

Color = Tuple[int, int, int]

WHITE: Color = (255, 255, 255)
BLUE: Color = (70, 130, 180)
LIGHT_BLUE: Color = (100, 160, 210)
DARK_BLUE: Color = (40, 90, 140)
GRAY: Color = (180, 180, 180)

class Button:
    """
    Pygame용 재사용 버튼 위젯
    - hover / active 색상
    - on_click 콜백
    - enabled 토글
    - set_colors()로 런타임 색상 변경
    """
    def __init__(
        self,
        text: str,
        pos: Tuple[int, int],
        size: Tuple[int, int] = (160, 52),
        *,
        font: Optional[pygame.font.Font] = None,
        colors: Tuple[Color, Color, Color, Color] = (BLUE, LIGHT_BLUE, DARK_BLUE, GRAY),  # default, hover, active, disabled
        text_color: Color = WHITE,
        border_radius: int = 10,
        on_click: Optional[Callable[[], None]] = None,
        enabled: bool = True,
        elevation: bool = False,
    ) -> None:
        self.text = text
        self.rect = pygame.Rect(pos, size)
        self.font = font or pygame.font.SysFont("arial", 24)
        self.text_color = text_color
        self.border_radius = border_radius
        self.on_click = on_click
        self.enabled = enabled
        self.elevation = elevation

        # 상태 색상
        self.default_color, self.hover_color, self.active_color, self.disabled_color = colors
        self._current_color: Color = self.default_color

        # 상태 플래그
        self._is_hovered = False
        self._is_pressed = False

        # 텍스트 서피스만 캐싱 (위치는 draw 때 center로 계산)
        self._render_text()

    # ---------- public ----------
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        # disabled 즉시 반영
        if not self.enabled:
            self._current_color = self.disabled_color

    def set_on_click(self, fn: Optional[Callable[[], None]]) -> None:
        self.on_click = fn

    def set_text(self, text: str) -> None:
        self.text = text
        self._render_text()

    def set_colors(
        self,
        *,
        default: Optional[Color] = None,
        hover: Optional[Color] = None,
        active: Optional[Color] = None,
        disabled: Optional[Color] = None,
    ) -> None:
        """버튼 색상을 런타임에 변경"""
        if default is not None:
            self.default_color = default
        if hover is not None:
            self.hover_color = hover
        if active is not None:
            self.active_color = active
        if disabled is not None:
            self.disabled_color = disabled

        # 현재 상태에 맞는 색 즉시 반영
        if not self.enabled:
            self._current_color = self.disabled_color
        elif self._is_pressed:
            self._current_color = self.active_color
        elif self._is_hovered:
            self._current_color = self.hover_color
        else:
            self._current_color = self.default_color

    def draw(self, surface: pygame.Surface) -> None:
        # 본체
        pygame.draw.rect(surface, self._current_color, self.rect, border_radius=self.border_radius)

        # (옵션) 바닥 그림자
        if self.elevation and self.enabled:
            shadow_rect = self.rect.copy()
            shadow_rect.height = 4
            shadow_rect.top = self.rect.bottom - 4
            shadow_color = tuple(max(0, c - 30) for c in self._current_color)
            pygame.draw.rect(surface, shadow_color, shadow_rect, border_radius=self.border_radius)

        # 텍스트는 매 프레임 최신 center 기준으로 위치 잡기
        text_rect = self._text_surf.get_rect(center=self.rect.center)
        surface.blit(self._text_surf, text_rect)

    def update(self, events: list[pygame.event.Event]) -> None:
        """상태 업데이트 및 클릭 처리. 콜백은 여기서 호출."""
        mouse_pos = pygame.mouse.get_pos()
        self._is_hovered = self.rect.collidepoint(mouse_pos)

        # 색상 상태 결정
        if not self.enabled:
            self._current_color = self.disabled_color
            self._is_pressed = False
            return
        if self._is_pressed:
            self._current_color = self.active_color
        elif self._is_hovered:
            self._current_color = self.hover_color
        else:
            self._current_color = self.default_color

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._is_hovered and self.enabled:
                    self._is_pressed = True
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self._is_pressed and self._is_hovered and self.enabled:
                    self._is_pressed = False
                    if self.on_click:
                        self.on_click()
                self._is_pressed = False

    # ---------- internal ----------
    def _render_text(self) -> None:
        self._text_surf = self.font.render(self.text, True, self.text_color)
