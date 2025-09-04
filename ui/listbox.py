import pygame
from typing import Callable, Iterable, List, Optional, Tuple, Union

Color = Tuple[int, int, int]
Index = int

WHITE: Color = (255, 255, 255)
BLACK: Color = (25, 25, 25)
BG: Color = (248, 249, 252)
BORDER: Color = (190, 190, 190)
HOVER: Color = (230, 236, 245)
SELECTED: Color = (70, 130, 180)
SELECTED_TEXT: Color = (255, 255, 255)
SCROLL_BG: Color = (235, 235, 235)
SCROLL_FG: Color = (160, 160, 160)

class ListBox:
    """
    Pygame ListBox 위젯
    - 마우스: 클릭 선택, 더블클릭 제출, 휠 스크롤
    - 키보드: ↑/↓/Home/End/PgUp/PgDn 이동, Enter 제출 (포커스 필요)
    - 단일/멀티 선택 지원(multi_select=True)
    - on_change(idx|[idx...]), on_submit(idx|[idx...]) 콜백
    """
    def __init__(
        self,
        pos: Tuple[int, int],
        size: Tuple[int, int],
        items: Iterable[str],
        *,
        font: Optional[pygame.font.Font] = None,
        item_height: int = 28,
        multi_select: bool = False,
        border_radius: int = 10,
        on_change: Optional[Callable[[Union[Index, List[Index]]], None]] = None,
        on_submit: Optional[Callable[[Union[Index, List[Index]]], None]] = None,
    ) -> None:
        self.rect = pygame.Rect(pos, size)
        self.font = font or pygame.font.SysFont("arial", 22)
        self.item_height = item_height
        self.border_radius = border_radius
        self.multi_select = multi_select
        self.on_change = on_change
        self.on_submit = on_submit

        self.items: List[str] = list(items)
        self.top_index: int = 0
        self.hover_row: Optional[int] = None
        self.focused: bool = False

        self.selected: Union[Optional[Index], List[Index]]
        self.selected = [] if multi_select else None

        # 더블클릭 인식
        self._last_click_time = 0
        self._last_click_row: Optional[int] = None
        self._dbl_ms = 250

    # ---------- Public API ----------
    def set_items(self, items: Iterable[str]) -> None:
        self.items = list(items)
        self.top_index = 0
        if self.multi_select:
            self.selected = []
        else:
            self.selected = None
        self._fire_change()

    def get_selected(self) -> Union[Optional[Index], List[Index]]:
        return self.selected

    def set_focus(self, focus: bool) -> None:
        self.focused = focus

    # ---------- Event / Update ----------
    def update(self, events: list[pygame.event.Event]) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.hover_row = None

        # 가시 영역
        rows_visible = max(1, self.rect.height // self.item_height)
        max_top = max(0, len(self.items) - rows_visible)
        if self.top_index > max_top:
            self.top_index = max_top

        # hover 계산
        if self.rect.collidepoint(mouse_pos):
            local_y = mouse_pos[1] - self.rect.y
            row = local_y // self.item_height
            if 0 <= row < rows_visible and self.top_index + row < len(self.items):
                self.hover_row = row

        for ev in events:
            # 포커스 얻기
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 2):
                self.focused = self.rect.collidepoint(ev.pos)

            # 휠 스크롤
            if ev.type == pygame.MOUSEWHEEL:
                if self.rect.collidepoint(mouse_pos):
                    self.top_index = max(0, min(max_top, self.top_index - ev.y))

            # 클릭 선택/더블클릭
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
                row = (ev.pos[1] - self.rect.y) // self.item_height
                idx = self.top_index + row
                if 0 <= idx < len(self.items):
                    self._select_index(idx, ctrl=pygame.key.get_mods() & pygame.KMOD_CTRL)
                    # 더블클릭 체크
                    now = pygame.time.get_ticks()
                    if self._last_click_row == row and (now - self._last_click_time) <= self._dbl_ms:
                        self._fire_submit()
                    self._last_click_row = row
                    self._last_click_time = now

            # 키보드 이동/제출
            if ev.type == pygame.KEYDOWN and self.focused:
                if ev.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_HOME, pygame.K_END, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                    self._handle_nav_key(ev.key)
                elif ev.key == pygame.K_RETURN:
                    self._fire_submit()

    # ---------- Draw ----------
    def draw(self, surface: pygame.Surface) -> None:
        # 배경/보더
        pygame.draw.rect(surface, WHITE, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, BORDER, self.rect, width=2, border_radius=self.border_radius)

        clip = surface.get_clip()
        surface.set_clip(self.rect)

        rows_visible = max(1, self.rect.height // self.item_height)
        for i in range(rows_visible):
            idx = self.top_index + i
            if idx >= len(self.items):
                break

            row_rect = pygame.Rect(self.rect.x, self.rect.y + i * self.item_height, self.rect.width, self.item_height)

            # 행 배경 (hover / selected)
            is_hover = (self.hover_row == i)
            is_selected = (idx in self.selected) if self.multi_select else (self.selected == idx)

            if is_selected:
                pygame.draw.rect(surface, SELECTED, row_rect)
            elif is_hover:
                pygame.draw.rect(surface, HOVER, row_rect)

            # 텍스트
            txt = self.font.render(self.items[idx], True, SELECTED_TEXT if is_selected else BLACK)
            surface.blit(txt, (row_rect.x + 10, row_rect.y + (self.item_height - txt.get_height()) // 2))

            # 행 구분선
            pygame.draw.line(surface, (235, 235, 235), (row_rect.x, row_rect.bottom - 1), (row_rect.right, row_rect.bottom - 1))

        # 스크롤바
        total = len(self.items)
        if total > rows_visible:
            track = pygame.Rect(self.rect.right - 8, self.rect.y + 4, 6, self.rect.height - 8)
            pygame.draw.rect(surface, SCROLL_BG, track, border_radius=3)
            ratio = rows_visible / total
            thumb_h = max(20, int(track.height * ratio))
            top_ratio = (self.top_index / (total - rows_visible))
            thumb_y = track.y + int((track.height - thumb_h) * top_ratio)
            thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
            pygame.draw.rect(surface, SCROLL_FG, thumb, border_radius=3)

        surface.set_clip(clip)

        # 포커스 테두리
        if self.focused:
            pygame.draw.rect(surface, (120, 160, 220), self.rect, width=2, border_radius=self.border_radius)

    # ---------- Internal ----------
    def _select_index(self, idx: int, *, ctrl: bool = False) -> None:
        if self.multi_select:
            sel: List[int] = list(self.selected)  # type: ignore
            if ctrl:
                if idx in sel:
                    sel.remove(idx)
                else:
                    sel.append(idx)
                self.selected = sorted(sel)
            else:
                self.selected = [idx]
        else:
            if self.selected == idx:
                # 단일 선택은 동일 항목 재클릭 시 그대로 둠 (토글 원하면 여기서 None 처리)
                pass
            else:
                self.selected = idx
        self._ensure_visible(idx)
        self._fire_change()

    def _ensure_visible(self, idx: int) -> None:
        rows_visible = max(1, self.rect.height // self.item_height)
        if idx < self.top_index:
            self.top_index = idx
        elif idx >= self.top_index + rows_visible:
            self.top_index = idx - rows_visible + 1
        self.top_index = max(0, min(self.top_index, max(0, len(self.items) - rows_visible)))

    def _handle_nav_key(self, key: int) -> None:
        rows_visible = max(1, self.rect.height // self.item_height)
        # 현재 기준 인덱스
        cur = None
        if self.multi_select:
            if self.selected:
                cur = self.selected[-1]
        else:
            cur = self.selected if self.selected is not None else None

        if cur is None:
            cur = 0 if self.items else None

        if cur is None:
            return

        if key == pygame.K_UP:
            cur = max(0, cur - 1)
        elif key == pygame.K_DOWN:
            cur = min(len(self.items) - 1, cur + 1)
        elif key == pygame.K_HOME:
            cur = 0
        elif key == pygame.K_END:
            cur = len(self.items) - 1
        elif key == pygame.K_PAGEUP:
            cur = max(0, cur - rows_visible)
        elif key == pygame.K_PAGEDOWN:
            cur = min(len(self.items) - 1, cur + rows_visible)

        if self.multi_select:
            self.selected = [cur]
        else:
            self.selected = cur
        self._ensure_visible(cur)
        self._fire_change()

    def _fire_change(self) -> None:
        if self.on_change:
            self.on_change(self.selected if self.multi_select else self.selected)

    def _fire_submit(self) -> None:
        if self.on_submit:
            self.on_submit(self.selected if self.multi_select else self.selected)
