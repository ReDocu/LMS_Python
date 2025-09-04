import pygame
from typing import Optional, Tuple

# ---------- minimal clipboard helpers (scrap -> pyperclip fallback) ----------
_HAS_SCRAP = False
try:
    import pygame.scrap as _scrap
    _HAS_SCRAP = True
except Exception:
    _scrap = None
    _HAS_SCRAP = False

try:
    import pyperclip as _pyperclip
    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False

def _clip_init_if_needed():
    if _HAS_SCRAP:
        try:
            if not _scrap.get_init():
                _scrap.init()
        except Exception:
            pass

def _clip_set(text: str):
    _clip_init_if_needed()
    if _HAS_SCRAP:
        try:
            _scrap.put(_scrap.SCRAP_TEXT, text.encode("utf-8"))
            return
        except Exception:
            pass
    if _HAS_PYPERCLIP:
        try:
            _pyperclip.copy(text)
            return
        except Exception:
            pass

def _clip_get() -> str:
    _clip_init_if_needed()
    if _HAS_SCRAP:
        try:
            raw = _scrap.get(_scrap.SCRAP_TEXT)
            if raw:
                try:
                    return raw.decode("utf-8")
                except Exception:
                    return raw.decode(errors="ignore")
        except Exception:
            pass
    if _HAS_PYPERCLIP:
        try:
            return _pyperclip.paste() or ""
        except Exception:
            pass
    return ""

# ---------- TextBox ----------
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
    - Ctrl+A/C/X/V (전체 선택/복사/잘라내기/붙여넣기)
      * 선택 영역 UI는 없지만 내부적으로 전체 선택만 지원
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
        self.caret = 0
        self.scroll_px = 0
        self._blink_visible = True
        self._blink_ms = 500
        self._last_blink_t = pygame.time.get_ticks()

        self._last_click_time = 0
        self._dbl_ms = 350   # 더블클릭 인식 시간(밀리초) — 300~400 추천

        # "전체 선택" 상태 (Ctrl+A 적용 시 True) — 시각 표시 없이 로직만
        self._select_all = False

    # ---------- Public API ----------
    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text
        self.caret = min(len(self.text), self.caret)
        self._select_all = False
        self._ensure_caret_visible()

    def set_focus(self, focus: bool) -> None:
        self.focused = focus
        self._reset_blink()
        if not focus:
            self._select_all = False

    # ---------- Event / Update ----------
    def update(self, events) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                inside = self.rect.collidepoint(ev.pos)
                self.focused = inside
                if inside:
                    now = pygame.time.get_ticks()
                    if now - self._last_click_time <= self._dbl_ms:
                        # --- 더블 클릭: 내용 지우기 ---
                        self.text = ""
                        self.caret = 0
                        self.scroll_px = 0
                        self._select_all = False if hasattr(self, "_select_all") else False
                        self._reset_blink()
                    else:
                        # 일반 클릭: 캐럿 이동
                        self.caret = self._pos_to_index(ev.pos[0])
                        self._select_all = False if hasattr(self, "_select_all") else False
                        self._reset_blink()
                    self._last_click_time = now
                continue

            if not self.focused:
                continue

            # 유니코드 입력 (한글 포함)
            if ev.type == pygame.TEXTINPUT:
                if (self.max_chars is None) or (len(self.text) < self.max_chars):
                    # 전체선택 상태면 덮어쓰기
                    if self._select_all:
                        self.text = ""
                        self.caret = 0
                        self._select_all = False
                    self._insert_text(ev.text)
                    self._reset_blink()

            elif ev.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl = bool(mods & pygame.KMOD_CTRL)

                if ctrl:
                    # Ctrl 조합 처리
                    if ev.key == pygame.K_a:
                        # 전체 선택
                        self._select_all = True
                        self.caret = len(self.text)
                        self._ensure_caret_visible()
                        self._reset_blink()
                        continue
                    if ev.key == pygame.K_c:
                        # 복사
                        if self._select_all:
                            _clip_set(self.text)
                        else:
                            _clip_set(self.text)  # 선택 UI 없음 → 전체 복사
                        continue
                    if ev.key == pygame.K_x:
                        # 잘라내기
                        _clip_set(self.text)
                        self.text = ""
                        self.caret = 0
                        self._select_all = False
                        self._ensure_caret_visible()
                        self._reset_blink()
                        continue
                    if ev.key == pygame.K_v:
                        # 붙여넣기
                        paste = _clip_get()
                        if paste:
                            if self._select_all:
                                self.text = ""
                                self.caret = 0
                                self._select_all = False
                            if (self.max_chars is None) or (len(self.text) + len(paste) <= self.max_chars):
                                self._insert_text(paste)
                            else:
                                # 남는 만큼만
                                remain = max(0, self.max_chars - len(self.text)) if self.max_chars is not None else len(paste)
                                if remain > 0:
                                    self._insert_text(paste[:remain])
                            self._reset_blink()
                        continue
                    # 다른 Ctrl+키는 아래 기본 이동/삭제 로직으로

                # 일반 편집 키
                if ev.key == pygame.K_BACKSPACE:
                    if self._select_all:
                        self.text = ""
                        self.caret = 0
                        self._select_all = False
                    elif self.caret > 0:
                        self.text = self.text[:self.caret-1] + self.text[self.caret:]
                        self.caret -= 1
                    self._ensure_caret_visible()
                    self._reset_blink()

                elif ev.key == pygame.K_DELETE:
                    if self._select_all:
                        self.text = ""
                        self.caret = 0
                        self._select_all = False
                    elif self.caret < len(self.text):
                        self.text = self.text[:self.caret] + self.text[self.caret+1:]
                    self._ensure_caret_visible()
                    self._reset_blink()

                elif ev.key == pygame.K_LEFT:
                    self._select_all = False
                    if self.caret > 0:
                        self.caret -= 1
                    self._ensure_caret_visible()
                    self._reset_blink()

                elif ev.key == pygame.K_RIGHT:
                    self._select_all = False
                    if self.caret < len(self.text):
                        self.caret += 1
                    self._ensure_caret_visible()
                    self._reset_blink()

                elif ev.key == pygame.K_HOME:
                    self._select_all = False
                    self.caret = 0
                    self._ensure_caret_visible()
                    self._reset_blink()

                elif ev.key == pygame.K_END:
                    self._select_all = False
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

        draw_text = ("•" * len(self.text)) if self.password else self.text
        text_surf = self.font.render(draw_text, True, self.text_color)

        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        surface.blit(text_surf, (clip_rect.x - self.scroll_px, clip_rect.y + (clip_rect.height - text_surf.get_height()) // 2))

        # placeholder (포커스 없고 비어있을 때)
        if not self.text and not self.focused and self.placeholder:
            ph = self.font.render(self.placeholder, True, self.placeholder_color)
            surface.blit(ph, (clip_rect.x, clip_rect.y + (clip_rect.height - ph.get_height()) // 2))

        # 캐럿
        if self.focused and self._blink_visible and not self._select_all:
            caret_x = clip_rect.x - self.scroll_px + self._text_width(draw_text[:self.caret])
            caret_y = clip_rect.y + 6
            caret_h = clip_rect.height - 12
            pygame.draw.rect(surface, self.text_color, pygame.Rect(caret_x, caret_y, 2, caret_h))

        surface.set_clip(old_clip)

    # ---------- Internal ----------
    def _insert_text(self, s: str) -> None:
        self.text = self.text[:self.caret] + s + self.text[self.caret:]
        self.caret += len(s)
        self._ensure_caret_visible()

    def _text_width(self, s: str) -> int:
        return 0 if not s else self.font.size(s)[0]

    def _pos_to_index(self, x_screen: int) -> int:
        """마우스 x좌표를 텍스트 인덱스로 변환"""
        clip_x = self.rect.x + self.padding_x
        local_x = x_screen - clip_x + self.scroll_px
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
