# scenes/music_manager_scene.py
from __future__ import annotations
import pygame
from pathlib import Path
import csv
from datetime import datetime

from core.scene_manager import Scene
from ui.listcontainer import ListContainer
from ui.icon_button import IconButton

# ====== 리스트 아이템 ======
class TrackItem:
    def __init__(self, label: str, index: int, on_click, font: pygame.font.Font, h=36):
        self.label = label
        self.index = index
        self.on_click = on_click
        self.font = font
        self.rect = pygame.Rect(0, 0, 200, h)
        self._hover = False
        self._selected = False
        self._last_click_time = 0
        self._dbl_ms = 300

        self.col_bg = (28, 30, 34)
        self.col_bg_hover = (38, 42, 48)
        self.col_bg_sel = (60, 88, 140)
        self.col_text = (220, 220, 230)
        self.col_text_sel = (255, 255, 255)

    def set_position(self, x, y): self.rect.topleft = (x, y)
    def set_size(self, w, h): self.rect.size = (w, h)
    def set_selected(self, yes: bool): self._selected = yes
    def offset(self, dy): self.rect.move_ip(0, dy)

    def _ellipsize(self, text, max_w):
        if self.font.size(text)[0] <= max_w:
            return text
        ell = "…"
        left, right = 0, len(text)
        while left < right:
            mid = (left + right) // 2
            if self.font.size(text[:mid] + ell)[0] <= max_w:
                left = mid + 1
            else:
                right = mid
        return text[:max(0, left-1)] + ell

    def update(self, events):
        mx, my = pygame.mouse.get_pos()
        self._hover = self.rect.collidepoint(mx, my)
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self._hover:
                now = pygame.time.get_ticks()
                dbl = (now - self._last_click_time) <= self._dbl_ms
                self._last_click_time = now
                self.on_click(self.index, dbl_click=dbl)

    def draw(self, surface):
        bg = self.col_bg_sel if self._selected else (self.col_bg_hover if self._hover else self.col_bg)
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pad = 10
        max_w = self.rect.width - pad * 2
        txt = self._ellipsize(self.label, max_w)
        col = self.col_text_sel if self._selected else self.col_text
        ts = self.font.render(txt, True, col)
        surface.blit(ts, (self.rect.x + pad, self.rect.y + (self.rect.height - ts.get_height()) // 2))


# ====== 메인 씬 ======
class MusicManagerScene(Scene):
    """
    좌측 리스트 + 중앙 컨트롤 바(이전/플레이·일시정지/다음/반복) + 진행바 + 시간·볼륨 지정
    조작:
      - Enter: 재생  Space: 일시정지/해제  R: 처음부터
      - ↑/↓: 선택 이동  ←/→: 이전/다음
      - L: 반복 토글
      - 진행바 클릭/드래그: 탐색
      - 시간 박스 클릭 후 mm:ss 입력 + Enter: 해당 위치로 점프
      - 볼륨 슬라이더 드래그/휠 또는 볼륨 박스 클릭 후 숫자% 입력 + Enter
      - 키보드 +- : 볼륨 5% 씩 조절, [ / ] : -5s / +5s 점프
    """
    def __init__(self, app):
        super().__init__(app)
        self.font = None
        self.small = None

        self.items = []         # [{'key': str, 'path': Path, 'name': str}]
        self.idx = 0
        self.volume = 0.7
        self.paused = False
        self.auto_next = True
        self.repeat_one = True

        # 길이/진행
        self._current_length: float | None = None  # seconds

        # UI
        self.left_w = 420
        self.list_container: ListContainer | None = None
        self._widgets: list[TrackItem] = []
        self.buttons: list[IconButton] = []

        # 진행/볼륨 영역 Rect (draw에서 계산, event에서 사용)
        self._progress_rect = pygame.Rect(0,0,0,0)
        self._time_box_rect = pygame.Rect(0,0,0,0)
        self._vol_rect = pygame.Rect(0,0,0,0)
        self._vol_knob_rect = pygame.Rect(0,0,0,0)

        # 입력 상태
        self._drag_progress = False
        self._drag_volume = False

        self._time_edit = False
        self._time_str = ""   # "mm:ss" 혹은 "ss"

        self._vol_edit = False
        self._vol_str = ""    # "0~100"

        # (다음 단계 용) 로그/이름
        self.mainname_mode = "before_underscore"
        self.log_path = Path("assets/audio/_classification_log.csv")

    # ---------- lifecycle ----------
    def enter(self, **kwargs):
        if not pygame.mixer.get_init():
            try: pygame.mixer.init()
            except pygame.error as e: print("[MusicManager] mixer.init 실패:", e)

        self.font = pygame.font.SysFont(None, 28)
        self.small = pygame.font.SysFont(None, 22)

        assets = self.app.get("assets")
        if assets is None:
            raise RuntimeError("app['assets']가 없습니다. AssetRegistry를 main에서 app에 넣어주세요.")
        if not assets.audio:
            assets.preload()

        rows = []
        for k in assets.list_audio():
            p = assets.get_audio_path(k)
            if p and p.exists():
                rows.append({"key": k, "path": Path(p), "name": Path(p).name})
        rows.sort(key=lambda r: r["name"].lower())
        self.items = rows
        self.idx = min(self.idx, max(0, len(self.items) - 1))

        # 좌측 리스트
        w, h = self.app["screen"].get_size()
        self.list_container = ListContainer(
            (12, 12), (self.left_w, h - 24),
            padding=(8, 8), gap=6, bg=(24, 26, 30), border=(70, 74, 80), radius=10, scroll=True
        )
        self._build_list_widgets()
        self._build_controls()

        if self.items:
            self._play_current()

    def exit(self):
        try: pygame.mixer.music.stop()
        except pygame.error: pass

    # ---------- UI build ----------
    def _build_list_widgets(self):
        if not self.list_container: return
        self.list_container.clear(); self._widgets.clear()
        for i, itm in enumerate(self.items):
            wdg = TrackItem(itm["name"], i, self._on_item_clicked, self.font, h=34)
            wdg.set_selected(i == self.idx)
            self._widgets.append(wdg)
        self.list_container.add_many(self._widgets)
        self.list_container.layout_now()

    def _build_controls(self):
        self.buttons.clear()

        def draw_prev(surf, rect, st):
            bar = pygame.Rect(rect.left, rect.top, max(2, rect.width//8), rect.height)
            pygame.draw.rect(surf, (235,235,240), bar, border_radius=2)
            pts = [(rect.right-4, rect.top+4), (rect.centerx, rect.centery), (rect.right-4, rect.bottom-4)]
            pygame.draw.polygon(surf, (235,235,240), pts)

        def draw_play(surf, rect, st):
            if self.paused:
                pts = [(rect.left+6, rect.top+4), (rect.right-6, rect.centery), (rect.left+6, rect.bottom-4)]
                pygame.draw.polygon(surf, (235,235,240), pts)
            else:
                bar_w = max(4, rect.width//6)
                r1 = pygame.Rect(rect.left+8, rect.top+4, bar_w, rect.height-8)
                r2 = pygame.Rect(rect.right-8-bar_w, rect.top+4, bar_w, rect.height-8)
                pygame.draw.rect(surf, (235,235,240), r1, border_radius=2)
                pygame.draw.rect(surf, (235,235,240), r2, border_radius=2)

        def draw_next(surf, rect, st):
            pts = [(rect.left+4, rect.top+4), (rect.centerx, rect.centery), (rect.left+4, rect.bottom-4)]
            pygame.draw.polygon(surf, (235,235,240), pts)
            bar = pygame.Rect(rect.right - max(2, rect.width//8), rect.top, max(2, rect.width//8), rect.height)
            pygame.draw.rect(surf, (235,235,240), bar, border_radius=2)

        def draw_repeat(surf, rect, st):
            col = (255,255,255) if st.get("toggled") else (220,220,220)
            pad = 6
            r = rect.inflate(-pad*2, -pad*2)
            pygame.draw.arc(surf, col, r, 3.5, 6.0, width=3)
            arrow1 = [(r.right, r.centery-6), (r.right+8, r.centery), (r.right, r.centery+6)]
            pygame.draw.polygon(surf, col, arrow1)
            pygame.draw.arc(surf, col, r, 0.5, 3.0, width=3)
            arrow2 = [(r.left, r.centery+6), (r.left-8, r.centery), (r.left, r.centery-6)]
            pygame.draw.polygon(surf, col, arrow2)

        y = self._controls_y()
        size = (60, 60); gap = 14
        x0 = self.left_w + 24

        self.btn_prev   = IconButton((x0, y), size, self._prev, draw_prev)
        self.btn_play   = IconButton((x0+(size[0]+gap), y), size, self._toggle_pause, draw_play)
        self.btn_next   = IconButton((x0+(size[0]+gap)*2, y), size, self._next, draw_next)
        self.btn_repeat = IconButton((x0+(size[0]+gap)*3, y), size, self._toggle_repeat, draw_repeat, get_toggled=lambda: self.repeat_one)
        self.buttons = [self.btn_prev, self.btn_play, self.btn_next, self.btn_repeat]

    def _controls_y(self):
        return self.app["screen"].get_height() // 2 - 30

    def _refresh_selection_highlight(self):
        for i, wdg in enumerate(self._widgets):
            wdg.set_selected(i == self.idx)

    def _scroll_item_into_view(self, i: int):
        lc = self.list_container
        if not lc or i < 0 or i >= len(self._widgets): return
        item = self._widgets[i]
        view_top = lc.rect.y + lc.padding[1]
        view_h = lc.rect.height - lc.padding[1]*2
        view_bot = view_top + view_h
        y = item.rect.y - lc._scroll_y
        if y < view_top:
            lc._scroll_y -= (view_top - y) + 4; lc._clamp_scroll()
        elif y + item.rect.height > view_bot:
            lc._scroll_y += (y + item.rect.height - view_bot) + 4; lc._clamp_scroll()

    # ---------- item click ----------
    def _on_item_clicked(self, index: int, dbl_click: bool):
        self.idx = index
        self._refresh_selection_highlight()
        self._scroll_item_into_view(self.idx)
        if dbl_click: self._play_current()

    # ---------- events ----------
    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app["running"] = False

            # --- 텍스트 입력 우선 처리 (시간/볼륨 편집 중) ---
            if ev.type == pygame.KEYDOWN and (self._time_edit or self._vol_edit):
                if ev.key == pygame.K_ESCAPE:
                    self._time_edit = False; self._vol_edit = False
                elif ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
                    if self._time_edit:
                        self._apply_time_input()
                    if self._vol_edit:
                        self._apply_volume_input()
                    self._time_edit = False; self._vol_edit = False
                elif ev.key == pygame.K_BACKSPACE:
                    if self._time_edit and self._time_str:
                        self._time_str = self._time_str[:-1]
                    if self._vol_edit and self._vol_str:
                        self._vol_str = self._vol_str[:-1]
                else:
                    ch = ev.unicode
                    if self._time_edit:
                        # 허용: 숫자와 콜론
                        if ch.isdigit() or ch == ":":
                            self._time_str += ch
                    if self._vol_edit:
                        # 허용: 숫자 (0~100)
                        if ch.isdigit():
                            self._vol_str += ch
                continue  # 편집 중이면 다른 키 처리 스킵

            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER): self._play_current()
                elif ev.key == pygame.K_SPACE: self._toggle_pause()
                elif ev.key == pygame.K_RIGHT: self._next()
                elif ev.key == pygame.K_LEFT: self._prev()
                elif ev.key == pygame.K_r: self._restart()
                elif ev.key == pygame.K_UP: self._move_selection(-1)
                elif ev.key == pygame.K_DOWN: self._move_selection(+1)
                elif ev.key == pygame.K_l: self._toggle_repeat()
                elif ev.key in (pygame.K_EQUALS, pygame.K_PLUS): self._set_volume(self.volume + 0.05)
                elif ev.key == pygame.K_MINUS: self._set_volume(self.volume - 0.05)
                elif ev.key == pygame.K_LEFTBRACKET: self._nudge_time(-5.0)
                elif ev.key == pygame.K_RIGHTBRACKET: self._nudge_time(+5.0)

            # 마우스 조작
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                # 진행바 클릭 → 탐색 시작(드래그 지원)
                if self._progress_rect.collidepoint(ev.pos):
                    self._drag_progress = True
                    self._seek_by_click(ev.pos[0])
                # 시간 박스 클릭 → 편집 모드
                elif self._time_box_rect.collidepoint(ev.pos):
                    self._time_edit = True
                    self._time_str = ""  # 비워두고 새로 입력 (원하면 현재 시간으로 초기화 가능)
                # 볼륨 박스 클릭 → 편집 모드
                elif self._vol_label_rect.collidepoint(ev.pos):
                    self._vol_edit = True
                    self._vol_str = ""
                # 볼륨 슬라이더 클릭/드래그
                elif self._vol_rect.collidepoint(ev.pos):
                    self._drag_volume = True
                    self._apply_volume_from_mouse(ev.pos[0])

            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self._drag_progress = False
                self._drag_volume = False

            elif ev.type == pygame.MOUSEMOTION:
                if self._drag_progress:
                    self._seek_by_click(ev.pos[0])
                if self._drag_volume:
                    self._apply_volume_from_mouse(ev.pos[0])

            elif ev.type == pygame.MOUSEWHEEL:
                # 볼륨 슬라이더 위에서 휠 → 5% 조절
                mx, my = pygame.mouse.get_pos()
                if self._vol_rect.collidepoint((mx, my)) or self._vol_label_rect.collidepoint((mx, my)):
                    self._set_volume(self.volume + ev.y * 0.05)

        if self.list_container: self.list_container.update(events)
        for b in self.buttons: b.update(events)

    # ---------- update / draw ----------
    def update(self, dt: float):
        try: busy = pygame.mixer.music.get_busy()
        except pygame.error: busy = False
        if self.auto_next and (not self.paused) and (not busy) and self.items and (not self.repeat_one):
            self._next()

    def draw(self, screen: pygame.Surface):
        screen.fill((18, 20, 22))
        w, h = screen.get_size()

        if self.list_container:
            if (self.list_container.rect.height != h - 24):
                self.list_container.rect.height = h - 24
                self.list_container.layout_now()
            self.list_container.draw(screen)

        pad = 20
        x_right = self.left_w + 24
        header = self.font.render("Music Manager", True, (230, 230, 230))
        screen.blit(header, (x_right, 20))

        if self.items:
            cur = self.items[self.idx]
            line1 = self.small.render(f"[{self.idx+1}/{len(self.items)}] {cur['name']}", True, (200, 220, 255))
            state = "PAUSED" if self.paused else "PLAYING"
            rep = "Repeat: ON" if self.repeat_one else "Repeat: OFF"
            line2 = self.small.render(f"{state}  Vol: {self.volume*100:3.0f}%  {rep}", True, (180,180,180))
            screen.blit(line1, (x_right, 56))
            screen.blit(line2, (x_right, 80))
        else:
            empty = self.small.render("assets/audio 에 오디오가 없습니다.", True, (255,180,180))
            screen.blit(empty, (x_right, 56))

        # 버튼
        y = self._controls_y()
        total_w = len(self.buttons) * 60 + (len(self.buttons)-1) * 14
        for i, b in enumerate(self.buttons):
            b.set_position(x_right + i * (60 + 14), y)
            b.set_size(60, 60)
            b.draw(screen)

        # 진행바 + 시간 + 볼륨 레이아웃
        left_x = x_right + total_w + 24
        right_margin = 24
        available_w = max(320, w - left_x - right_margin)

        # 고정폭: 진행바 420, 시간박스 86, 볼륨슬라이더 160 (공간 부족 시 진행바를 줄임)
        time_w = 86
        vol_w = 160
        min_bar_w = 220
        bar_w = max(min_bar_w, available_w - time_w - vol_w - 24 - 40)
        bar_h = 10
        bar_x = left_x
        bar_y = y + 25
        self._progress_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)

        # 진행바
        pygame.draw.rect(screen, (50, 54, 62), self._progress_rect, border_radius=6)
        elapsed = max(0, self._get_elapsed_sec())
        length = self._current_length or 0.0
        ratio = 0.0 if length <= 0 else max(0.0, min(1.0, elapsed / length))
        fill = self._progress_rect.copy(); fill.width = int(self._progress_rect.width * ratio)
        pygame.draw.rect(screen, (100, 170, 240), fill, border_radius=6)

        # 시간 박스 (좌: 편집 입력, 우: 총 길이)
        self._time_box_rect = pygame.Rect(self._progress_rect.right + 8, bar_y-6, time_w, 22)
        pygame.draw.rect(screen, (40, 44, 52), self._time_box_rect, border_radius=6)
        pygame.draw.rect(screen, (70, 74, 80),  self._time_box_rect, width=1, border_radius=6)

        if self._time_edit:
            txt = self._time_str if self._time_str else "mm:ss"
            color = (240,240,240) if self._time_str else (150,150,150)
        else:
            txt = self._fmt_time(elapsed)
            color = (200,200,210)
        ts = self.small.render(txt, True, color)
        screen.blit(ts, (self._time_box_rect.x + 6, self._time_box_rect.y + 2))

        total_txt = f"/ {self._fmt_time(length) if length>0 else '--:--'}"
        screen.blit(self.small.render(total_txt, True, (170,170,170)),
                    (self._time_box_rect.right + 6, self._time_box_rect.y + 2))

        # 볼륨 슬라이더 + 라벨(숫자 입력 박스)
        vol_x = self._time_box_rect.right + 60
        vol_y = bar_y + 1
        self._vol_rect = pygame.Rect(vol_x, vol_y, vol_w, 8)
        pygame.draw.rect(screen, (50,54,62), self._vol_rect, border_radius=4)
        # 채움
        vol_ratio = max(0.0, min(1.0, self.volume))
        fill = self._vol_rect.copy(); fill.width = int(self._vol_rect.width * vol_ratio)
        pygame.draw.rect(screen, (130, 200, 120), fill, border_radius=4)
        # 노브
        knob_x = self._vol_rect.left + int(self._vol_rect.width * vol_ratio)
        self._vol_knob_rect = pygame.Rect(knob_x-5, self._vol_rect.centery-6, 10, 12)
        pygame.draw.rect(screen, (220,220,220), self._vol_knob_rect, border_radius=3)

        # 볼륨 라벨 박스(숫자입력)
        self._vol_label_rect = pygame.Rect(self._vol_rect.right + 8, self._vol_rect.y - 6, 56, 22)
        pygame.draw.rect(screen, (40,44,52), self._vol_label_rect, border_radius=6)
        pygame.draw.rect(screen, (70,74,80),  self._vol_label_rect, width=1, border_radius=6)
        if self._vol_edit:
            vtxt = self._vol_str if self._vol_str else "%(0-100)"
            vcol = (240,240,240) if self._vol_str else (150,150,150)
        else:
            vtxt = f"{int(round(self.volume*100))}%"
            vcol = (210,210,210)
        screen.blit(self.small.render(vtxt, True, vcol), (self._vol_label_rect.x+6, self._vol_label_rect.y+2))

        # 하단 가이드
        guide = [
            "Enter: 재생, Space: 일시정지/해제, R: 처음부터, L: 반복 토글",
            "진행바 클릭/드래그: 탐색 ┃ 시간박스 클릭: mm:ss 입력 후 Enter",
            "볼륨: 슬라이더 드래그/휠, 박스 클릭 후 %입력(0~100) + Enter,  +/- 키: 5% 조절, [ / ]: -5s / +5s",
        ]
        for i, t in enumerate(guide):
            screen.blit(self.small.render(t, True, (170,170,170)), (x_right, h - pad - (len(guide)-i)*22))

    # ---------- selection ----------
    def _move_selection(self, delta: int):
        if not self.items: return
        self.idx = (self.idx + delta) % len(self.items)
        self._refresh_selection_highlight()
        self._scroll_item_into_view(self.idx)

    # ---------- playback ----------
    def _play_current(self):
        if not self.items: return
        path = self.items[self.idx]["path"]
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.volume)
            loops = -1 if self.repeat_one else 0
            pygame.mixer.music.play(loops=loops)
            self.paused = False
            self._probe_length(path)
        except pygame.error as e:
            print("[MusicManager] load/play 실패:", e)

    def _toggle_pause(self):
        if self.paused:
            try: pygame.mixer.music.unpause(); self.paused = False
            except pygame.error: pass
        else:
            try: pygame.mixer.music.pause(); self.paused = True
            except pygame.error: pass

    def _restart(self): self._play_current()
    def _next(self):
        if not self.items: return
        self.idx = (self.idx + 1) % len(self.items)
        self._refresh_selection_highlight(); self._scroll_item_into_view(self.idx); self._play_current()

    def _prev(self):
        if not self.items: return
        self.idx = (self.idx - 1) % len(self.items)
        self._refresh_selection_highlight(); self._scroll_item_into_view(self.idx); self._play_current()

    def _toggle_repeat(self):
        self.repeat_one = not self.repeat_one
        if not self.paused: self._play_current()

    # ---------- time/progress ----------
    def _get_elapsed_sec(self) -> float:
        try: ms = pygame.mixer.music.get_pos()
        except pygame.error: ms = 0
        return max(0.0, ms / 1000.0)

    def _fmt_time(self, sec: float) -> str:
        sec = int(max(0, sec))
        return f"{sec//60:02d}:{sec%60:02d}"

    def _probe_length(self, path: Path):
        self._current_length = None
        try:
            if path.suffix.lower() in (".ogg", ".wav"):
                snd = pygame.mixer.Sound(str(path))
                self._current_length = float(snd.get_length())
            else:
                # mp3는 백엔드에 따라 get_length 불가 → None
                self._current_length = None
        except Exception:
            self._current_length = None

    def _seek_by_click(self, mouse_x: int):
        if not self.items: return
        if self._current_length is None or self._current_length <= 0:
            return  # 길이 모르면 정확 탐색 불가
        rel = (mouse_x - self._progress_rect.left) / max(1, self._progress_rect.width)
        rel = max(0.0, min(1.0, rel))
        self._seek_to_seconds(rel * self._current_length)

    def _nudge_time(self, delta: float):
        if self._current_length is None or self._current_length <= 0:
            return
        cur = self._get_elapsed_sec()
        self._seek_to_seconds(cur + delta)

    def _seek_to_seconds(self, sec: float):
        if self._current_length is not None:
            sec = max(0.0, min(self._current_length - 0.05, sec))
        try:
            pygame.mixer.music.set_pos(sec)
            if self.paused:
                pygame.mixer.music.unpause(); pygame.mixer.music.pause()
        except Exception as e:
            print("seek 실패:", e)

    # ---- 시간/볼륨 입력 적용 ----
    def _apply_time_input(self):
        # 허용 포맷: "m:ss" 또는 "mm:ss" 또는 "sss"
        s = self._time_str.strip()
        sec = None
        if ":" in s:
            try:
                m, ss = s.split(":")
                sec = int(m) * 60 + int(ss)
            except ValueError:
                pass
        else:
            try:
                sec = int(s)
            except ValueError:
                pass
        if sec is None:
            print("시간 형식 오류: mm:ss 또는 ss")
            return
        if self._current_length is None or self._current_length <= 0:
            # 길이 모르면 set_pos가 mp3 등에서 동작 안할 수 있음
            try:
                pygame.mixer.music.set_pos(sec)
                if self.paused:
                    pygame.mixer.music.unpause(); pygame.mixer.music.pause()
            except Exception as e:
                print("seek 실패(파일 형식 미지원일 수 있음):", e)
        else:
            self._seek_to_seconds(float(sec))

    def _apply_volume_from_mouse(self, mx: int):
        ratio = (mx - self._vol_rect.left) / max(1, self._vol_rect.width)
        self._set_volume(ratio)

    def _apply_volume_input(self):
        s = self._vol_str.strip()
        try:
            v = int(s)
        except ValueError:
            print("볼륨 형식 오류: 0~100 정수")
            return
        v = max(0, min(100, v))
        self._set_volume(v / 100.0)

    def _set_volume(self, v: float):
        self.volume = max(0.0, min(1.0, v))
        try: pygame.mixer.music.set_volume(self.volume)
        except pygame.error: pass
