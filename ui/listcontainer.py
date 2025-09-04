# ui/listcontainer.py
import pygame

class ListContainer:
    """
    - 내부 패딩/간격 기준 자동 레이아웃
    - add/clear 시 즉시 레이아웃(첫 프레임 0,0 번쩍임 방지)
    - 자식이 update()/draw() 있으면 자동 호출
    - 자식이 rect 또는 set_position/set_size를 가지면 위치/폭 자동 보정
    - 스크롤(마우스 휠/드래그) + 스크롤바 표시
    """
    def __init__(self, pos, size, *, padding=(12,12), gap=8, bg=None, border=None, radius=8, scroll=True):
        self.rect = pygame.Rect(pos, size)
        self.padding = padding
        self.gap = gap
        self.widgets = []
        self.bg = bg
        self.border = border
        self.radius = radius

        # layout/scroll state
        self._layout_dirty = True
        self._content_h = 0
        self._scroll_y = 0
        self._scroll_enabled = scroll
        self._dragging = False
        self._drag_start_y = 0
        self._scroll_start = 0

        # style
        self._scroll_track = (0, 0, 0, 60)     # 반투명 트랙
        self._scroll_thumb = (180, 180, 180)   # 썸

    # ---------- theme ----------
    def set_theme(self, *, bg=None, border=None, scroll_thumb=None):
        if bg is not None: self.bg = bg
        if border is not None: self.border = border
        if scroll_thumb is not None: self._scroll_thumb = scroll_thumb

    # ---------- children ----------
    def add(self, widget):
        self.widgets.append(widget)
        self._relayout()

    def add_many(self, widgets):
        self.widgets.extend(widgets)
        self._relayout()

    def remove(self, widget):
        if widget in self.widgets:
            self.widgets.remove(widget)
            self._relayout()

    def clear(self):
        self.widgets.clear()
        self._relayout()

    # ---------- layout ----------
    def _relayout(self):
        x0 = self.rect.x + self.padding[0]
        y  = self.rect.y + self.padding[1]
        inner_w = self.rect.width - self.padding[0]*2

        ymax = y
        for wdg in self.widgets:
            # 높이
            h = getattr(getattr(wdg, "rect", None), "height", 40)

            # 우선 set_position/set_size 호출
            if hasattr(wdg, "set_position"):
                wdg.set_position(x0, y)
            if hasattr(wdg, "set_size"):
                wdg.set_size(inner_w, h)

            # fallback로 rect도 보정
            if hasattr(wdg, "rect"):
                wdg.rect.topleft = (x0, y)
                wdg.rect.width = min(wdg.rect.width, inner_w)
                h = wdg.rect.height

            y += h + self.gap
            ymax = y

        self._content_h = max(0, ymax - (self.rect.y + self.padding[1]))
        self._layout_dirty = False

        # 스크롤 범위 보정
        self._clamp_scroll()

    def layout_now(self):
        self._relayout()

    def _clamp_scroll(self):
        if not self._scroll_enabled:
            self._scroll_y = 0
            return
        max_scroll = max(0, self._content_h - (self.rect.height - self.padding[1]*2))
        self._scroll_y = max(0, min(self._scroll_y, max_scroll))

    # ---------- loop ----------
    def update(self, events):
        if self._layout_dirty:
            self._relayout()

        # 스크롤 입력 처리
        if self._scroll_enabled and self._content_h > (self.rect.height - self.padding[1]*2):
            for ev in events:
                if ev.type == pygame.MOUSEWHEEL:
                    # 일반 휠: 한 칸당 40px
                    self._scroll_y -= ev.y * 40
                    self._clamp_scroll()
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # 스크롤바 드래그 시작 체크
                    if self._hit_scroll_thumb(pygame.mouse.get_pos()):
                        self._dragging = True
                        self._drag_start_y = pygame.mouse.get_pos()[1]
                        self._scroll_start = self._scroll_y
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    self._dragging = False
                elif ev.type == pygame.MOUSEMOTION and self._dragging:
                    dy = pygame.mouse.get_pos()[1] - self._drag_start_y
                    # 썸 이동량 -> 컨텐츠 스크롤로 변환
                    view_h = self.rect.height - self.padding[1]*2
                    max_scroll = max(1, self._content_h - view_h)
                    thumb_h = max(24, int(view_h * (view_h / self._content_h)))
                    track_h = view_h - thumb_h
                    ratio = max_scroll / max(1, track_h)
                    self._scroll_y = self._scroll_start + dy * ratio
                    self._clamp_scroll()

        # 자식 업데이트(스크롤 보정: y를 일시적으로 이동)
        dy = -self._scroll_y
        for w in self.widgets:
            if hasattr(w, "offset"):
                w.offset(dy)
                if hasattr(w, "update"):
                    w.update(events)
                w.offset(-dy)
            else:
                if hasattr(w, "rect"):
                    w.rect.move_ip(0, dy)
                if hasattr(w, "update"):
                    w.update(events)
                if hasattr(w, "rect"):
                    w.rect.move_ip(0, -dy)

    def draw(self, surface):
        # 배경/외곽
        if self.bg is not None:
            pygame.draw.rect(surface, self.bg, self.rect, border_radius=self.radius)
        if self.border is not None:
            pygame.draw.rect(surface, self.border, self.rect, width=2, border_radius=self.radius)

        # 클리핑
        old_clip = surface.get_clip()
        surface.set_clip(self.rect)

        # 자식 그리기(스크롤 보정)
        dy = -self._scroll_y
        for w in self.widgets:
            if hasattr(w, "offset"):
                w.offset(dy)
                if hasattr(w, "draw"):
                    w.draw(surface)
                w.offset(-dy)
            else:
                if hasattr(w, "rect"):
                    w.rect.move_ip(0, dy)
                if hasattr(w, "draw"):
                    w.draw(surface)
                if hasattr(w, "rect"):
                    w.rect.move_ip(0, -dy)
        
        # 스크롤바
        if self._scroll_enabled and self._content_h > (self.rect.height - self.padding[1]*2):
            self._draw_scrollbar(surface)

        # 클립 복원
        surface.set_clip(old_clip)

    # ---------- scrollbar ----------
    def _draw_scrollbar(self, surface):
        view_h = self.rect.height - self.padding[1]*2
        max_scroll = max(1, self._content_h - view_h)
        # 트랙
        track = pygame.Rect(self.rect.right - 8, self.rect.y + self.padding[1], 4, view_h)
        trk = pygame.Surface(track.size, pygame.SRCALPHA); trk.fill(self._scroll_track)
        surface.blit(trk, track.topleft)
        # 썸
        thumb_h = max(24, int(view_h * (view_h / self._content_h)))
        track_h = view_h - thumb_h
        thumb_y = track.y + int((self._scroll_y / max_scroll) * track_h)
        thumb = pygame.Rect(track.x, thumb_y, 4, thumb_h)
        pygame.draw.rect(surface, self._scroll_thumb, thumb, border_radius=2)

    def _hit_scroll_thumb(self, pos):
        view_h = self.rect.height - self.padding[1]*2
        if self._content_h <= view_h:
            return False
        max_scroll = max(1, self._content_h - view_h)
        track = pygame.Rect(self.rect.right - 8, self.rect.y + self.padding[1], 4, view_h)
        thumb_h = max(24, int(view_h * (view_h / self._content_h)))
        track_h = view_h - thumb_h
        thumb_y = track.y + int((self._scroll_y / max_scroll) * track_h)
        thumb = pygame.Rect(track.x, thumb_y, 4, thumb_h)
        return thumb.collidepoint(pos)
