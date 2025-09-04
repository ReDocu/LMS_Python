import pygame

from typing import Optional, Tuple

Color = Tuple[int, int, int]

WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)
GRAY: Color = (180, 180, 180)
DARK_GRAY: Color = (120, 120, 120)
BLUE: Color = (70, 130, 180)
LIGHT_BLUE: Color = (100, 160, 210)

class TextBox:
    """
    Pygame TextBox 위젯
    - 유니코드 입력 (pygame.TEXTINPUT)
    - 커서 깜빡임, 좌우/홈/엔드, Backspace/Delete
    - 길어질 때 수평 스크롤
    - placeholder 지원
    """
    def __init__(
        self,
        pos: Tuple[int, int],
        size: Tuple[int, int] = (260, 44),
        *,
        font: Optional[pygame.font.Font] = None,
        text_color: Color = BLACK,
        bg_color: Color = WHITE,
        border_color: Color = DARK_GRAY,
        border_color_hover: Color = LIGHT_BLUE,
        border_color_focus: Color = BLUE,
        border_radius: int = 10,
        padding_x: int = 10,
        placeholder: str = "",
        placeholder_color: Color = GRAY,
        max_chars: Optional[int] = None,
        password: bool = False,
    ) -> None:
        self.rect = pygame.Rect(pos, size)
        self.font = font or pygame.font.SysFont("arial", 24)
        self.text_color = text_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_color_hover = border_color_hover
        self.border_color_focus = border_color_focus
        self.border_radius = border_radius
        self.padding_x = padding_x
        self.placeholder = placeholder
        self.placeholder_color = placeholder_color
        self.max_chars = max_chars
        self.password = password

        self.text = ""
        self.focused = False
        self.hovered = False

        # 캐럿/스크롤
        self.caret = 0                     # 텍스트 내 인덱스
        self.scroll_px = 0                 # 왼쪽으로 스크롤된 픽셀
        self._blink_visible = True
        self._blink_ms = 500               # 깜빡임 주기
        self._last_blink_t = pygame.time.get_ticks()

    # ---------- Public API ----------
    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text
        self.caret = min(len(self.text), self.caret)
        self._ensure_caret_visible()

    def set_focus(self, focus: bool) -> None:
        self.focused = focus
        self._reset_blink()

    # ---------- Event / Update ----------
    def update(self, events) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.focused = self.rect.collidepoint(ev.pos)
                if self.focused:
                    # 클릭 위치로 캐럿 이동
                    self.caret = self._pos_to_index(ev.pos[0])
                    self._reset_blink()
                continue

            if not self.focused:
                continue

            # 유니코드 입력 (한글 포함)
            if ev.type == pygame.TEXTINPUT:
                if (self.max_chars is None) or (len(self.text) < self.max_chars):
                    self._insert_text(ev.text)
                    self._reset_blink()

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_BACKSPACE:
                    if self.caret > 0:
                        self.text = self.text[:self.caret-1] + self.text[self.caret:]
                        self.caret -= 1
                        self._ensure_caret_visible()
                        self._reset_blink()
                elif ev.key == pygame.K_DELETE:
                    if self.caret < len(self.text):
                        self.text = self.text[:self.caret] + self.text[self.caret+1:]
                        self._ensure_caret_visible()
                        self._reset_blink()
                elif ev.key == pygame.K_LEFT:
                    if self.caret > 0:
                        self.caret -= 1
                        self._ensure_caret_visible()
                        self._reset_blink()
                elif ev.key == pygame.K_RIGHT:
                    if self.caret < len(self.text):
                        self.caret += 1
                        self._ensure_caret_visible()
                        self._reset_blink()
                elif ev.key == pygame.K_HOME:
                    self.caret = 0
                    self._ensure_caret_visible()
                    self._reset_blink()
                elif ev.key == pygame.K_END:
                    self.caret = len(self.text)
                    self._ensure_caret_visible()
                    self._reset_blink()

        # 커서 깜빡임
        now = pygame.time.get_ticks()
        if now - self._last_blink_t >= self._blink_ms:
            self._blink_visible = not self._blink_visible
            self._last_blink_t = now

    # ---------- Draw ----------
    def draw(self, surface: pygame.Surface) -> None:
        # 배경 + 보더
        border_col = self.border_color_focus if self.focused else (self.border_color_hover if self.hovered else self.border_color)
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, border_col, self.rect, width=2, border_radius=self.border_radius)

        # 그릴 영역(클리핑)
        clip_rect = self.rect.inflate(-2, -2).copy()
        clip_rect.x += self.padding_x
        clip_rect.width -= (self.padding_x * 2)

        # 텍스트/플레이스홀더 렌더
        draw_text = ("•" * len(self.text)) if self.password else self.text
        text_surf = self.font.render(draw_text, True, self.text_color)
        # 스크롤 보정 후 그리기
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        surface.blit(text_surf, (clip_rect.x - self.scroll_px, clip_rect.y + (clip_rect.height - text_surf.get_height()) // 2))

        # 플레이스홀더
        if not self.text and not self.focused and self.placeholder:
            ph = self.font.render(self.placeholder, True, self.placeholder_color)
            surface.blit(ph, (clip_rect.x, clip_rect.y + (clip_rect.height - ph.get_height()) // 2))

        # 캐럿
        if self.focused and self._blink_visible:
            caret_x = clip_rect.x - self.scroll_px + self._text_width(draw_text[:self.caret])
            caret_y = clip_rect.y + 6
            caret_h = clip_rect.height - 12
            pygame.draw.rect(surface, self.text_color, pygame.Rect(caret_x, caret_y, 2, caret_h))

        surface.set_clip(old_clip)

    # ---------- Internal ----------
    def _insert_text(self, s: str) -> None:
        # max_chars 체크는 호출부에서
        self.text = self.text[:self.caret] + s + self.text[self.caret:]
        self.caret += len(s)
        self._ensure_caret_visible()

    def _text_width(self, s: str) -> int:
        if not s:
            return 0
        return self.font.size(s)[0]

    def _pos_to_index(self, x_screen: int) -> int:
        """마우스 x좌표를 텍스트 인덱스로 변환"""
        clip_x = self.rect.x + self.padding_x
        local_x = x_screen - clip_x + self.scroll_px
        # 문자를 하나씩 폭 합산해서 근사 인덱스
        draw_text = ("•" * len(self.text)) if self.password else self.text
        acc = 0
        for i, ch in enumerate(draw_text):
            w = self._text_width(ch)
            if local_x < acc + w / 2:
                return i
            acc += w
        return len(draw_text)

    def _ensure_caret_visible(self) -> None:
        """캐럿이 보이도록 scroll_px 조정"""
        clip_inner_w = self.rect.width - self.padding_x * 2
        draw_text = ("•" * len(self.text)) if self.password else self.text
        caret_px = self._text_width(draw_text[:self.caret])

        if caret_px - self.scroll_px > clip_inner_w:
            self.scroll_px = caret_px - clip_inner_w
        elif caret_px - self.scroll_px < 0:
            self.scroll_px = caret_px

        self.scroll_px = max(0, self.scroll_px)

    def _reset_blink(self) -> None:
        self._blink_visible = True
        self._last_blink_t = pygame.time.get_ticks()
