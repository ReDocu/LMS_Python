# scenes/ytdownload_scene.py
import pygame, threading, time, os
from typing import Optional
from core.scene_manager import Scene
from ui.listcontainer import ListContainer
from ui.button import Button
from ui.textbox import TextBox
from ui.labelbox import LabelBox
from core.theme import get_colors
from core.fonts import load_font

# yt-dlp가 있으면 실제 다운로드, 없으면 모의 다운로드로 동작
try:
    import yt_dlp
    HAS_YTDLP = True
except Exception:
    yt_dlp = None
    HAS_YTDLP = False

DOWNLOAD_DIR = "downloads"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def draw_progress_bar(surface: pygame.Surface, rect: pygame.Rect, progress: float, bg, fg, border):
    pygame.draw.rect(surface, bg, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=6)
    p = max(0.0, min(1.0, progress))
    fill_w = int((rect.width - 4) * p)
    fill_rect = pygame.Rect(rect.x + 2, rect.y + 2, fill_w, rect.height - 4)
    pygame.draw.rect(surface, fg, fill_rect, border_radius=4)


# -------------------- DownloadItem --------------------
class DownloadItem:
    """
    한 줄짜리 다운로드 아이템:
      - URL(TextBox) + MP3/MP4 토글 + Download/Stop
      - 진행률 바 + 상태 텍스트
    스크롤 호환을 위해 offset(dy) 제공.
    """
    FIXED_H = 82  # 고정 높이 (스크롤/레이아웃 안정화)

    def __init__(self, pos, size, font, theme_colors, on_theme_apply):
        w = size[0]
        self.rect = pygame.Rect(pos, (w, self.FIXED_H))
        self.font = font
        self._apply_theme = on_theme_apply

        # 상태값
        self.url = ""
        self.format = "mp3"
        self.progress = 0.0
        self.status = "Idle"
        self.downloading = False
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = False
        self.last_filename = ""

        # 내부 위젯 (초기값은 임시, 아래에서 레이아웃)
        self.txt_url = TextBox((0, 0), (100, 36), font=self.font, placeholder="YouTube URL")
        self.btn_mp3  = Button("MP3",      (0, 0), (60, 36),  font=self.font, on_click=lambda: self._set_fmt("mp3"))
        self.btn_mp4  = Button("MP4",      (0, 0), (60, 36),  font=self.font, on_click=lambda: self._set_fmt("mp4"))
        self.btn_dl   = Button("Download", (0, 0), (100, 36), font=self.font, on_click=self._start_download)
        self.btn_stop = Button("Stop",     (0, 0), (84, 36),  font=self.font, on_click=self._stop_download, enabled=False)

        # 진행바 영역
        self.pb_rect = pygame.Rect(0, 0, 100, 18)

        # 테마
        self.colors = theme_colors
        self._apply_theme_to_widgets()
        self._reflow_children()

        # 스크롤 임시 이동용 누적치(디버깅/안전)
        self._scroll_offset_applied = 0

    # ---------- 레이아웃 ----------
    def _reflow_children(self):
        pad = 8
        x = self.rect.x + pad
        y = self.rect.y + pad
        inner_w = self.rect.width - pad * 2

        # [MP3][gap][MP4][gap][Download(100)][gap][Stop(84)]
        right_w = 60 + 8 + 60 + 8 + 100 + 8 + 84

        url_w = max(160, inner_w - right_w)
        self.txt_url.rect.topleft = (x, y)
        self.txt_url.rect.size = (url_w, 36)

        cx = x + url_w + 8
        self.btn_mp3.rect.topleft  = (cx, y);          cx += 60 + 8
        self.btn_mp4.rect.topleft  = (cx, y);          cx += 60 + 8
        self.btn_dl.rect.topleft   = (cx, y);          cx += 100 + 8
        self.btn_stop.rect.topleft = (cx, y)

        # 진행바
        self.pb_rect.x = x
        self.pb_rect.y = self.rect.y + 50
        self.pb_rect.width = inner_w
        self.pb_rect.height = 18

        # 고정 높이 유지(풍선처럼 늘어나는 버그 방지)
        self.rect.height = self.FIXED_H

    def set_position(self, x, y):
        self.rect.topleft = (x, y)
        self._reflow_children()

    def set_size(self, width, height=None):
        if width is not None:
            self.rect.width = int(width)
        # height는 FIXED_H 유지
        self._reflow_children()

    # ---------- 스크롤 임시 이동 ----------
    def offset(self, dy: int):
        """ListContainer가 스크롤에서 호출: 본체+자식 rect 모두 임시 이동."""
        if dy == 0:
            return
        self._scroll_offset_applied += dy
        self.rect.move_ip(0, dy)
        self.txt_url.rect.move_ip(0, dy)
        self.btn_mp3.rect.move_ip(0, dy)
        self.btn_mp4.rect.move_ip(0, dy)
        self.btn_dl.rect.move_ip(0, dy)
        self.btn_stop.rect.move_ip(0, dy)
        self.pb_rect.move_ip(0, dy)

    # ---------- 테마 ----------
    def _set_fmt(self, fmt: str):
        if self.downloading:
            return
        self.format = fmt

    def _apply_theme_to_widgets(self):
        bc = self.colors["button_colors"]
        for b in (self.btn_mp3, self.btn_mp4, self.btn_dl, self.btn_stop):
            b.set_colors(default=bc["default"], hover=bc["hover"], active=bc["active"], disabled=bc["disabled"])

        # 포맷 선택 강조
        if self.format == "mp3":
            self.btn_mp3.set_colors(
                default=self.colors["button_colors"]["active"],
                hover=self.colors["button_colors"]["active"],
                active=self.colors["button_colors"]["active"],
                disabled=self.colors["button_colors"]["disabled"],
            )
            self._apply_theme(self.btn_mp4)
        else:
            self.btn_mp4.set_colors(
                default=self.colors["button_colors"]["active"],
                hover=self.colors["button_colors"]["active"],
                active=self.colors["button_colors"]["active"],
                disabled=self.colors["button_colors"]["disabled"],
            )
            self._apply_theme(self.btn_mp3)

    def set_theme(self, theme_colors):
        self.colors = theme_colors
        self._apply_theme_to_widgets()

    # ---------- 루프 ----------
    def update(self, events):
        self.txt_url.update(events)
        self.url = self.txt_url.get_text()

        self.btn_mp3.update(events)
        self.btn_mp4.update(events)
        self.btn_dl.update(events)
        self.btn_stop.update(events)

        self._apply_theme_to_widgets()

        self.btn_dl.set_enabled(bool(self.url) and not self.downloading)
        self.btn_stop.set_enabled(self.downloading)

    def draw(self, surface):
        pygame.draw.rect(surface, self.colors["panel"], self.rect, border_radius=10)
        pygame.draw.rect(surface, self.colors["panel_border"], self.rect, width=2, border_radius=10)

        self.txt_url.draw(surface)
        self.btn_mp3.draw(surface)
        self.btn_mp4.draw(surface)
        self.btn_dl.draw(surface)
        self.btn_stop.draw(surface)

        bg_col = (30, 30, 35) if self.colors.get("name") == "dark" else (230, 230, 235)
        draw_progress_bar(surface, self.pb_rect, self.progress,
                          bg=bg_col,
                          fg=self.colors["button_colors"]["default"],
                          border=self.colors["panel_border"])
        st = self.font.render(self._status_line(), True, self.colors["text"])
        surface.blit(st, (self.pb_rect.x, self.pb_rect.bottom + 6))

    def _status_line(self) -> str:
        s = self.status
        if self.last_filename:
            s += f"  •  {self.last_filename}"
        return s

    # ---------- 다운로드 ----------
    def _start_download(self):
        if self.downloading or not self.url:
            return
        self.stop_flag = False
        self.progress = 0.0
        self.status = "Starting..."
        self.downloading = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _stop_download(self):
        if not self.downloading:
            return
        self.stop_flag = True
        self.status = "Stopping..."

    def _worker(self):
        ensure_dir(DOWNLOAD_DIR)
        url = self.url.strip()
        fmt = self.format

        if HAS_YTDLP:
            try:
                ydl_opts = {
                    "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
                    "progress_hooks": [self._hook],
                    "noplaylist": True,
                    "quiet": True,
                }
                if fmt == "mp3":
                    ydl_opts.update({
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                        ],
                    })
                else:  # mp4
                    ydl_opts.update({
                        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                        "merge_output_format": "mp4",
                    })

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if not self.stop_flag:
                    self.progress = 1.0
                    self.status = "Done"
            except Exception as e:
                self.status = f"Error: {e}"
        else:
            # 모의 다운로드
            for i in range(100):
                if self.stop_flag:
                    self.status = "Stopped"
                    break
                self.progress = (i + 1) / 100.0
                self.status = f"Downloading... {int(self.progress * 100)}%"
                time.sleep(0.05)
            else:
                self.status = "Done"

        self.downloading = False

    def _hook(self, d):
        if self.stop_flag:
            raise Exception("User stopped")
        if d.get("status") == "downloading":
            try:
                p = d.get("_percent_str", "").strip().strip("%")
                self.progress = max(0.0, min(1.0, float(p) / 100.0))
            except Exception:
                pass
            self.last_filename = d.get("filename", self.last_filename)
            self.status = "Downloading..."
        elif d.get("status") == "finished":
            self.status = "Postprocessing..."
            self.last_filename = d.get("filename", self.last_filename)


# -------------------- Scene --------------------
class YTDownloadScene(Scene):
    """YouTube MP3/MP4 다운로드 씬 (멀티-아이템)"""
    def enter(self, **kwargs):
        self.screen = self.app["screen"]
        self.state = self.app["state"]

        # ✅ 한글 가능한 폰트
        self.font32 = load_font(28)
        self.font20 = load_font(20)
        self.font18 = load_font(18)

        self._apply_theme(first=True)

        W, H = self.screen.get_size()

        # 상단
        self.title = LabelBox("YouTube Downloader", (20, 14), (320, 44), font=self.font32)
        self.title.set_theme(bg=None, border=None, ink=self.INK)

        self.btn_add = Button("Add Item", (360, 16), (120, 40), font=self.font20, on_click=self._add_item)
        self._apply_button_theme(self.btn_add)

        # ✅ 스크롤 가능한 리스트 (scroll=True)
        self.list = ListContainer((20, 70), (W - 40, H - 100),
                                  padding=(12, 12), gap=14,
                                  bg=None, border=self.PBORDER, scroll=True)
        self.items: list[DownloadItem] = []

        # 초기 아이템
        self._add_item()
        self._add_item()

        # 공통 Quit 버튼 (있다면)
        if hasattr(self, "init_quit_button"):
            self.init_quit_button(label="Quit", margin_right=20, margin_top=16)

    def _apply_theme(self, first=False):
        c = get_colors(self.state.theme)
        self.COL = c
        self.BG = c["bg"]
        self.PANEL = c["panel"]
        self.PBORDER = c["panel_border"]
        self.INK = c["text"]
        self.BTN = c["button_colors"]
        if not first:
            self._apply_button_theme(self.btn_add)
            for it in self.items:
                it.set_theme(self.COL)

    def _apply_button_theme(self, btn: Button):
        btn.set_colors(
            default=self.BTN["default"],
            hover=self.BTN["hover"],
            active=self.BTN["active"],
            disabled=self.BTN["disabled"],
        )

    def _add_item(self):
        inner_w = self.list.rect.width - self.list.padding[0] * 2
        item = DownloadItem(
            (0, 0), (inner_w, DownloadItem.FIXED_H),
            font=self.font18,
            theme_colors=self.COL,
            on_theme_apply=lambda b: self._apply_button_theme(b),
        )
        self.items.append(item)
        self.list.add(item)

    # ---- loop ----
    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app["running"] = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                pass

        self.list.update(events)
        self.btn_add.update(events)

        if hasattr(self, "update_quit"):
            self.update_quit(events)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(self.BG)

        self.title.draw(screen)
        self.btn_add.draw(screen)

        note = "(Requires yt-dlp for real downloads; otherwise runs a mock progress)"
        srf = self.font18.render(note, True, self.INK)
        screen.blit(srf, (20, 54))

        self.list.draw(screen)

        if hasattr(self, "draw_quit"):
            self.draw_quit(screen)
