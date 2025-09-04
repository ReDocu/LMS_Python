import pygame, threading, time, os
from typing import Optional
from core.scene_manager import Scene
from ui.listcontainer import ListContainer
from ui.button import Button
from ui.textbox import TextBox
from ui.labelbox import LabelBox
from core.theme import get_colors
from core.fonts import load_font

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
    pygame.draw.rect(surface, fg, (rect.x + 2, rect.y + 2, fill_w, rect.height - 4), border_radius=4)

# -------------------- DownloadItem --------------------
class DownloadItem:
    FIXED_H = 112  # 고정 높이 (레이아웃 안정화)

    def __init__(self, pos, size, font, theme_colors, on_theme_apply):
        w = size[0]
        self.rect = pygame.Rect(pos, (w, self.FIXED_H))
        self.font = font
        self._apply_theme = on_theme_apply

        # 상태
        self.url = ""
        self.format = "mp3"
        self.progress = 0.0
        self.status = "Idle"
        self.downloading = False
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = False
        self.last_filename = ""

        # 하위 위젯(좌표는 _reflow_children에서 배치)
        self.txt_url = TextBox((0, 0), (100, 36), font=self.font, placeholder="YouTube URL")
        self.btn_mp3  = Button("MP3",      (0, 0), (60, 36),  font=self.font, on_click=lambda: self._set_fmt("mp3"))
        self.btn_mp4  = Button("MP4",      (0, 0), (60, 36),  font=self.font, on_click=lambda: self._set_fmt("mp4"))
        self.btn_dl   = Button("Download", (0, 0), (100, 36), font=self.font, on_click=self._start_download)
        self.btn_stop = Button("Stop",     (0, 0), (84, 36),  font=self.font, on_click=self._stop_download, enabled=False)

        self.pb_rect = pygame.Rect(0, 0, 100, 18)

        self.colors = theme_colors
        self._apply_theme_to_widgets()
        self._reflow_children()

    # ----- 레이아웃 -----
    def _reflow_children(self):
        pad = 8
        x = self.rect.x + pad
        y = self.rect.y + pad
        inner_w = self.rect.width - pad * 2

        right_w = 80 + 8 + 60 + 8 + 100 + 8 + 84  # MP3 gap MP4 gap DL(100) gap STOP(84)
        url_w = max(160, inner_w - right_w)

        self.txt_url.rect.topleft = (x, y)
        self.txt_url.rect.size = (url_w, 36)

        cx = x + url_w + 8
        self.btn_mp3.rect.topleft  = (cx, y);          cx += 60 + 8
        self.btn_mp4.rect.topleft  = (cx, y);          cx += 60 + 8
        self.btn_dl.rect.topleft   = (cx, y);          cx += 100 + 8
        self.btn_stop.rect.topleft = (cx, y)

        self.pb_rect.update(x, self.rect.y + 50, inner_w, 18)
        self.rect.height = self.FIXED_H  # 고정

    def set_position(self, x, y):
        self.rect.topleft = (x, y)
        self._reflow_children()

    def set_size(self, width, height=None):
        if width is not None:
            self.rect.width = int(width)
        self._reflow_children()

    # ----- 스크롤용 임시 이동 -----
    def offset(self, dy: int):
        if dy == 0:
            return
        self.rect.move_ip(0, dy)
        self.txt_url.rect.move_ip(0, dy)
        self.btn_mp3.rect.move_ip(0, dy)
        self.btn_mp4.rect.move_ip(0, dy)
        self.btn_dl.rect.move_ip(0, dy)
        self.btn_stop.rect.move_ip(0, dy)
        self.pb_rect.move_ip(0, dy)

    # ----- 테마/토글 -----
    def _set_fmt(self, fmt: str):
        if not self.downloading:
            self.format = fmt

    def _apply_theme_to_widgets(self):
        bc = self.colors["button_colors"]
        for b in (self.btn_mp3, self.btn_mp4, self.btn_dl, self.btn_stop):
            b.set_colors(default=bc["default"], hover=bc["hover"], active=bc["active"], disabled=bc["disabled"])
        if self.format == "mp3":
            self.btn_mp3.set_colors(default=bc["active"], hover=bc["active"], active=bc["active"], disabled=bc["disabled"])
            self._apply_theme(self.btn_mp4)
        else:
            self.btn_mp4.set_colors(default=bc["active"], hover=bc["active"], active=bc["active"], disabled=bc["disabled"])
            self._apply_theme(self.btn_mp3)

    def set_theme(self, theme_colors):
        self.colors = theme_colors
        self._apply_theme_to_widgets()

    # ----- 루프 -----
    def update(self, events):
        self.txt_url.update(events); self.url = self.txt_url.get_text()
        self.btn_mp3.update(events); self.btn_mp4.update(events)
        self.btn_dl.update(events);  self.btn_stop.update(events)
        self._apply_theme_to_widgets()
        self.btn_dl.set_enabled(bool(self.url) and not self.downloading)
        self.btn_stop.set_enabled(self.downloading)

    def draw(self, surface):
        pygame.draw.rect(surface, self.colors["panel"], self.rect, border_radius=10)
        pygame.draw.rect(surface, self.colors["panel_border"], self.rect, width=2, border_radius=10)

        self.txt_url.draw(surface)
        self.btn_mp3.draw(surface); self.btn_mp4.draw(surface)
        self.btn_dl.draw(surface);  self.btn_stop.draw(surface)

        bg_col = (30, 30, 35) if self.colors.get("name") == "dark" else (230, 230, 235)
        draw_progress_bar(surface, self.pb_rect, self.progress, bg=bg_col,
                          fg=self.colors["button_colors"]["default"], border=self.colors["panel_border"])
        st = self.font.render(self._status_line(), True, self.colors["text"])
        surface.blit(st, (self.pb_rect.x, self.pb_rect.bottom + 6))

    def _status_line(self) -> str:
        s = self.status
        if self.last_filename:
            s += f"  •  {self.last_filename}"
        return s

    # ----- 다운로드 -----
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
                        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
                    })
                else:
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
            for i in range(100):
                if self.stop_flag:
                    self.status = "Stopped"; break
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
    def enter(self, **kwargs):
        self.screen = self.app["screen"]
        self.state = self.app["state"]

        self.font32 = load_font(28)
        self.font20 = load_font(20)
        self.font18 = load_font(18)

        self._apply_theme(first=True)

        W, H = self.screen.get_size()

        self.title = LabelBox("YouTube Downloader", (20, 14), (320, 44), font=self.font32)
        self.title.set_theme(bg=None, border=None, ink=self.INK)

        self.btn_add    = Button("Add Item",    (360, 16), (120, 40), font=self.font20, on_click=self._add_item)
        self.btn_remove = Button("Remove Item", (490, 16), (140, 40), font=self.font20, on_click=self._remove_item)
        self.btn_back   = Button("Back",        (640, 16), (100, 40), font=self.font20,
                                  on_click=lambda: self.app["scenes"].switch(self.app["MainScene"], with_fade=True))
        for b in (self.btn_add, self.btn_remove, self.btn_back):
            self._apply_button_theme(b)

        # 스크롤 가능한 리스트
        self.list = ListContainer((20, 100), (W - 40, H - 100),
                                  padding=(12, 12), gap=14,
                                  bg=None, border=self.PBORDER, scroll=True)
        self.items: list[DownloadItem] = []

        self._add_item()
        self._add_item()

        if hasattr(self, "init_quit_button"):
            self.init_quit_button(label="Quit", margin_right=20, margin_top=16)

    # ---- Theme ----
    def _apply_theme(self, first=False):
        c = get_colors(self.state.theme)
        self.COL = c
        self.BG = c["bg"]; self.PANEL = c["panel"]; self.PBORDER = c["panel_border"]
        self.INK = c["text"]; self.BTN = c["button_colors"]
        if not first:
            for b in (self.btn_add, self.btn_remove, self.btn_back):
                self._apply_button_theme(b)
            for it in self.items:
                it.set_theme(self.COL)

    def _apply_button_theme(self, btn: Button):
        btn.set_colors(default=self.BTN["default"], hover=self.BTN["hover"],
                       active=self.BTN["active"], disabled=self.BTN["disabled"])

    # ---- Items ----
    def _add_item(self):
        inner_w = self.list.rect.width - self.list.padding[0] * 2
        item = DownloadItem((0, 0), (inner_w, DownloadItem.FIXED_H),
                            font=self.font18, theme_colors=self.COL,
                            on_theme_apply=lambda b: self._apply_button_theme(b))
        self.items.append(item)
        self.list.add(item)

    def _remove_item(self):
        if not self.items:
            return
        item = self.items.pop()
        # 안전하게 중지
        item.stop_flag = True
        # 컨테이너에서 제거
        self.list.remove(item)

    # ---- Loop ----
    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app["running"] = False

        self.list.update(events)
        self.btn_add.update(events); self.btn_remove.update(events); self.btn_back.update(events)

        if hasattr(self, "update_quit"):
            self.update_quit(events)

    def update(self, dt): pass

    def draw(self, screen):
        screen.fill(self.BG)

        self.title.draw(screen)
        self.btn_add.draw(screen); self.btn_remove.draw(screen); self.btn_back.draw(screen)

        note = "(Requires yt-dlp for real downloads; otherwise runs a mock progress)"
        srf = self.font18.render(note, True, self.INK)
        screen.blit(srf, (20, 54))

        self.list.draw(screen)

        if hasattr(self, "draw_quit"):
            self.draw_quit(screen)
