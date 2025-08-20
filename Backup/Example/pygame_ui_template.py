#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import pygame
from pygame import Rect

pygame.init()

# ----------------------------
# Config
# ----------------------------
WIN_W, WIN_H = 1100, 700
FPS = 60

# Layout ratios (relative)
HEADER_H = 64
FOOTER_H = 32
SIDEBAR_W = 240

BG_COLOR = (18, 18, 20)
PANEL_COLOR = (28, 28, 32)
BORDER_COLOR = (55, 55, 65)
TEXT_COLOR = (230, 230, 235)
MUTED_TEXT = (170, 170, 180)

ACCENT = (100, 130, 255)
ACCENT_DARK = (75, 95, 200)
HOVER = (44, 44, 52)
ACTIVE = (60, 60, 68)

RADIUS = 12

# ----------------------------
# Helpers
# ----------------------------
def draw_round_rect(surface, rect, color, radius=RADIUS, width=0):
    """Draw a rounded rectangle."""
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)

def draw_border(surface, rect, color=BORDER_COLOR, radius=RADIUS, width=1):
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)

def blit_text(surface, text, pos, font, color=TEXT_COLOR, aa=True):
    s = font.render(text, aa, color)
    surface.blit(s, pos)
    return s.get_rect(topleft=pos)

# ----------------------------
# UI Primitives
# ----------------------------
class Button:
    def __init__(self, rect, text, on_click=None, kind="solid", group=None, shortcut=None):
        self.rect = Rect(rect)
        self.text = text
        self.on_click = on_click
        self.kind = kind  # "solid" or "ghost"
        self.group = group
        self.shortcut = shortcut
        self.hover = False
        self.active = False
        self.focus = False

        self.font = pygame.font.SysFont("malgungothic", 18)
        self.pad_x, self.pad_y = 16, 10

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.active = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.active and self.rect.collidepoint(event.pos):
                if self.group:  # turn off others in group
                    for b in self.group:
                        b.active = False
                self.active = True
                if self.on_click:
                    self.on_click(self)
            self.active = False
        elif event.type == pygame.KEYDOWN and self.shortcut:
            if event.key == self.shortcut:
                if self.on_click:
                    self.on_click(self)

    def draw(self, surface):
        # background
        if self.kind == "solid":
            color = ACCENT if (self.focus or self.active) else (ACCENT_DARK if self.hover else ACCENT)
            draw_round_rect(surface, self.rect, color)
        else:  # ghost
            color = HOVER if (self.focus or self.active or self.hover) else PANEL_COLOR
            draw_round_rect(surface, self.rect, color)
            draw_border(surface, self.rect)

        # text
        text_color = (255, 255, 255) if self.kind == "solid" else TEXT_COLOR
        txt = self.font.render(self.text, True, text_color)
        tx = self.rect.x + (self.rect.w - txt.get_width()) // 2
        ty = self.rect.y + (self.rect.h - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))

class Toggle:
    """Simple toggle switch used in the sidebar."""
    def __init__(self, rect, label, value=False, on_change=None):
        self.rect = Rect(rect)
        self.label = label
        self.value = value
        self.on_change = on_change
        self.font = pygame.font.SysFont("malgungothic", 17)
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                if self.on_change:
                    self.on_change(self.value)

    def draw(self, surface):
        # label
        blit_text(surface, self.label, (self.rect.x, self.rect.y), self.font, color=TEXT_COLOR)
        # switch
        sw_w, sw_h = 44, 24
        sw_x = self.rect.right - sw_w
        sw_y = self.rect.y - 2
        track = Rect(sw_x, sw_y, sw_w, sw_h)
        knob_r = sw_h - 6
        draw_round_rect(surface, track, ACTIVE if self.value else HOVER, radius=sw_h//2)
        # knob
        kx = sw_x + (sw_w - sw_h + 3) if self.value else sw_x + 3
        ky = sw_y + 3
        pygame.draw.circle(surface, (240,240,245), (kx + (sw_h-6)//2, ky + (sw_h-6)//2), (sw_h-6)//2)

class ImageCard:
    """Placeholder 'image' card."""
    def __init__(self, rect, title="Placeholder", subtitle=None):
        self.rect = Rect(rect)
        self.title = title
        self.subtitle = subtitle
        self.title_font = pygame.font.SysFont("malgungothic", 18, bold=True)
        self.sub_font = pygame.font.SysFont("malgungothic", 14)

    def draw(self, surface):
        draw_round_rect(surface, self.rect, HOVER)
        draw_border(surface, self.rect)
        # fake thumbnail region
        thumb = self.rect.inflate(-20, -20)
        thumb.h = int(self.rect.h * 0.6)
        draw_round_rect(surface, thumb, (35,35,42), radius=10)
        draw_border(surface, thumb)
        # caption
        tx = self.rect.x + 14
        ty = thumb.bottom + 8
        blit_text(surface, self.title, (tx, ty), self.title_font, color=TEXT_COLOR)
        if self.subtitle:
            blit_text(surface, self.subtitle, (tx, ty + 22), self.sub_font, color=MUTED_TEXT)

# ----------------------------
# App State
# ----------------------------
class App:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
        pygame.display.set_caption("Pygame UI Template")
        self.clock = pygame.time.Clock()
        self.running = True

        self.ui_init()

    def ui_init(self):
        self.title_font = pygame.font.SysFont("malgungothic", 22, bold=True)
        self.small_font = pygame.font.SysFont("malgungothic", 16)
        self.sidebar_open = True
        self.active_tab = "Dashboard"
        self.message = "Ready."

        # Dynamic UI elements
        self.header_buttons = []
        self.sidebar_buttons = []
        self.sidebar_toggles = []

        self.make_header()
        self.make_sidebar()

    # --- Layout Rects ---
    def layout_rects(self):
        w, h = self.screen.get_size()
        header = Rect(12, 10, w - 24, HEADER_H)
        footer = Rect(12, h - FOOTER_H - 10, w - 24, FOOTER_H)
        sb_w = SIDEBAR_W if self.sidebar_open else 0
        sidebar = Rect(12, header.bottom + 10, sb_w, h - header.h - footer.h - 40)
        content = Rect(sidebar.right + (10 if self.sidebar_open else 0), header.bottom + 10,
                       w - sidebar.w - 12 - 12 - (10 if self.sidebar_open else 0), h - header.h - footer.h - 40)
        return header, sidebar, content, footer

    # --- Header ---
    def make_header(self):
        self.header_buttons.clear()
        def on_toggle_sidebar(btn):
            self.sidebar_open = not self.sidebar_open
            self.message = f"Sidebar {'opened' if self.sidebar_open else 'collapsed'}."
        def on_refresh(btn):
            self.message = "Refreshed ✨"
        def on_tab(btn):
            self.active_tab = btn.text
            self.message = f"Switched to {btn.text}"

        # Placeholder rects will be set in draw()
        self.btn_toggle_sidebar = Button((0,0,44,36), "≡", on_click=on_toggle_sidebar, kind="ghost")
        self.btn_refresh = Button((0,0,80,36), "새로고침", on_click=on_refresh, kind="ghost")
        # Tab buttons (grouped)
        self.tab1 = Button((0,0,110,36), "Dashboard", on_click=on_tab, kind="ghost")
        self.tab2 = Button((0,0,110,36), "Gallery", on_click=on_tab, kind="ghost")
        self.tab3 = Button((0,0,110,36), "Settings", on_click=on_tab, kind="ghost")
        tabs = [self.tab1, self.tab2, self.tab3]
        for t in tabs:
            t.group = tabs
        self.tab1.active = True

        self.header_buttons = [self.btn_toggle_sidebar, self.btn_refresh, self.tab1, self.tab2, self.tab3]

    # --- Sidebar ---
    def make_sidebar(self):
        self.sidebar_buttons.clear()
        self.sidebar_toggles.clear()

        def make_click_cb(name):
            def _cb(btn):
                self.active_tab = name
                self.message = f"Clicked {name}"
                # update group active
                for b in self.sidebar_buttons:
                    b.active = (b.text == name)
            return _cb

        items = ["홈", "프로젝트", "리소스", "도움말"]
        for _ in items:
            self.sidebar_buttons.append(Button((0,0,0,40), _, on_click=make_click_cb(_), kind="ghost"))
        self.sidebar_buttons[0].active = True

        # toggles
        self.sidebar_toggles.append(Toggle(Rect(0,0,200,28), "알림", value=True, on_change=lambda v: print("알림:", v)))
        self.sidebar_toggles.append(Toggle(Rect(0,0,200,28), "자동저장", value=False, on_change=lambda v: print("자동저장:", v)))

    # --- Content ---
    def draw_dashboard(self, surface, rect):
        # grid of image cards
        pad = 12
        cols = max(1, (rect.w + pad) // (280 + pad))
        card_w, card_h = 280, 200
        x = rect.x + pad
        y = rect.y + pad

        items = [
            ("샘플 이미지 A", "1024x768"),
            ("샘플 이미지 B", "512x512"),
            ("샘플 이미지 C", "1920x1080"),
            ("샘플 이미지 D", "1:1 Placeholder"),
            ("샘플 이미지 E", "작업중..."),
            ("샘플 이미지 F", "템플릿")
        ]

        for i, (title, sub) in enumerate(items):
            r = Rect(x, y, card_w, card_h)
            ImageCard(r, title, sub).draw(surface)
            if (i+1) % cols == 0:
                x = rect.x + pad
                y += card_h + pad
            else:
                x += card_w + pad

        # help block
        help_rect = Rect(rect.x + pad, rect.bottom - 90, rect.w - pad*2, 80)
        draw_round_rect(surface, help_rect, ACTIVE)
        draw_border(surface, help_rect)
        blit_text(surface, "💡 Tip: 버튼들은 콘솔에 로그를 찍고 탭을 전환합니다.", (help_rect.x + 12, help_rect.y + 12), self.small_font, color=TEXT_COLOR)

    def draw_gallery(self, surface, rect):
        # big placeholder
        inner = rect.inflate(-16, -16)
        draw_round_rect(surface, inner, HOVER)
        draw_border(surface, inner)
        # Title
        blit_text(surface, "Gallery Placeholder", (inner.x + 14, inner.y + 12), self.title_font)
        # Thumbnails row
        thumb_w, thumb_h = 140, 100
        x = inner.x + 14
        y = inner.y + 50
        for i in range(6):
            card = Rect(x, y, thumb_w, thumb_h)
            draw_round_rect(surface, card, (35,35,42), radius=10)
            draw_border(surface, card)
            blit_text(surface, f"{i+1}", (card.centerx - 6, card.centery - 10), self.title_font)
            x += thumb_w + 10

    def draw_settings(self, surface, rect):
        inner = rect.inflate(-16, -16)
        draw_round_rect(surface, inner, HOVER)
        draw_border(surface, inner)
        blit_text(surface, "Settings", (inner.x + 14, inner.y + 12), self.title_font)

        # Some fake controls (labels only)
        y = inner.y + 60
        for label in ["Theme", "Language", "Layout Density", "Experimental Features"]:
            blit_text(surface, f"- {label}", (inner.x + 20, y), self.small_font, color=MUTED_TEXT)
            y += 30

    # --- Event Loop ---
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False

        # Send events
        for b in self.header_buttons:
            b.handle_event(event)
        if self.sidebar_open:
            for b in self.sidebar_buttons:
                b.handle_event(event)
            for t in self.sidebar_toggles:
                t.handle_event(event)

    def draw(self):
        self.screen.fill(BG_COLOR)
        header, sidebar, content, footer = self.layout_rects()

        # Header
        draw_round_rect(self.screen, header, PANEL_COLOR)
        draw_border(self.screen, header)
        blit_text(self.screen, "UI 템플릿", (header.x + 16, header.y + 18), self.title_font)
        # place header buttons (right side)
        x = header.right - 16
        pad = 8
        for btn in reversed(self.header_buttons[0:2]):  # toggle + refresh
            btn.rect.size = (max(44, btn.rect.w), 36)
            btn.rect.topleft = (x - btn.rect.w, header.y + (header.h - btn.rect.h)//2)
            x -= btn.rect.w + pad
        # tabs
        x -= 12
        for btn in self.header_buttons[2:]:
            btn.rect.size = (110, 36)
            btn.rect.topleft = (x - btn.rect.w, header.y + (header.h - btn.rect.h)//2)
            x -= btn.rect.w + pad

        for b in self.header_buttons:
            b.draw(self.screen)

        # Sidebar
        if self.sidebar_open:
            draw_round_rect(self.screen, sidebar, PANEL_COLOR)
            draw_border(self.screen, sidebar)
            # sidebar buttons stacked
            y = sidebar.y + 12
            for b in self.sidebar_buttons:
                b.rect = Rect(sidebar.x + 12, y, sidebar.w - 24, 40)
                b.draw(self.screen)
                y += 46

            # toggles
            y += 10
            for t in self.sidebar_toggles:
                t.rect.topleft = (sidebar.x + 16, y)
                t.rect.width = sidebar.w - 32
                t.draw(self.screen)
                y += 34

        # Content
        draw_round_rect(self.screen, content, PANEL_COLOR)
        draw_border(self.screen, content)

        if self.active_tab == "Dashboard":
            self.draw_dashboard(self.screen, content)
        elif self.active_tab == "Gallery":
            self.draw_gallery(self.screen, content)
        else:
            self.draw_settings(self.screen, content)

        # Footer
        draw_round_rect(self.screen, footer, PANEL_COLOR)
        draw_border(self.screen, footer)
        blit_text(self.screen, f"상태: {self.message}", (footer.x + 12, footer.y + 7), self.small_font, color=MUTED_TEXT)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
        pygame.quit()
        sys.exit()

def main():
    App().run()

if __name__ == "__main__":
    main()
