#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pygame Music Player
-------------------
간단하지만 꽤 쓸만한 음악 플레이어.

기능
- 폴더 열기(O) 또는 파일 드롭으로 재생목록 만들기 (mp3/ogg/wav/flac 일부 코덱 환경에 따라)
- 재생/일시정지, 정지, 다음/이전 트랙
- 셔플, 반복(전체/한곡) 토글
- 볼륨 슬라이더 및 키보드 +/-로 볼륨 조절
- 진행바 클릭으로 탐색(포맷/코덱별로 정확도 차이 있음)
- 좌측 재생목록 클릭/스크롤로 선택 & 재생

의존성
- pygame (pip install pygame)
- 추가 코덱은 OS 에 설치된 SDL_mixer/코덱에 의존

실행
- python pygame_music_player.py

키보드 단축키
- Space : 재생/일시정지 토글
- S     : 정지
- Left/Right : 이전/다음 트랙
- +/-   : 볼륨 조절
- O     : 폴더 열기(파일 선택 창)
- R     : 반복 모드 토글 (없음→전체→한곡)
- F     : 셔플 토글

주의
- mixer.music.set_pos 지원은 포맷/코덱에 따라 정확하지 않을 수 있음.
- 총 길이 계산은 일부 포맷에서 실패할 수 있으며, 실패 시 '??:??'로 표기됩니다.
"""

import os
import sys
import random
import time
import math
import tkinter as tk
from tkinter import filedialog

import pygame

# --------- 유틸 ---------
SUPPORTED_EXTS = {'.mp3', '.ogg', '.wav', '.flac', '.mod', '.xm', '.it', '.s3m'}

def list_audio_files(path):
    files = []
    if os.path.isdir(path):
        for root, _, fnames in os.walk(path):
            for f in fnames:
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                    files.append(os.path.join(root, f))
    elif os.path.isfile(path):
        if os.path.splitext(path)[1].lower() in SUPPORTED_EXTS:
            files.append(path)
    return sorted(files)


def format_time(seconds):
    if seconds is None or seconds <= 0:
        return "??:??"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def safe_get_length(path):
    """pygame.mixer.Sound 길이 얻기. mp3에서 실패 가능. 실패 시 None."""
    try:
        snd = pygame.mixer.Sound(path)
        return snd.get_length()
    except Exception:
        return None

# --------- 플레이어 로직 ---------
class RepeatMode:
    NONE = 0
    ALL = 1
    ONE = 2

class MusicPlayer:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        self.playlist = []             # list[str]
        self.play_index = -1
        self.is_paused = False
        self.shuffle = False
        self.repeat_mode = RepeatMode.NONE
        self.volume = 0.7
        pygame.mixer.music.set_volume(self.volume)
        self.track_lengths = {}        # path -> seconds or None
        self.track_started_at = 0.0    # epoch time when unpaused
        self.accumulated_pos = 0.0     # seconds accumulated before last play

    # ---- 재생목록 관리 ----
    def set_playlist(self, files):
        self.stop()
        self.playlist = files[:]
        self.play_index = 0 if files else -1
        self._preload_lengths()

    def add_files(self, files):
        for f in files:
            if f not in self.playlist:
                self.playlist.append(f)
        if self.play_index == -1 and self.playlist:
            self.play_index = 0
        self._preload_lengths()

    def _preload_lengths(self):
        for f in self.playlist:
            if f not in self.track_lengths:
                self.track_lengths[f] = safe_get_length(f)

    # ---- 재생 제어 ----
    def play(self, index=None):
        if not self.playlist:
            return
        if index is not None:
            self.play_index = max(0, min(index, len(self.playlist)-1))
        path = self.playlist[self.play_index]
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self.is_paused = False
            self.accumulated_pos = 0.0
            self.track_started_at = time.time()
        except Exception as e:
            print("재생 실패:", e)

    def toggle_pause(self):
        if not pygame.mixer.music.get_busy():
            # 정지 상태면 재생 시도
            if self.play_index != -1:
                self.play(self.play_index)
            return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.track_started_at = time.time()
        else:
            pygame.mixer.music.pause()
            self.is_paused = True
            # 누적 진행
            self.accumulated_pos = self.get_pos_seconds()

    def stop(self):
        pygame.mixer.music.stop()
        self.is_paused = False
        self.accumulated_pos = 0.0
        self.track_started_at = 0.0

    def next(self):
        if not self.playlist:
            return
        if self.shuffle:
            candidates = list(range(len(self.playlist)))
            if self.play_index in candidates:
                candidates.remove(self.play_index)
            if candidates:
                self.play_index = random.choice(candidates)
        else:
            self.play_index = (self.play_index + 1) % len(self.playlist)
        self.play(self.play_index)

    def prev(self):
        if not self.playlist:
            return
        if self.shuffle:
            # shuffle에서는 그냥 랜덤
            self.play_index = random.randrange(len(self.playlist))
        else:
            self.play_index = (self.play_index - 1) % len(self.playlist)
        self.play(self.play_index)

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        pygame.mixer.music.set_volume(self.volume)

    def get_pos_seconds(self):
        # get_pos 는 ms. 일시정지/언포즈 사이 정확도 한계 있음
        if self.is_paused:
            return self.accumulated_pos
        ms = pygame.mixer.music.get_pos()
        if ms < 0:
            ms = 0
        # 일부 포맷에서 언포즈 후 0부터 다시 세는 이슈가 있어 보정치로 epoch 기반 누적 사용
        if self.track_started_at > 0:
            elapsed = time.time() - self.track_started_at
            return self.accumulated_pos + elapsed
        return ms / 1000.0

    def seek(self, seconds):
        if self.play_index == -1 or not self.playlist:
            return
        length = self.track_lengths.get(self.playlist[self.play_index])
        if length is not None:
            seconds = max(0.0, min(seconds, length - 0.2))
        try:
            pygame.mixer.music.play(start=seconds)
            self.is_paused = False
            self.accumulated_pos = seconds
            self.track_started_at = time.time()
        except Exception:
            # 일부 포맷에서 set_pos 미지원
            pass

    def on_track_end(self):
        if self.repeat_mode == RepeatMode.ONE:
            self.play(self.play_index)
        elif self.repeat_mode == RepeatMode.ALL:
            self.next()
        else:
            # 없음: 마지막 곡이면 정지, 아니면 다음
            if self.play_index == len(self.playlist) - 1:
                self.stop()
            else:
                self.next()

# --------- UI ---------
class UI:
    WIDTH = 960
    HEIGHT = 600
    BG = (20, 22, 25)
    FG = (240, 240, 240)
    ACCENT = (90, 180, 255)
    MUTED = (140, 140, 150)

    def __init__(self, player: MusicPlayer):
        pygame.init()
        pygame.display.set_caption("Pygame Music Player")
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgungothic" if sys.platform == "win32" else None, 18)
        self.font_small = pygame.font.SysFont("malgungothic" if sys.platform == "win32" else None, 14)

        self.player = player

        # 레이아웃
        self.sidebar_rect = pygame.Rect(0, 0, 360, self.HEIGHT)
        self.controls_rect = pygame.Rect(self.sidebar_rect.right, self.HEIGHT - 120, self.WIDTH - self.sidebar_rect.width, 120)
        self.content_rect = pygame.Rect(self.sidebar_rect.right, 0, self.WIDTH - self.sidebar_rect.width, self.HEIGHT - self.controls_rect.height)

        self.list_scroll = 0
        self.item_height = 28

        # 진행바/볼륨바
        self.progress_rect = pygame.Rect(self.controls_rect.left + 20, self.controls_rect.top + 20, self.controls_rect.width - 40, 14)
        self.volume_rect = pygame.Rect(self.controls_rect.left + 80, self.controls_rect.top + 60, self.controls_rect.width - 160, 10)

        # 버튼 영역 정의
        cx = self.controls_rect.left + 20
        cy = self.controls_rect.top + 88
        self.btn_prev = pygame.Rect(cx, cy - 16, 40, 32); cx += 50
        self.btn_play = pygame.Rect(cx, cy - 16, 60, 32); cx += 70
        self.btn_next = pygame.Rect(cx, cy - 16, 40, 32); cx += 50
        self.btn_stop = pygame.Rect(cx, cy - 16, 50, 32); cx += 60
        self.btn_shuffle = pygame.Rect(cx, cy - 16, 70, 32); cx += 80
        self.btn_repeat = pygame.Rect(cx, cy - 16, 70, 32)

        # 파일 드롭 활성화
        try:
            pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL, pygame.DROPFILE, pygame.USEREVENT])
        except Exception:
            pass
        # 곡 종료 이벤트
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)

    # ---- 렌더 ----
    def draw(self):
        self.screen.fill(self.BG)
        self.draw_sidebar()
        self.draw_content()
        self.draw_controls()
        pygame.display.flip()

    def draw_sidebar(self):
        # 배경
        pygame.draw.rect(self.screen, (28, 30, 34), self.sidebar_rect)
        # 타이틀
        self.blit_text("재생목록 (O로 폴더 열기, 파일 드롭 가능)", 12, 10, color=self.FG)

        # 아이템 영역
        list_area = self.sidebar_rect.inflate(-12, -48)
        list_area.topleft = (6, 40)

        # 스크롤 가능한 영역 계산
        start_y = list_area.top + self.list_scroll
        for idx, path in enumerate(self.player.playlist):
            item_rect = pygame.Rect(list_area.left, start_y + idx * self.item_height, list_area.width, self.item_height - 2)
            if item_rect.bottom < list_area.top or item_rect.top > list_area.bottom:
                continue
            # 배경
            bg = (45, 48, 54) if idx % 2 == 0 else (38, 40, 45)
            if idx == self.player.play_index:
                bg = (60, 90, 120)
            pygame.draw.rect(self.screen, bg, item_rect, border_radius=6)

            # 파일명
            name = os.path.basename(path)
            self.blit_text(name, item_rect.left + 8, item_rect.top + 6, color=self.FG)

        # 스크롤 경계선
        pygame.draw.line(self.screen, (70, 70, 75), (self.sidebar_rect.right-1, 0), (self.sidebar_rect.right-1, self.sidebar_rect.bottom))

    def draw_content(self):
        pygame.draw.rect(self.screen, (24, 26, 30), self.content_rect)
        # 현재 곡 정보
        title = "(재생 대기)" if self.player.play_index == -1 else os.path.basename(self.player.playlist[self.player.play_index])
        self.blit_text(title, self.content_rect.left + 16, self.content_rect.top + 16, color=self.FG)

        # 길이/진행 시간
        if self.player.play_index != -1:
            path = self.player.playlist[self.player.play_index]
            total = self.player.track_lengths.get(path)
            pos = self.player.get_pos_seconds()
            self.blit_text(f"{format_time(pos)} / {format_time(total)}", self.content_rect.left + 16, self.content_rect.top + 48, color=self.MUTED, small=True)

    def draw_controls(self):
        pygame.draw.rect(self.screen, (18, 20, 23), self.controls_rect)
        # 진행 바
        pygame.draw.rect(self.screen, (50, 54, 60), self.progress_rect, border_radius=5)
        # 진행 채움
        frac = 0.0
        if self.player.play_index != -1:
            path = self.player.playlist[self.player.play_index]
            total = self.player.track_lengths.get(path)
            pos = self.player.get_pos_seconds()
            if total and total > 0:
                frac = max(0.0, min(1.0, pos / total))
        fill_rect = self.progress_rect.copy()
        fill_rect.width = int(self.progress_rect.width * frac)
        pygame.draw.rect(self.screen, self.ACCENT, fill_rect, border_radius=5)

        # 볼륨 바
        pygame.draw.rect(self.screen, (50, 54, 60), self.volume_rect, border_radius=5)
        knob_x = int(self.volume_rect.left + self.player.volume * self.volume_rect.width)
        pygame.draw.circle(self.screen, self.ACCENT, (knob_x, self.volume_rect.centery), 8)
        self.blit_text(f"VOL {int(self.player.volume*100)}%", self.volume_rect.right - 70, self.volume_rect.top - 18, color=self.MUTED, small=True)

        # 버튼들
        self.draw_button(self.btn_prev, "⏮")
        self.draw_button(self.btn_play, "⏯" if pygame.mixer.music.get_busy() and not self.player.is_paused else "▶")
        self.draw_button(self.btn_next, "⏭")
        self.draw_button(self.btn_stop, "⏹")
        self.draw_button(self.btn_shuffle, "🔀 ON" if self.player.shuffle else "🔀 OFF")
        rep_text = {RepeatMode.NONE: "🔁 OFF", RepeatMode.ALL: "🔁 ALL", RepeatMode.ONE: "🔂 ONE"}[self.player.repeat_mode]
        self.draw_button(self.btn_repeat, rep_text)

    def draw_button(self, rect, label):
        pygame.draw.rect(self.screen, (40, 44, 50), rect, border_radius=8)
        pygame.draw.rect(self.screen, (70, 74, 80), rect, width=2, border_radius=8)
        self.blit_text_center(label, rect, color=self.FG)

    def blit_text(self, text, x, y, color=FG, small=False):
        surf = (self.font_small if small else self.font).render(text, True, color)
        self.screen.blit(surf, (x, y))

    def blit_text_center(self, text, rect, color=FG, small=False):
        surf = (self.font_small if small else self.font).render(text, True, color)
        r = surf.get_rect(center=rect.center)
        self.screen.blit(surf, r)

    # ---- 이벤트 처리 ----
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    self.player.toggle_pause()
                elif e.key == pygame.K_s:
                    self.player.stop()
                elif e.key == pygame.K_RIGHT:
                    self.player.next()
                elif e.key == pygame.K_LEFT:
                    self.player.prev()
                elif e.key == pygame.K_PLUS or e.key == pygame.K_EQUALS:  # '=' on many layouts
                    self.player.set_volume(self.player.volume + 0.05)
                elif e.key == pygame.K_MINUS:
                    self.player.set_volume(self.player.volume - 0.05)
                elif e.key == pygame.K_o:
                    self.open_folder_dialog()
                elif e.key == pygame.K_r:
                    # 반복 토글
                    self.player.repeat_mode = (self.player.repeat_mode + 1) % 3
                elif e.key == pygame.K_f:
                    self.player.shuffle = not self.player.shuffle
            elif e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = e.pos
                if e.button == 1:
                    if self.btn_prev.collidepoint(mx, my):
                        self.player.prev()
                    elif self.btn_play.collidepoint(mx, my):
                        self.player.toggle_pause()
                    elif self.btn_next.collidepoint(mx, my):
                        self.player.next()
                    elif self.btn_stop.collidepoint(mx, my):
                        self.player.stop()
                    elif self.btn_shuffle.collidepoint(mx, my):
                        self.player.shuffle = not self.player.shuffle
                    elif self.btn_repeat.collidepoint(mx, my):
                        self.player.repeat_mode = (self.player.repeat_mode + 1) % 3
                    elif self.progress_rect.collidepoint(mx, my):
                        self.handle_seek(mx)
                    elif self.volume_rect.collidepoint(mx, my):
                        self.handle_volume_drag(mx)
                    else:
                        self.handle_list_click(mx, my)
                elif e.button == 4:  # wheel up
                    self.list_scroll = min(self.list_scroll + 40, 0)
                elif e.button == 5:  # wheel down
                    # 리스트 총 높이 계산 (대략)
                    total_h = len(self.player.playlist) * self.item_height
                    view_h = self.sidebar_rect.height - 60
                    min_scroll = min(0, view_h - total_h)
                    self.list_scroll = max(self.list_scroll - 40, min_scroll)
            elif e.type == pygame.MOUSEWHEEL:
                # 일부 플랫폼에서 MOUSEWHEEL 사용
                dy = e.y
                if dy > 0:
                    self.list_scroll = min(self.list_scroll + 40, 0)
                elif dy < 0:
                    total_h = len(self.player.playlist) * self.item_height
                    view_h = self.sidebar_rect.height - 60
                    min_scroll = min(0, view_h - total_h)
                    self.list_scroll = max(self.list_scroll - 40, min_scroll)
            elif e.type == pygame.DROPFILE:
                path = e.file
                files = list_audio_files(path)
                if files:
                    if not self.player.playlist:
                        self.player.set_playlist(files)
                        self.player.play(0)
                    else:
                        self.player.add_files(files)
            elif e.type == pygame.USEREVENT + 1:
                # 곡 종료
                self.player.on_track_end()
        return True

    def handle_seek(self, mx):
        if self.player.play_index == -1:
            return
        frac = (mx - self.progress_rect.left) / self.progress_rect.width
        frac = max(0.0, min(1.0, frac))
        path = self.player.playlist[self.player.play_index]
        total = self.player.track_lengths.get(path)
        if total and total > 1.0:
            self.player.seek(total * frac)

    def handle_volume_drag(self, mx):
        frac = (mx - self.volume_rect.left) / self.volume_rect.width
        self.player.set_volume(frac)

    def handle_list_click(self, mx, my):
        # 리스트 영역
        list_area = self.sidebar_rect.inflate(-12, -48)
        list_area.topleft = (6, 40)
        if not list_area.collidepoint(mx, my):
            return
        y_local = my - list_area.top - self.list_scroll
        idx = int(y_local // self.item_height)
        if 0 <= idx < len(self.player.playlist):
            self.player.play(idx)

    def open_folder_dialog(self):
        root = tk.Tk()
        root.withdraw()
        folder = filedialog.askdirectory(title="음악 폴더 선택")
        root.update()
        root.destroy()
        if folder:
            files = list_audio_files(folder)
            if files:
                self.player.set_playlist(files)
                self.player.play(0)

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(60)


def main():
    player = MusicPlayer()
    ui = UI(player)

    # 커맨드라인 인자(폴더/파일)로 초기 로드
    if len(sys.argv) > 1:
        files = []
        for p in sys.argv[1:]:
            files.extend(list_audio_files(p))
        if files:
            player.set_playlist(files)
            player.play(0)

    ui.run()


if __name__ == "__main__":
    main()
