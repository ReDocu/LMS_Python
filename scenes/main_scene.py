import pygame, os, math
from core.scene_manager import Scene
from ui.listcontainer import ListContainer
from ui.button import Button
from ui.labelbox import LabelBox
from ui.tabbar import TabBar
from core.theme import get_colors

ASSET_DIR = "assets/images"

# ---------- utils ----------
def safe_load(path: str, alpha: bool = True):
    try:
        img = pygame.image.load(path)
        return img.convert_alpha() if alpha else img.convert()
    except Exception:
        return None

def draw_overlay(surface, alpha=60):
    w, h = surface.get_size()
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    mask.fill((0, 0, 0, alpha))
    surface.blit(mask, (0, 0))

def draw_vignette(surface, strength=120):
    w, h = surface.get_size()
    vign = pygame.Surface((w, h), pygame.SRCALPHA)
    for r, a in (
        (int(min(w, h) * 0.75), int(strength * 0.20)),
        (int(min(w, h) * 0.55), int(strength * 0.35)),
        (int(min(w, h) * 0.40), int(strength * 0.50)),
    ):
        pygame.draw.ellipse(vign, (0, 0, 0, a), (-r // 2, -r // 2, w + r, h + r))
    surface.blit(vign, (0, 0))

def draw_card(surface, rect, fill, border, radius=12, shadow=10, shadow_alpha=70):
    if shadow > 0:
        sh = pygame.Surface((rect.width + shadow * 2, rect.height + shadow * 2), pygame.SRCALPHA)
        pygame.draw.rect(
            sh, (0, 0, 0, shadow_alpha),
            (shadow, shadow, rect.width, rect.height),
            border_radius=radius + 2,
        )
        surface.blit(sh, (rect.x - shadow, rect.y - shadow))
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=radius)

def draw_bubble_tail(surface, bubble_rect, towards, fill, border):
    base_y = bubble_rect.bottom
    base_x = bubble_rect.right - 46
    tri = [(base_x, base_y), (base_x + 28, base_y), (towards[0], towards[1] - 16)]
    pygame.draw.polygon(surface, fill, tri)
    pygame.draw.polygon(surface, border, tri, width=2)

def draw_speech_text(surface, rect, text, font, ink=(40, 40, 40)):
    words = text.split()
    lines, line = [], ""
    max_w = rect.width - 24
    for w in words:
        t = (line + " " + w).strip()
        if font.size(t)[0] <= max_w:
            line = t
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    y = rect.y + 12
    for ln in lines[:3]:
        surf = font.render(ln, True, ink)
        surface.blit(surf, (rect.x + 12, y))
        y += surf.get_height() + 6

def draw_character_glow(surface, rect, color=(80, 120, 200), alpha=55, scale=1.6):
    w = int(rect.width * scale)
    h = int(rect.height * scale)
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (*color, alpha), (0, 0, w, h))
    surface.blit(glow, (rect.centerx - w // 2, rect.centery - h // 2))

# ---------- character ----------
class StaticCharacter:
    def __init__(self, path: str):
        self.img = safe_load(path, alpha=True)
        self.time = 0.0
        self.bob_amp = 6
        self.bob_speed = 2.0

    def update(self, dt: float):
        self.time += dt

    def draw(self, surface: pygame.Surface, rect: pygame.Rect):
        if self.img:
            dy = int(math.sin(self.time * math.pi * self.bob_speed) * self.bob_amp)
            scaled = pygame.transform.smoothscale(self.img, (rect.width, rect.height))
            surface.blit(scaled, (rect.x, rect.y + dy))
        else:
            pygame.draw.rect(surface, (230, 235, 246), rect, border_radius=16)
            pygame.draw.rect(surface, (170, 180, 200), rect, width=2, border_radius=16)

# ---------- main scene ----------
class MainScene(Scene):
    def enter(self, **kwargs):
        self.screen = self.app['screen']
        self.state = self.app['state']
        self.username = kwargs.get("username", self.state.username)

        self.font32 = pygame.font.SysFont("arial", 32)
        self.font24 = pygame.font.SysFont("arial", 24)
        self.font20 = pygame.font.SysFont("arial", 20)

        self._apply_theme(first=True)

        W, H = self.screen.get_size()

        # background

        self.bg_img = self.app["assets"].get_image("background")

        if self.bg_img:
            self.bg_img = pygame.transform.smoothscale(self.bg_img, (W, H))

        # --- TabBar + Logout 공간 확보 ---
        LOGOUT_W, GAP = 120, 10
        self.tabs = TabBar(
            ["All", "Assets", "Text", "Audio", "Templates", "Recent"],
            pos=(430, 22),
            size=(W - 460 - LOGOUT_W - GAP, 40),
            font=self.font20,
            on_change=lambda idx: self._on_tab_change(idx),
        )
        self._sync_tabbar_theme()

        # left panel
        self.left = ListContainer((30, 88), (360, H-118), padding=(12,12), gap=10, bg=None, border=None)
        self.left.set_theme(bg=None, border=(90, 90, 90))  # 투명 유지 (바깥 카드가 이미 있음)


        # character + bubble
        self.dialog_text = f"Hi, {self.username}! What do you want to open?"
        char_path = os.path.join(ASSET_DIR, "char_01.png")
        self.character = StaticCharacter(char_path)

        margin = 24
        char_w, char_h = 240, 320
        self.char_rect = pygame.Rect(W - margin - char_w, H - margin - char_h, char_w, char_h)

        bubble_w, bubble_h = 460, 170
        self.bubble_rect = pygame.Rect(
            self.char_rect.right - bubble_w,
            self.char_rect.top - bubble_h - 12,
            bubble_w, bubble_h
        )

        # Theme / Logout
        self.btn_theme = Button("Theme", (30, 22), (120, 40),
                                font=self.font20, on_click=self._toggle_theme)
        self._apply_button_theme(self.btn_theme)

        self.btn_logout = Button("Logout", (W - 30 - LOGOUT_W, 22), (LOGOUT_W, 40),
                                 font=self.font20, on_click=self._logout)
        self.btn_logout.set_colors(
            default=(220, 60, 60),
            hover=(240, 90, 90),
            active=(200, 40, 40),
            disabled=(150, 120, 120)
        )

        # --- Bubble Open 보조 버튼 (처음엔 숨김) ---
        self.current_feature = None           # {"title","msg","scene_key"}
        open_w, open_h = 100, 36
        self.btn_bubble_open = Button(
            "Open",
            (self.bubble_rect.right - open_w - 14, self.bubble_rect.bottom - open_h - 12),
            (open_w, open_h),
            font=self.font20,
            on_click=self._open_selected
        )
        self._apply_button_theme(self.btn_bubble_open)
        self.bubble_open_visible = False      # scene이 준비된 경우에만 True

        # build menu
        self._rebuild_menu()
        self.feature_buttons = []
        self._cache_feature_buttons()

    # ---- theme ----
    def _apply_theme(self, first=False):
        c = get_colors(self.state.theme)
        self.COL = c
        self.BG = c["bg"]; self.PANEL = c["panel"]; self.PBORDER = c["panel_border"]
        self.INK = c["text"]; self.BTN = c["button_colors"]
        if not first:
            self._apply_theme_to_left_buttons(); self._sync_tabbar_theme()

    def _apply_button_theme(self, btn: Button):
        btn.set_colors(
            default=self.BTN["default"], hover=self.BTN["hover"],
            active=self.BTN["active"], disabled=self.BTN["disabled"]
        )

    def _apply_theme_to_left_buttons(self):
        for w in self.left.widgets:
            if isinstance(w, Button):
                self._apply_button_theme(w)
            elif isinstance(w, LabelBox):
                w.set_theme(bg=None, border=self.PBORDER, ink=self.INK)
        # 말풍선 Open 버튼도 동기화
        self._apply_button_theme(self.btn_bubble_open)

    def _sync_tabbar_theme(self):
        self.tabs.set_theme(
            bg=self.PANEL, border=self.PBORDER, ink=self.INK,
            active_ink=(255, 255, 255), active_bg=self.BTN["default"]
        )

    # ---- tab change ----
    def _on_tab_change(self, idx):
        self._rebuild_menu()

    def _toggle_theme(self):
        self.state.theme = "dark" if self.state.theme == "light" else "light"
        self.state.save()
        self._apply_theme()
        self._apply_button_theme(self.btn_theme)

    # ---- features ----
    def _features_by_tab(self):
        # (name, category, desc, scene_key)
        all_feats = [
            ("YouTube Downloader", "Assets", "Download audio/video from a YouTube URL.", "YTDownloadScene"),
            ("Map Gen", "Assets", "Download audio/video from a YouTube URL.", "ProcGenPlaygroundScene"),
            ("MusicManagement", "Audio", "Download audio/video from a YouTube URL.", "MusicManagerScene"),
        ]
        if self.state.recent:
            recent_feats = [(name, "Recent", f"Recently opened: {name}", None) for name in self.state.recent]
        else:
            recent_feats = []
        return all_feats, recent_feats

    def _rebuild_menu(self):
        tabname = self.tabs.tabs[self.tabs.active_index]

        self.left.clear()
        inner_w = self.left.rect.width - self.left.padding[0]*2

        title_lbl = LabelBox(f"{tabname} Tools", (0, 0), (inner_w, 44),
                             font=self.font24, bg=None, border=self.PBORDER, ink=self.INK)
        self.left.add(title_lbl)

        all_feats, recent_feats = self._features_by_tab()

        def add_button(title, msg, scene_key):
            # 리스트 버튼은 “선택”만 담당 (실행은 말풍선 Open)
            btn = Button(title, (0, 0), (inner_w, 46), font=self.font20,
                         on_click=lambda t=title, m=msg, sk=scene_key: self._select_feature(t, m, sk))
            self._apply_button_theme(btn)
            self.left.add(btn)

        if tabname == "All":
            for t, _, m, sk in all_feats: add_button(t, m, sk)
        elif tabname == "Recent":
            if recent_feats:
                for t, _, m, _ in recent_feats:
                    sk = next((sk for (tt, _, __, sk) in all_feats if tt == t), None)
                    add_button(t, m, sk)
            else:
                self.left.add(LabelBox("No recent items", (0, 0), (inner_w, 40),
                                       font=self.font20, bg=None, border=None, ink=self.INK))
        else:
            for t, cat, m, sk in all_feats:
                if cat == tabname: add_button(t, m, sk)

        self._apply_theme_to_left_buttons()
        # 첫 프레임 번쩍임 방지
        self.left.update([])
        self._cache_feature_buttons()

        # 선택이 바뀌면 Open 버튼은 일단 숨김
        self.bubble_open_visible = False
        self.current_feature = None

    def _cache_feature_buttons(self):
        self.feature_buttons = [w for w in self.left.widgets if isinstance(w, Button)]

    def _select_feature(self, title: str, message: str, scene_key: str | None):
        """왼쪽 버튼을 눌렀을 때: 말풍선 업데이트 + Open 버튼 표시 여부 결정"""
        self.dialog_text = message or f"{title}"
        self.current_feature = {"title": title, "msg": message, "scene_key": scene_key}

        # scene 준비 여부 확인 (self.app에 등록돼 있어야 함)
        self.bubble_open_visible = bool(scene_key and (scene_key in self.app))
        self.btn_bubble_open.set_enabled(self.bubble_open_visible)

        # 최근 목록 업데이트(선택해도 기록)
        self.state.push_recent(title); self.state.save()

    def _open_selected(self):
        """말풍선의 Open 버튼 클릭 또는 Enter 키로 실행"""
        if not (self.bubble_open_visible and self.current_feature):
            return
        sk = self.current_feature["scene_key"]
        if sk and sk in self.app:
            self.app["scenes"].switch(self.app[sk], with_fade=True)

    def _logout(self):
        self.app["scenes"].switch(self.app["LoginScene"], with_fade=True)

    # ---- loop ----
    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app["running"] = False
            if ev.type == pygame.KEYDOWN:
                if pygame.K_1 <= ev.key <= pygame.K_9:
                    idx = ev.key - pygame.K_1
                    if 0 <= idx < len(self.feature_buttons):
                        fn = self.feature_buttons[idx].on_click
                        if fn: fn()
                if ev.key == pygame.K_RETURN:   # Enter로도 Open
                    self._open_selected()

        self.left.update(events)
        self.tabs.handle_events(events)
        self.btn_theme.update(events)
        self.btn_logout.update(events)
        if self.bubble_open_visible:
            self.btn_bubble_open.update(events)

    def update(self, dt):
        self.character.update(dt)

    def draw(self, screen):
        if self.bg_img: screen.blit(self.bg_img, (0, 0))
        else: screen.fill(self.BG)
        draw_overlay(screen, alpha=60)
        draw_vignette(screen, strength=120)

        # header
        header = pygame.Rect(20, 12, screen.get_width() - 40, 60)
        draw_card(screen, header, self.PANEL, self.PBORDER, radius=12, shadow=10, shadow_alpha=70)

        hdr = self.font32.render(f"Hi, {self.username}!", True, self.INK)
        screen.blit(hdr, (170, 24))

        # buttons + tabs
        self.btn_theme.draw(screen)
        self.btn_logout.draw(screen)
        self.tabs.draw(screen)

        # left panel
        left_box = pygame.Rect(20, 76, 380, screen.get_height() - 96)
        draw_card(screen, left_box, self.PANEL, self.PBORDER, radius=12, shadow=10, shadow_alpha=70)
        self.left.draw(screen)

        # character + bubble
        draw_character_glow(screen, self.char_rect, color=(80, 120, 200), alpha=55, scale=1.6)
        self.character.draw(screen, self.char_rect)
        draw_card(screen, self.bubble_rect, self.PANEL, self.PBORDER, radius=14, shadow=12, shadow_alpha=80)
        draw_bubble_tail(screen, self.bubble_rect, self.char_rect.midtop, self.PANEL, self.PBORDER)
        draw_speech_text(screen, self.bubble_rect, self.dialog_text, self.font20, ink=self.INK)

        # bubble Open 보조 버튼 (scene 준비된 경우에만 표시)
        if self.bubble_open_visible:
            self.btn_bubble_open.draw(screen)
