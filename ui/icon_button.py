# ui/icon_button.py
import pygame
from typing import Callable, Optional

class IconButton:
    """
    - 사각 버튼 안에 벡터 아이콘을 그려주는 경량 위젯
    - hover/pressed/toggled 상태에 따라 배경/포커스 색 변화
    - on_click 콜백 호출
    - 토글 상태는 외부에서 get_toggled()로 주입(예: repeat 버튼)
    """
    def __init__(
        self,
        pos, size,
        on_click: Callable[[], None],
        draw_icon: Callable[[pygame.Surface, pygame.Rect, dict], None],
        *,
        radius=10,
        get_toggled: Optional[Callable[[], bool]] = None,
        tooltip: Optional[str] = None,
    ):
        self.rect = pygame.Rect(pos, size)
        self.on_click = on_click
        self.draw_icon = draw_icon
        self.radius = radius
        self.get_toggled = get_toggled
        self.tooltip = tooltip

        self._hover = False
        self._pressed = False
        self.enabled = True

        # style
        self.col_bg = (36, 39, 46)
        self.col_bg_hover = (46, 50, 58)
        self.col_bg_pressed = (28, 31, 38)
        self.col_bg_toggled = (64, 100, 170)
        self.col_border = (70, 74, 80)

    # for layout containers (optional APIs)
    def set_position(self, x, y):
        self.rect.topleft = (x, y)

    def set_size(self, w, h):
        self.rect.size = (w, h)

    def offset(self, dy):
        self.rect.move_ip(0, dy)

    # loop
    def update(self, events):
        if not self.enabled:
            return
        mx, my = pygame.mouse.get_pos()
        self._hover = self.rect.collidepoint(mx, my)
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self._hover:
                self._pressed = True
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                was_pressed = self._pressed
                self._pressed = False
                if was_pressed and self._hover:
                    if self.on_click:
                        self.on_click()

    def draw(self, surface: pygame.Surface):
        toggled = bool(self.get_toggled()) if self.get_toggled else False
        if not self.enabled:
            bg = (30, 30, 30)
        elif toggled:
            bg = self.col_bg_toggled
        elif self._pressed:
            bg = self.col_bg_pressed
        elif self._hover:
            bg = self.col_bg_hover
        else:
            bg = self.col_bg

        pygame.draw.rect(surface, bg, self.rect, border_radius=self.radius)
        pygame.draw.rect(surface, self.col_border, self.rect, width=1, border_radius=self.radius)

        inner = self.rect.inflate(-12, -12)
        state = {"hover": self._hover, "pressed": self._pressed, "toggled": toggled, "enabled": self.enabled}
        self.draw_icon(surface, inner, state)
