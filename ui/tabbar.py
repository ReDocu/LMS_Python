import pygame
from typing import Callable, List, Tuple, Optional

Color = Tuple[int,int,int]

class TabBar:
    def __init__(self, tabs, pos, size, font, on_change=None):
        self.tabs = tabs
        self.rect = pygame.Rect(pos, size)
        self.font = font
        self.on_change = on_change

        # 기본 색
        self.bg = (240, 240, 0)
        self.border = (180, 180, 180)
        self.ink = (40, 40, 40)

        # active 색
        self.active_bg = (70, 130, 180)
        self.active_ink = (255, 255, 255)

        # hover 색
        self.hover_bg = (200, 220, 240)
        self.hover_ink = (20, 20, 20)

        self.border_radius = 10
        self.active_index = 0
        self._tab_rects = []
        self._build_rects()

    def _build_rects(self):
        n = len(self.tabs)
        if n == 0: return
        tab_w = self.rect.width // n
        self._tab_rects = [pygame.Rect(self.rect.x + i*tab_w, self.rect.y, tab_w, self.rect.height) for i in range(n)]

    def set_theme(self, bg, border, ink, active_ink, active_bg):
        self.bg = bg
        self.border = border
        self.ink = ink
        self.active_ink = active_ink
        self.active_bg = active_bg

    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, r in enumerate(self._tab_rects):
                    if r.collidepoint(ev.pos):
                        self.active_index = i
                        if self.on_change: self.on_change(i)

    def draw(self, surface, special_colors=None):
        # TabBar 전체 배경
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, self.border, self.rect, width=2, border_radius=self.border_radius)

        mouse_pos = pygame.mouse.get_pos()

        for i, (tab, r) in enumerate(zip(self.tabs, self._tab_rects)):
            active = (i == self.active_index)
            hovered = r.collidepoint(mouse_pos)

            # hover/active 시 shrink 효과 (모든 탭 동일)
            draw_rect = r
            if active or hovered:
                draw_rect = r.inflate(-4, -4)

            # ---- Logout (special 색상 처리) ----
            if special_colors and tab in special_colors:
                normal, active_col = special_colors[tab]

                if active:
                    color = active_col
                    txt_color = (255, 255, 255)
                elif hovered:
                    # hover 시 normal보다 조금 밝게
                    color = tuple(min(255, c + 30) for c in normal)
                    txt_color = (255, 255, 255)
                else:
                    color = normal
                    txt_color = (255, 255, 255)

                pygame.draw.rect(surface, color, draw_rect, border_radius=8)
                txt = self.font.render(tab, True, txt_color)
                surface.blit(txt, txt.get_rect(center=draw_rect.center))

            # ---- 일반 탭 ----
            else:
                if active:
                    pygame.draw.rect(surface, self.active_bg, draw_rect, border_radius=8)
                    txt = self.font.render(tab, True, self.active_ink)
                elif hovered:
                    pygame.draw.rect(surface, self.hover_bg, draw_rect, border_radius=8)
                    txt = self.font.render(tab, True, self.hover_ink)
                else:
                    txt = self.font.render(tab, True, self.ink)

                surface.blit(txt, txt.get_rect(center=draw_rect.center))
