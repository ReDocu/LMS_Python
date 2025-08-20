# music_grouper_player.py
import os
import sys
import math
import shutil
import threading
import pygame
from pygame import Rect
from tkinter import Tk, filedialog, simpledialog

# -----------------------------
# Config
# -----------------------------
WIN_W, WIN_H = 900, 600
LIST_LEFT, LIST_TOP, LIST_W, LIST_H = 20, 80, 520, 480
CTRL_W = 840
FONT_NAME = None
ROW_H = 26
SCROLLBAR_W = 10
SUPPORTED_EXT = {'.mp3','.ogg','.wav','.flac','.m4a','.aac'}

# Colors
BG = (22,22,26)
FG = (235,235,245)
MUTED = (170,170,185)
ACCENT = (120,170,255)
ACCENT_DIM = (90,120,210)
SEL = (60,90,150)
SEL_BORDER = (150,180,255)
BTN = (40,40,52)
BTN_HOVER = (60,60,78)
BTN_TEXT = (230,230,240)
ERR = (255,90,90)
OK = (90,220,120)

pygame.mixer.pre_init(44100, -16, 2, 1024)
pygame.init()
pygame.display.set_caption("Pygame Music Player + Group/Copy")
screen = pygame.display.set_mode((WIN_W, WIN_H))
clock = pygame.time.Clock()
font = pygame.font.SysFont(FONT_NAME, 18)
font_small = pygame.font.SysFont(FONT_NAME, 14)
font_big = pygame.font.SysFont(FONT_NAME, 22)

MUSIC_END = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(MUSIC_END)

# Tk root (hidden)
_tk = Tk()
_tk.withdraw()

def is_audio(p):
    return os.path.splitext(p)[1].lower() in SUPPORTED_EXT

def list_audio_in(path):
    out=[]
    if os.path.isdir(path):
        for root,_,files in os.walk(path):
            for f in files:
                fp = os.path.join(root,f)
                if is_audio(fp):
                    out.append(os.path.normpath(fp))
    else:
        if is_audio(path):
            out.append(os.path.normpath(path))
    return out

def secs_to_mmss(s):
    if s is None or s<=0:
        return "??:??"
    m = int(s//60)
    ss = int(s%60)
    return f"{m:02d}:{ss:02d}"

class Playlist:
    def __init__(self):
        self.tracks=[]  # list[str]
    def add_many(self, paths):
        before = len(self.tracks)
        for p in paths:
            if p not in self.tracks:
                self.tracks.append(p)
        return len(self.tracks)-before
    def add_from_open_dialog(self):
        d = filedialog.askdirectory(title="음악 폴더 선택")
        if not d: return 0
        return self.add_many(list_audio_in(d))
    def add_from_drop(self, dropped_path):
        return self.add_many(list_audio_in(dropped_path))
    def __len__(self): return len(self.tracks)
    def __getitem__(self,i): return self.tracks[i]

class Player:
    def __init__(self, playlist: Playlist):
        self.playlist = playlist
        self.index = -1
        self.paused = False
        self.repeat_mode = 0  # 0: none, 1: all, 2: one
        self.shuffle = False
        self.history=[]
        self.volume = 0.7
        pygame.mixer.music.set_volume(self.volume)
        self.length_cache = {}  # path -> seconds (best-effort)
    def play(self, idx):
        if not (0<=idx<len(self.playlist)): return
        self.index = idx
        path = self.playlist[idx]
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self.paused = False
        except Exception as e:
            print("Play error:", e)
    def toggle_pause(self):
        if pygame.mixer.music.get_busy():
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused=False
            else:
                pygame.mixer.music.pause()
                self.paused=True
        else:
            # if stopped, try resume current
            if 0<=self.index<len(self.playlist):
                self.play(self.index)
    def stop(self):
        pygame.mixer.music.stop()
        self.paused=False
    def next(self):
        n = len(self.playlist)
        if n==0: return
        if self.repeat_mode==2:  # one
            self.play(self.index)
            return
        if self.shuffle:
            import random
            choices = [i for i in range(n) if i!=self.index]
            if choices:
                self.play(random.choice(choices))
            else:
                self.play(self.index)
            return
        # linear
        ni = self.index + 1
        if ni>=n:
            if self.repeat_mode==1:
                ni = 0
            else:
                self.stop()
                return
        self.play(ni)
    def prev(self):
        n = len(self.playlist)
        if n==0: return
        if self.repeat_mode==2:
            self.play(self.index)
            return
        if self.shuffle:
            import random
            choices = [i for i in range(n) if i!=self.index]
            if choices:
                self.play(random.choice(choices))
            else:
                self.play(self.index)
            return
        pi = self.index - 1
        if pi<0:
            if self.repeat_mode==1:
                pi = n-1
            else:
                pi = 0
        self.play(pi)
    def set_repeat(self):
        self.repeat_mode = (self.repeat_mode+1)%3
    def set_shuffle(self):
        self.shuffle = not self.shuffle
    def set_volume(self, delta):
        self.volume = max(0.0, min(1.0, self.volume+delta))
        pygame.mixer.music.set_volume(self.volume)
    def set_pos_ratio(self, r):
        # r in [0,1]; best-effort seek
        try:
            # pygame.mixer.music.set_pos takes seconds from beginning for some formats
            # We don't always know exact length; try using Sound length if possible
            length = self.length_cache.get(self.playlist[self.index])
            if length:
                pygame.mixer.music.play(start=length*r)
            else:
                pygame.mixer.music.set_pos( max(0.0, r*180.0) )  # heuristic
        except Exception as e:
            print("seek failed:", e)

# UI helpers
def draw_text(surf, text, pos, color=FG, f=font, center_y=False):
    t = f.render(text, True, color)
    r = t.get_rect()
    if center_y:
        surf.blit(t, (pos[0], pos[1]-r.height//2))
    else:
        surf.blit(t, pos)
    return r

class Button:
    def __init__(self, rect, label, key=None):
        self.rect = Rect(rect)
        self.label = label
        self.key = key
        self.hover=False
    def draw(self, surf):
        color = BTN_HOVER if self.hover else BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, (90,90,100), self.rect, 1, border_radius=6)
        tr = font.render(self.label, True, BTN_TEXT)
        surf.blit(tr, (self.rect.centerx - tr.get_width()//2, self.rect.centery - tr.get_height()//2))
    def handle(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button==1 and self.rect.collidepoint(e.pos):
            return True
        return False

# App State
playlist = Playlist()
player = Player(playlist)
scroll = 0
selected = set()     # indices
anchor = None        # for shift-range
message = ""         # status line
message_col = FG
message_t = 0

# Buttons
buttons=[]
x = 20; y = 20; w = 90; h = 36; gap = 10
def add_btn(lbl):
    global x
    b = Button((x,y,w,h), lbl)
    buttons.append(b)
    x += w+gap
add_btn("Open")
add_btn("Prev")
add_btn("Play/Pause")
add_btn("Stop")
add_btn("Next")
add_btn("Shuffle")
add_btn("Repeat")
add_btn("Vol-")
add_btn("Vol+")
add_btn("Group/Copy")

def set_message(text, col=FG, hold=180):
    global message, message_col, message_t
    message, message_col, message_t = text, col, hold

def ensure_visible(idx):
    global scroll
    rows = LIST_H//ROW_H
    if idx < scroll:
        scroll = idx
    elif idx >= scroll+rows:
        scroll = max(0, idx - rows + 1)

def play_selected_first():
    if selected:
        idx = sorted(selected)[0]
        player.play(idx)
        ensure_visible(idx)

def toggle_select(idx, ctrl=False, shift=False):
    global anchor
    if not (0<=idx<len(playlist)): return
    if shift and anchor is not None:
        lo = min(anchor, idx); hi = max(anchor, idx)
        for i in range(lo, hi+1):
            selected.add(i)
    elif ctrl:
        if idx in selected: selected.remove(idx)
        else: selected.add(idx)
        anchor = idx
    else:
        selected.clear()
        selected.add(idx)
        anchor = idx

def handle_group_copy():
    if not selected:
        set_message("선택된 곡이 없어요 🙃", ERR); return
    # Ask group name
    grp = simpledialog.askstring("그룹 이름", "폴더에 만들 그룹 이름을 입력하세요:")
    if not grp:
        set_message("취소됨", MUTED); return
    # Ask destination folder
    dest = filedialog.askdirectory(title="복사할 대상 폴더 선택")
    if not dest:
        set_message("취소됨", MUTED); return
    target = os.path.join(dest, grp)
    os.makedirs(target, exist_ok=True)
    paths = [playlist[i] for i in sorted(selected)]
    ok_cnt=0; fail_cnt=0
    for p in paths:
        try:
            base = os.path.basename(p)
            dst = os.path.join(target, base)
            # ensure unique if exists
            root, ext = os.path.splitext(dst)
            k=1
            while os.path.exists(dst):
                dst = f"{root} ({k}){ext}"
                k+=1
            shutil.copy2(p, dst)
            ok_cnt+=1
        except Exception as e:
            print("copy error:", e)
            fail_cnt+=1
    if fail_cnt==0:
        set_message(f"복사 완료! {ok_cnt}곡 → {target}", OK)
    else:
        set_message(f"일부 실패 😵 {ok_cnt} 성공 / {fail_cnt} 실패", ERR)

def draw_ui():
    screen.fill(BG)
    # Title
    draw_text(screen, "Pygame Music Player  —  다중 선택 → Group/Copy", (20, 58), MUTED, font_small)

    # Buttons
    for b in buttons:
        b.draw(screen)

    # Playlist box
    list_r = Rect(LIST_LEFT, LIST_TOP, LIST_W, LIST_H)
    pygame.draw.rect(screen, (30,30,36), list_r, border_radius=8)
    pygame.draw.rect(screen, (70,70,80), list_r, 1, border_radius=8)

    # Items
    rows = LIST_H//ROW_H
    start = scroll
    end = min(len(playlist), start+rows)
    y = LIST_TOP
    mouse_x, mouse_y = pygame.mouse.get_pos()
    for i in range(start, end):
        r = Rect(LIST_LEFT, y, LIST_W - SCROLLBAR_W, ROW_H)
        hovered = r.collidepoint(mouse_x, mouse_y)
        if i in selected:
            pygame.draw.rect(screen, SEL, r)
            pygame.draw.rect(screen, SEL_BORDER, r, 1)
        elif hovered:
            pygame.draw.rect(screen, (40,40,50), r)

        path = playlist[i]
        name = os.path.basename(path)
        # mark current
        prefix = "▶ " if i==player.index and pygame.mixer.music.get_busy() and not player.paused else ("Ⅱ " if i==player.index and player.paused else "   ")
        draw_text(screen, prefix + name, (LIST_LEFT+8, y+5), FG if i in selected else (FG if i==player.index else (210,210,220)))
        y += ROW_H

    # Scrollbar
    if len(playlist)>0:
        total = len(playlist)
        bar_h = max(24, int(LIST_H * (rows / max(rows, total))))
        if total>rows:
            ratio = scroll/(total-rows)
        else:
            ratio = 0
        bar_y = LIST_TOP + int((LIST_H - bar_h) * ratio)
        bar_r = Rect(LIST_LEFT + LIST_W - SCROLLBAR_W, bar_y, SCROLLBAR_W, bar_h)
        pygame.draw.rect(screen, (80,80,95), bar_r, border_radius=6)

    # Timeline
    tl_r = Rect(LIST_LEFT+LIST_W+20, LIST_TOP, CTRL_W-(LIST_LEFT+LIST_W-20), 60)
    pygame.draw.rect(screen, (30,30,36), tl_r, border_radius=8)
    pygame.draw.rect(screen, (70,70,80), tl_r, 1, border_radius=8)
    draw_text(screen, "Timeline (클릭으로 탐색·드래그)", (tl_r.x+10, tl_r.y+8), MUTED, font_small)

    # Progress bar
    pb_r = Rect(tl_r.x+10, tl_r.y+28, tl_r.w-20, 20)
    pygame.draw.rect(screen, (45,45,60), pb_r, border_radius=10)
    # We don't have exact position API reliably; render simple moving dot using get_pos heuristic
    if player.index>=0 and pygame.mixer.music.get_busy():
        # pygame doesn't expose current time reliably; we just keep a simple progress using Sound length if cached
        length = player.length_cache.get(playlist[player.index])
        # draw a static bar if known length
        if length:
            # we can't query current time, so we just draw bar background; knob on click handled separately
            pass
    knob_x = pb_r.x + int(pb_r.w*0.5)
    pygame.draw.circle(screen, ACCENT, (knob_x, pb_r.centery), 6)

    # Now playing + volume / repeat / shuffle
    np_y = LIST_TOP+80
    if 0<=player.index<len(playlist):
        now = os.path.basename(playlist[player.index])
    else:
        now = "(재생 중 아님)"
    draw_text(screen, f"Now: {now}", (LIST_LEFT+LIST_W+20, np_y), FG, font_big)
    draw_text(screen, f"Vol: {int(player.volume*100)}%", (LIST_LEFT+LIST_W+20, np_y+34), FG)
    draw_text(screen, f"Repeat: {['없음','전체','한 곡'][player.repeat_mode]}   Shuffle: {'ON' if player.shuffle else 'OFF'}", (LIST_LEFT+LIST_W+20, np_y+56), FG)

    # Status line
    if message_t>0:
        draw_text(screen, message, (20, WIN_H-28), message_col)
    pygame.display.flip()

def pos_in_list(y):
    rel = y - LIST_TOP
    if rel<0: return None
    idx = scroll + rel//ROW_H
    if 0<=idx<len(playlist):
        return idx
    return None

def handle_open():
    added = playlist.add_from_open_dialog()
    if added>0:
        set_message(f"{added}곡 추가됨 🎵", OK)
    else:
        set_message("추가된 곡 없음", MUTED)

def handle_drop(path):
    added = playlist.add_from_drop(path)
    if added>0:
        set_message(f"{added}곡 추가됨 (드롭)", OK)

def mouse_on_progress(pos):
    tl_r = Rect(LIST_LEFT+LIST_W+20, LIST_TOP, CTRL_W-(LIST_LEFT+LIST_W-20), 60)
    pb_r = Rect(tl_r.x+10, tl_r.y+28, tl_r.w-20, 20)
    return pb_r.collidepoint(pos), pb_r

def main_loop():
    global scroll, message_t
    dragging_prog = False
    prog_rect = None

    running=True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running=False

            elif e.type == pygame.DROPFILE:
                handle_drop(e.file)

            elif e.type == pygame.MOUSEMOTION:
                for b in buttons: b.handle(e)

            elif e.type == pygame.MOUSEBUTTONDOWN:
                # buttons
                for i,b in enumerate(buttons):
                    if b.handle(e):
                        if b.label=="Open": handle_open()
                        elif b.label=="Prev": player.prev()
                        elif b.label=="Play/Pause": player.toggle_pause()
                        elif b.label=="Stop": player.stop()
                        elif b.label=="Next": player.next()
                        elif b.label=="Shuffle": player.set_shuffle()
                        elif b.label=="Repeat": player.set_repeat()
                        elif b.label=="Vol-": player.set_volume(-0.05)
                        elif b.label=="Vol+": player.set_volume(+0.05)
                        elif b.label=="Group/Copy": handle_group_copy()

                # list click
                if e.button in (1,):
                    idx = pos_in_list(e.pos[1])
                    if idx is not None:
                        mods = pygame.key.get_mods()
                        shift = bool(mods & pygame.KMOD_SHIFT)
                        ctrl = bool(mods & (pygame.KMOD_CTRL | pygame.KMOD_META))
                        toggle_select(idx, ctrl=ctrl, shift=shift)
                        if not ctrl and not shift:
                            # single click: play that row
                            player.play(idx)
                            ensure_visible(idx)

                    # progress click
                    hit, pr = mouse_on_progress(e.pos)
                    if hit:
                        dragging_prog = True
                        prog_rect = pr
                        ratio = (e.pos[0]-pr.x)/pr.w
                        ratio = max(0.0,min(1.0,ratio))
                        player.set_pos_ratio(ratio)

                # wheel scroll
                if e.button==4:
                    scroll = max(0, scroll-3)
                elif e.button==5:
                    max_scroll = max(0, len(playlist)- (LIST_H//ROW_H))
                    scroll = min(max_scroll, scroll+3)

            elif e.type == pygame.MOUSEBUTTONUP:
                dragging_prog = False
                prog_rect = None

            elif e.type == pygame.MOUSEMOTION and dragging_prog and prog_rect:
                ratio = (e.pos[0]-prog_rect.x)/prog_rect.w
                ratio = max(0.0,min(1.0,ratio))
                player.set_pos_ratio(ratio)

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE: player.toggle_pause()
                elif e.key == pygame.K_s: player.stop()
                elif e.key == pygame.K_LEFT: player.prev()
                elif e.key == pygame.K_RIGHT: player.next()
                elif e.key == pygame.K_PLUS or e.key==pygame.K_EQUALS: player.set_volume(+0.05)
                elif e.key == pygame.K_MINUS: player.set_volume(-0.05)
                elif e.key == pygame.K_o: handle_open()
                elif e.key == pygame.K_f: player.set_shuffle()
                elif e.key == pygame.K_r: player.set_repeat()
                elif e.key == pygame.K_g: handle_group_copy()

            elif e.type == MUSIC_END:
                player.next()

        if message_t>0:
            message_t -= 1
        draw_ui()
        clock.tick(60)

if __name__=="__main__":
    try:
        main_loop()
    finally:
        pygame.quit()
