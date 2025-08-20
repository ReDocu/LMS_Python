#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import pygame
from pygame import Rect

pygame.init()

# ----------------------------
# Config
# ----------------------------
WIN_W, WIN_H = 1200, 720
FPS = 60

BG = (245, 246, 248)
PANEL = (255, 255, 255)
BORDER = (180, 186, 196)
TEXT = (25, 28, 33)
MUTED = (105, 115, 125)
ACCENT = (95, 125, 255)
HOVER = (235, 238, 243)
RADIUS = 10

FONT = pygame.font.SysFont("malgungothic", 20)
SMALL = pygame.font.SysFont("malgungothic", 16)
TITLE = pygame.font.SysFont("malgungothic", 24, bold=True)

ASSETS_DIR = "assets"  # drop your images here (e.g., assets/btn_start.png, assets/character.png)

# ----------------------------
# Helpers
# ----------------------------
def draw_round(surface, rect, color, radius=RADIUS, width=0):
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)

def draw_border(surface, rect, color=BORDER, radius=RADIUS, width=1):
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)

def blit_text(surface, text, pos, font=FONT, color=TEXT):
    img = font.render(text, True, color)
    surface.blit(img, pos)
    return img.get_rect(topleft=pos)

def try_load_image(path):
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

def center_in(inner, outer):
    x = outer.x + (outer.w - inner.w) // 2
    y = outer.y + (outer.h - inner.h) // 2
    return x, y

# Speech bubble with tail
def draw_speech_bubble(surface, rect, text, tail_dir="right", tail_size=(26, 18)):
    draw_round(surface, rect, (255, 255, 255), radius=14)
    draw_border(surface, rect, color=BORDER, radius=14)
    # tail
    w, h = tail_size
    if tail_dir == "right":
        pts = [(rect.right - 14, rect.bottom - h - 8),
               (rect.right + w - 10, rect.bottom - h//2 - 6),
               (rect.right - 14, rect.bottom - 10)]
    else:  # left
        pts = [(rect.x + 14, rect.bottom - h - 8),
               (rect.x - w + 10, rect.bottom - h//2 - 6),
               (rect.x + 14, rect.bottom - 10)]
    pygame.draw.polygon(surface, (255,255,255), pts)
    pygame.draw.lines(surface, BORDER, False, pts, 1)

    # wrap text
    words = text.split()
    lines, cur = [], ""
    maxw = rect.w - 24
    for w_ in words:
        test = (cur + " " + w_).strip()
        if FONT.size(test)[0] <= maxw:
            cur = test
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    y = rect.y + 12
    for ln in lines[:6]:
        blit_text(surface, ln, (rect.x + 12, y), font=FONT, color=TEXT)
        y += 26

# ----------------------------
# UI Elements
# ----------------------------
class ImageButton:
    """Image-backed button; falls back to rectangle with text if image missing."""
    def __init__(self, rect, text, image_name=None, on_click=None):
        self.rect = Rect(rect)
        self.text = text
        self.on_click = on_click
        self.hover = False
        self.pressed = False
        self.image = None
        if image_name:
            path = os.path.join(ASSETS_DIR, image_name)
            self.image = try_load_image(path)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click(self)
            self.pressed = False

    def draw(self, surface):
        if self.image:
            # fit image into rect keeping aspect ratio
            img = self.image
            iw, ih = img.get_size()
            scale = min(self.rect.w/iw, self.rect.h/ih)
            new = pygame.transform.smoothscale(img, (int(iw*scale), int(ih*scale)))
            pos = center_in(new.get_rect(), self.rect)
            draw_round(surface, self.rect, (255,255,255))
            draw_border(surface, self.rect)
            surface.blit(new, pos)
        else:
            draw_round(surface, self.rect, HOVER if self.hover else (255,255,255))
            draw_border(surface, self.rect)
            blit_text(surface, self.text, (self.rect.x + 16, self.rect.y + (self.rect.h-22)//2), font=FONT)

class ListView:
    """Simple scrollable list."""
    def __init__(self, rect, items):
        self.rect = Rect(rect)
        self.items = list(items)
        self.item_h = 36
        self.offset = 0
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if event.button == 4:   # wheel up
                    self.offset = max(0, self.offset - 1)
                elif event.button == 5: # wheel down
                    max_off = max(0, len(self.items) - self.visible_count())
                    self.offset = min(max_off, self.offset + 1)
                elif event.button == 1:
                    y_rel = event.pos[1] - self.rect.y
                    idx = y_rel // self.item_h + self.offset
                    if 0 <= idx < len(self.items):
                        self.selected = idx
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = max(0, self.selected - 1)
                self.ensure_visible(self.selected)
            elif event.key == pygame.K_DOWN:
                self.selected = min(len(self.items)-1, self.selected + 1)
                self.ensure_visible(self.selected)

    def visible_count(self):
        return max(1, self.rect.h // self.item_h)

    def ensure_visible(self, idx):
        if idx < self.offset:
            self.offset = idx
        elif idx >= self.offset + self.visible_count():
            self.offset = idx - self.visible_count() + 1

    def draw(self, surface):
        draw_round(surface, self.rect, (255,255,255))
        draw_border(surface, self.rect)
        # clip
        clip_prev = surface.get_clip()
        surface.set_clip(self.rect.inflate(-2, -2))
        y = self.rect.y
        for i in range(self.offset, min(len(self.items), self.offset + self.visible_count())):
            r = Rect(self.rect.x + 4, y + 2, self.rect.w - 8, self.item_h - 4)
            if i == self.selected:
                draw_round(surface, r, (231, 238, 255))
                blit_text(surface, self.items[i], (r.x + 8, r.y + 6), font=FONT, color=ACCENT)
            else:
                if (i - self.offset) % 2 == 1:
                    draw_round(surface, r, (246, 248, 251))
                blit_text(surface, self.items[i], (r.x + 8, r.y + 6), font=FONT, color=TEXT)
            y += self.item_h
        surface.set_clip(clip_prev)

# ----------------------------
# App
# ----------------------------
class App:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
        pygame.display.set_caption("게임 리스트 · 캐릭터 · 말풍선 템플릿")
        self.clock = pygame.time.Clock()
        self.running = True

        # state
        self.message = "안녕! 리스트에서 항목을 선택하거나 버튼을 눌러봐."
        self.character_img = try_load_image(os.path.join(ASSETS_DIR, "character.png"))

        # UI create
        self.make_ui()

    # Layout rectangles based on the provided wireframe
    def layout(self):
        w, h = self.screen.get_size()
        outer = Rect(10, 10, w - 20, h - 20)
        title_h = 48
        title_rect = Rect(outer.x + 16, outer.y + 12, outer.w - 32, title_h)

        left_panel = Rect(outer.x + 16, title_rect.bottom + 10, outer.w * 0.62, outer.h - title_h - 40)
        right_panel = Rect(left_panel.right + 12, title_rect.bottom + 10, outer.right - (left_panel.right + 28), left_panel.h)

        # inside left: list box
        list_rect = Rect(left_panel.x + 12, left_panel.y + 12, left_panel.w - 24, left_panel.h - 24)

        # inside right: character image box and buttons; speech bubble overlays bottom area
        char_w = right_panel.w - 40
        char_h = int(right_panel.h * 0.55)
        char_rect = Rect(right_panel.x + 20, right_panel.y + 20, char_w, char_h)

        btn_area = Rect(right_panel.x + 20, char_rect.bottom + 12, char_w, 120)
        # speech bubble floats across bottom-right over both panels width-wise
        bubble_w = min(520, outer.w * 0.45)
        bubble_h = 120
        bubble_rect = Rect(right_panel.right - bubble_w - 10, right_panel.bottom - bubble_h - 4, bubble_w, bubble_h)

        return outer, title_rect, left_panel, list_rect, right_panel, char_rect, btn_area, bubble_rect

    def make_ui(self):
        # list
        items = [f"프로그램 {i+1:02d}" for i in range(40)]
        _, _, _, list_rect, _, _, _, _ = self.layout()
        self.listview = ListView(list_rect, items)

        # buttons (image-backed with fallback)
        def make_handler(msg):
            def _cb(btn):
                self.message = msg
            return _cb
        # three sample buttons expecting optional images in assets/
        self.buttons = [
            ImageButton((0,0,0,44), "시작 (btn_start.png)",  "btn_start.png",  on_click=make_handler("시작 버튼 눌림!")),
            ImageButton((0,0,0,44), "옵션 (btn_options.png)", "btn_options.png", on_click=make_handler("옵션 열기!")),
            ImageButton((0,0,0,44), "종료 (btn_exit.png)",    "btn_exit.png",   on_click=make_handler("종료...는 아직 못하게 할래 🤭")),
        ]

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False

        self.listview.handle_event(event)
        for b in self.buttons:
            b.handle_event(event)

        # Update bubble message if selection changed by click
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.message = f"선택: {self.listview.items[self.listview.selected]}"

    def draw_character(self, rect):
        draw_round(self.screen, rect, (255,255,255))
        draw_border(self.screen, rect)
        if self.character_img:
            iw, ih = self.character_img.get_size()
            scale = min((rect.w - 20)/iw, (rect.h - 20)/ih)
            new = pygame.transform.smoothscale(self.character_img, (int(iw*scale), int(ih*scale)))
            pos = center_in(new.get_rect(), rect)
            self.screen.blit(new, pos)
        else:
            # dummy
            blit_text(self.screen, "캐릭터 이미지", (rect.x + 20, rect.y + 20), font=TITLE, color=MUTED)
            pygame.draw.rect(self.screen, (235, 235, 240), rect.inflate(-40, -40), border_radius=12)
            pygame.draw.rect(self.screen, BORDER, rect.inflate(-40, -40), width=1, border_radius=12)

    def place_buttons(self, area):
        # arrange buttons horizontally
        x = area.x
        y = area.y
        gap = 10
        bw, bh = (area.w - gap*2)//3, 48
        for i, b in enumerate(self.buttons):
            b.rect = Rect(x + i*(bw + gap), y, bw, bh)
            b.draw(self.screen)

    def draw(self):
        self.screen.fill(BG)
        outer, title_rect, left_panel, list_rect, right_panel, char_rect, btn_area, bubble_rect = self.layout()

        # outer border
        draw_round(self.screen, outer, PANEL, radius=8)
        draw_border(self.screen, outer, radius=8)

        # title
        blit_text(self.screen, "게임 리스트 제목", (title_rect.x, title_rect.y), font=TITLE)
        # left panel
        draw_round(self.screen, left_panel, PANEL)
        draw_border(self.screen, left_panel)
        blit_text(self.screen, "프로그램 리스트", (left_panel.x + 12, left_panel.y + 8), font=SMALL, color=MUTED)
        # list
        self.listview.rect = list_rect
        self.listview.draw(self.screen)

        # right panel
        draw_round(self.screen, right_panel, PANEL)
        draw_border(self.screen, right_panel)
        # character
        self.draw_character(char_rect)

        # buttons under character
        self.place_buttons(btn_area)

        # speech bubble (overlay)
        draw_speech_bubble(self.screen, bubble_rect, self.message, tail_dir="right")

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
