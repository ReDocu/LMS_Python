#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UML 스타일 상자(Box) 다이어그램로 디렉토리 구조 시각화 & 조작 툴 (pygame)
=====================================================================

핵심 기능
- 디렉토리/파일을 UML 클래스 다이어그램처럼 "사각형 박스 + 커넥터"로 렌더링
- 클릭 선택, 더블클릭(또는 Space)으로 디렉토리 펼치기/접기
- 새 폴더/파일 생성, 이름 변경, 삭제(확인 다이얼로그)
- 드래그로 캔버스 패닝, Ctrl + 휠로 확대/축소(줌)
- 자동 레이아웃(깊이별 X축 칼럼, 위에서 아래로 균등 Y 배치)

단축키
- R 새로고침   |  Ctrl+N 새 폴더  |  Ctrl+Shift+N 새 파일
- F2 이름 변경 |  Del 삭제        |  Space/더블클릭 펼치기/접기
- Ctrl+0 줌 초기화  |  H 도움말 토글

주의
- 실제 파일 시스템을 변경합니다! 테스트는 샌드박스 디렉토리에서 진행하세요.
"""
from __future__ import annotations
import os
import sys
import time
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional

import pygame

# ===================== 설정 =====================
root_dir = Path.cwd()  # 필요시 원하는 경로로 지정
WINDOW_W, WINDOW_H = 1280, 800
FONT_SIZE = 16
ROW_VSPACE = 16
COL_HSPACE = 240   # 깊이(칼럼) 간 X 간격
BOX_W = 200
BOX_H = 60
BORDER_R = 10

THEME = {
    "bg": (20, 22, 26),
    "grid": (28, 31, 36),
    "box": (36, 40, 48),
    "box_dir": (44, 54, 68),
    "box_file": (40, 44, 52),
    "stroke": (70, 80, 95),
    "conn": (95, 105, 120),
    "text": (232, 236, 241),
    "muted": (148, 155, 164),
    "accent": (99, 179, 237),
    "sel": (120, 200, 145),
    "warn": (237, 98, 107),
    "panel": (28, 31, 36),
    "shadow": (0, 0, 0),
}

# ===================== 데이터 모델 =====================
@dataclass
class Node:
    path: Path
    is_dir: bool
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)
    expanded: bool = True
    # layout
    depth: int = 0
    x: float = 0.0
    y: float = 0.0
    rect: pygame.Rect | None = None

    def refresh_children(self):
        self.children.clear()
        if not self.is_dir:
            return
        try:
            items = sorted(self.path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            items = []
        for p in items:
            n = Node(p, p.is_dir(), parent=self)
            self.children.append(n)

class Tree:
    def __init__(self, root: Path):
        self.root_path = root
        self.root = Node(root, True, None)
        self.root.expanded = True
        self.root.refresh_children()
        self.selected: Node = self.root
        self.flat_visible: List[Node] = []
        self.layout()

    def layout(self):
        """간단 계층 레이아웃: 깊이 기반 X, 가시 노드 순회로 Y 배치."""
        self.flat_visible.clear()
        def collect(n: Node, d: int):
            n.depth = d
            self.flat_visible.append(n)
            if n.is_dir and n.expanded:
                for c in n.children:
                    collect(c, d + 1)
        collect(self.root, 0)
        # Y 위치: 같은 깊이에서 균등하게 내려가며 배치
        y = 0
        for i, n in enumerate(self.flat_visible):
            n.x = n.depth * COL_HSPACE
            n.y = i * (BOX_H + ROW_VSPACE)
            n.rect = pygame.Rect(n.x, n.y, BOX_W, BOX_H)

    def refresh(self, node: Optional[Node] = None):
        if node is None:
            node = self.root
        if node.is_dir:
            node.refresh_children()
        self.layout()

# ===================== 보안/경로 유틸 =====================

def norm_in_root(p: Path) -> Path:
    p = (root_dir / p).resolve()
    rd = root_dir.resolve()
    if rd not in p.parents and p != rd:
        raise ValueError("루트 밖 경로 접근 금지")
    return p

# ===================== UI 요소 =====================
class InputBox:
    def __init__(self, rect: pygame.Rect, font, text="", placeholder=""):
        self.rect = rect
        self.font = font
        self.text = text
        self.placeholder = placeholder
        self.caret = len(text)
        self.active = True
        self.last_blink = 0.0
        self.show_caret = True

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                return "submit"
            if e.key == pygame.K_ESCAPE:
                return "cancel"
            if e.key == pygame.K_BACKSPACE:
                if self.caret > 0:
                    self.text = self.text[: self.caret - 1] + self.text[self.caret :]
                    self.caret -= 1
            elif e.key == pygame.K_DELETE:
                if self.caret < len(self.text):
                    self.text = self.text[: self.caret] + self.text[self.caret + 1 :]
            elif e.key == pygame.K_LEFT:
                self.caret = max(0, self.caret - 1)
            elif e.key == pygame.K_RIGHT:
                self.caret = min(len(self.text), self.caret + 1)
            else:
                if e.unicode and e.unicode.isprintable():
                    self.text = self.text[: self.caret] + e.unicode + self.text[self.caret :]
                    self.caret += 1
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(e.pos):
                return "cancel"
        return None

    def draw(self, surf):
        pygame.draw.rect(surf, THEME["box"], self.rect, border_radius=8)
        pygame.draw.rect(surf, THEME["stroke"], self.rect, 1, border_radius=8)
        txt = self.text if self.text else self.placeholder
        color = THEME["text"] if self.text else THEME["muted"]
        t = self.font.render(txt, True, color)
        surf.blit(t, (self.rect.x + 8, self.rect.y + 6))

# ===================== 앱 =====================
class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("dirviz-uml — UML Box Directory Viz")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        try:
            self.font = pygame.font.SysFont("malgungothic", FONT_SIZE)
        except Exception:
            self.font = pygame.font.SysFont(None, FONT_SIZE)
        self.font_small = pygame.font.SysFont(None, int(FONT_SIZE*0.9))
        self.font_big = pygame.font.SysFont(None, int(FONT_SIZE*1.2))

        self.tree = Tree(root_dir)
        self.running = True

        # 카메라(패닝/줌)
        self.cam_x, self.cam_y = 40.0, 60.0
        self.zoom = 1.0
        self.is_panning = False
        self.pan_start = (0, 0)
        self.cam_start = (0, 0)

        # 모달
        self.modal: Optional[dict] = None
        self.show_help = True

    # ---------- 도우미 ----------
    def world_to_screen(self, x, y):
        return int((x - self.cam_x) * self.zoom), int((y - self.cam_y) * self.zoom)

    def screen_rect(self, rect: pygame.Rect) -> pygame.Rect:
        x, y = self.world_to_screen(rect.x, rect.y)
        w, h = int(rect.w * self.zoom), int(rect.h * self.zoom)
        return pygame.Rect(x, y, w, h)

    def draw_grid(self):
        w, h = self.screen.get_size()
        step = int(40 * self.zoom)
        if step < 25:
            return
        for x in range(0, w, step):
            pygame.draw.line(self.screen, THEME["grid"], (x, 0), (x, h))
        for y in range(0, h, step):
            pygame.draw.line(self.screen, THEME["grid"], (0, y), (w, y))

    # ---------- 렌더 ----------
    
    def draw(self, save_image=False, image_path="output.jpg"):
        self.screen.fill(THEME["bg"])
        self.draw_grid()
        # 커넥터 - 직각 라인
        for n in self.tree.flat_visible:
            if n.parent and n.parent in self.tree.flat_visible:
                a = self.screen_rect(n.parent.rect)
                b = self.screen_rect(n.rect)
                start = (a.right, a.centery)
                end = (b.left, b.centery)
                mid_x = (start[0] + end[0]) // 2
                points = [start, (mid_x, start[1]), (mid_x, end[1]), end]
                pygame.draw.lines(self.screen, THEME["conn"], False, points, 2)
        # 박스
        for n in self.tree.flat_visible:
            r = self.screen_rect(n.rect)
            color = THEME["box_dir"] if n.is_dir else THEME["box_file"]
            shadow = r.copy()
            shadow.x += 4; shadow.y += 4
            pygame.draw.rect(self.screen, THEME["shadow"], shadow, border_radius=BORDER_R)
            pygame.draw.rect(self.screen, color, r, border_radius=BORDER_R)
            border_col = THEME["sel"] if n is self.tree.selected else THEME["stroke"]
            pygame.draw.rect(self.screen, border_col, r, 2, border_radius=BORDER_R)
            name = n.path.name if n.path != root_dir else str(n.path)
            t = self.font.render(("📁 " if n.is_dir else "📄 ") + name, True, THEME["text"])
            self.screen.blit(t, (r.x + 10, r.y + 10))
            sub = self.font_small.render("DIR" if n.is_dir else f"{n.path.stat().st_size} B", True, THEME["muted"])
            self.screen.blit(sub, (r.x + 10, r.bottom - 22))
            if n.is_dir:
                chevron = "▼" if n.expanded else "▶"
                c = self.font.render(chevron, True, THEME["muted"])
                self.screen.blit(c, (r.right - 24, r.y + 8))
        self.draw_header()
        if self.modal:
            self.draw_modal()
        pygame.display.flip()
        # 이미지 저장 기능
        if save_image:
            pygame.image.save(self.screen, image_path)
            print(f"이미지 저장 완료: {image_path}")

    def save_current_view(self, filename="output.jpg"):
        self.draw(save_image=True, image_path=filename)

    def draw_header(self):
        w, _ = self.screen.get_size()
        bar = pygame.Rect(0, 0, w, 44)
        pygame.draw.rect(self.screen, THEME["panel"], bar)
        title = self.font_big.render(f"Root: {root_dir}", True, THEME["text"])
        self.screen.blit(title, (12, 10))
        hint = "R 새로고침  Ctrl+N 폴더  Ctrl+Shift+N 파일  F2 이름변경  Del 삭제  Space/더블클릭 접기/펼치기  Drag 패닝  Ctrl+휠 줌  Ctrl+0 리셋  H 도움말"
        t = self.font_small.render(hint, True, THEME["muted"])
        self.screen.blit(t, (12, 26))
        if self.show_help:
            self.draw_help()

    def draw_help(self):
        w, h = self.screen.get_size()
        rect = pygame.Rect(w-420, 56, 400, 160)
        pygame.draw.rect(self.screen, THEME["panel"], rect, border_radius=10)
        pygame.draw.rect(self.screen, THEME["stroke"], rect, 1, border_radius=10)
        lines = [
            "UML 스타일 박스 다이어그램",
            "- 더블클릭 또는 Space: 폴더 접기/펼치기",
            "- 클릭: 선택",
            "- Ctrl+N / Ctrl+Shift+N: 새 폴더/파일",
            "- F2: 이름 변경  |  Del: 삭제",
            "- Drag: 캔버스 이동  |  Ctrl+휠: 줌",
        ]
        y = rect.y + 10
        for s in lines:
            t = self.font.render(s, True, THEME["text"])
            self.screen.blit(t, (rect.x + 12, y))
            y += 26

    def draw_modal(self):
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(w//2-260, h//2-80, 520, 160)
        pygame.draw.rect(self.screen, THEME["panel"], box, border_radius=10)
        pygame.draw.rect(self.screen, THEME["accent"], box, 2, border_radius=10)
        title = self.font_big.render(self.modal.get("title", ""), True, THEME["text"])
        self.screen.blit(title, (box.x + 16, box.y + 12))
        if self.modal["type"] in ("create", "rename"):
            ib: InputBox = self.modal["input"]
            ib.draw(self.screen)
            hint = self.font_small.render("Enter=확인  Esc=취소", True, THEME["muted"])
            self.screen.blit(hint, (box.x + 16, box.bottom - 26))
        elif self.modal["type"] == "confirm":
            msg = self.modal.get("message", "")
            t = self.font.render(msg, True, THEME["text"])
            self.screen.blit(t, (box.x + 16, box.y + 60))
            hint = self.font_small.render("Y=예  N=아니오", True, THEME["muted"])
            self.screen.blit(hint, (box.x + 16, box.bottom - 26))

    # ---------- 입력 ----------
    def handle(self, e):
        if self.modal:
            self.handle_modal(e)
            return
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if e.key == pygame.K_ESCAPE:
                self.running = False
            elif e.key == pygame.K_r:
                self.tree.refresh()
            elif (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_SHIFT) and e.key == pygame.K_n:
                self.start_create(file=True)
            elif (mods & pygame.KMOD_CTRL) and e.key == pygame.K_n:
                self.start_create(file=False)
            elif e.key == pygame.K_F2:
                self.start_rename()
            elif e.key == pygame.K_DELETE:
                self.start_delete()
            elif e.key == pygame.K_SPACE:
                self.toggle_expand(self.tree.selected)
            elif e.key == pygame.K_h:
                self.show_help = not self.show_help
            elif (mods & pygame.KMOD_CTRL) and e.key == pygame.K_0:
                self.zoom = 1.0; self.cam_x, self.cam_y = 40.0, 60.0
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                self.on_left_click(e.pos)
            elif e.button == 3:
                self.is_panning = True
                self.pan_start = e.pos
                self.cam_start = (self.cam_x, self.cam_y)
            elif e.button == 4 and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.zoom *= 1.1
            elif e.button == 5 and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.zoom /= 1.1
        elif e.type == pygame.MOUSEBUTTONUP:
            if e.button == 3:
                self.is_panning = False
        elif e.type == pygame.MOUSEMOTION and self.is_panning:
            dx, dy = e.pos[0] - self.pan_start[0], e.pos[1] - self.pan_start[1]
            self.cam_x = self.cam_start[0] - dx / self.zoom
            self.cam_y = self.cam_start[1] - dy / self.zoom
        elif e.type == pygame.MOUSEWHEEL and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
            # 일반 휠은 세로 스크롤처럼 카메라 이동
            self.cam_y -= e.y * 40 / self.zoom

    def handle_modal(self, e):
        mtype = self.modal["type"]
        if mtype in ("create", "rename"):
            res = self.modal["input"].handle(e)
            if res == "submit":
                txt = self.modal["input"].text.strip()
                try:
                    if mtype == "create":
                        self.do_create(self.modal["file"], txt)
                    else:
                        self.do_rename(txt)
                except Exception as exc:
                    print("[오류]", exc)
                self.modal = None
            elif res == "cancel":
                self.modal = None
        elif mtype == "confirm":
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_y, pygame.K_RETURN):
                    try:
                        self.do_delete()
                    except Exception as exc:
                        print("[오류]", exc)
                    self.modal = None
                elif e.key in (pygame.K_n, pygame.K_ESCAPE):
                    self.modal = None

    # ---------- 액션 ----------
    def on_left_click(self, pos):
        # 화면 좌표 → 월드 좌표 박스 찾기
        mx, my = pos
        for n in reversed(self.tree.flat_visible):  # 위에 그린 것부터 선택
            r = self.screen_rect(n.rect)
            if r.collidepoint(mx, my):
                # 더블클릭 체크(간단)
                now = time.time()
                if hasattr(self, "_last_click") and getattr(self, "_last_click_node", None) is n and now - self._last_click < 0.35:
                    self.toggle_expand(n)
                self._last_click = now
                self._last_click_node = n
                self.tree.selected = n
                return

    def toggle_expand(self, n: Node):
        if not n.is_dir:
            return
        n.expanded = not n.expanded
        if n.expanded:
            n.refresh_children()
        self.tree.layout()

    def start_create(self, file=False):
        target = self.tree.selected if self.tree.selected.is_dir else (self.tree.selected.parent or self.tree.selected)
        title = "새 파일 만들기" if file else "새 폴더 만들기"
        box = InputBox(pygame.Rect(self.screen.get_width()//2 - 220, self.screen.get_height()//2, 440, 40), self.font, "", "이름 입력")
        self.modal = {"type": "create", "title": title, "input": box, "file": file, "target": target}

    def do_create(self, is_file: bool, name: str):
        target: Node = self.modal["target"]
        parent = target if target.is_dir else (target.parent or target)
        parent_path = norm_in_root(parent.path)
        new_path = norm_in_root(parent_path / name)
        if is_file:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            with open(new_path, "x", encoding="utf-8") as f:
                pass
        else:
            new_path.mkdir()
        parent.refresh_children()
        self.tree.layout()

    def start_rename(self):
        n = self.tree.selected
        box = InputBox(pygame.Rect(self.screen.get_width()//2 - 220, self.screen.get_height()//2, 440, 40), self.font, n.path.name, "")
        self.modal = {"type": "rename", "title": "이름 바꾸기", "input": box, "target": n}

    def do_rename(self, new_name: str):
        n: Node = self.modal["target"]
        new_path = norm_in_root(n.path.parent / new_name)
        n.path.rename(new_path)
        n.path = new_path
        if n.parent:
            n.parent.refresh_children()
        self.tree.layout()

    def start_delete(self):
        n = self.tree.selected
        if n.path == root_dir:
            print("루트는 삭제할 수 없습니다")
            return
        self.modal = {"type": "confirm", "title": "삭제 확인", "message": f"정말 삭제할까요? {n.path.name}", "target": n}

    def do_delete(self):
        n: Node = self.modal["target"]
        p = norm_in_root(n.path)
        if n.is_dir:
            shutil.rmtree(p)
        else:
            p.unlink()
        if n.parent:
            n.parent.refresh_children()
            self.tree.selected = n.parent
        self.tree.layout()

    # ---------- 루프 ----------
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            for e in pygame.event.get():
                self.handle(e)
            self.draw()
            clock.tick(60)
        pygame.quit()


# 실행 예시: 현재 디렉토리 구조를 jpg로 저장
if __name__ == "__main__":
    try:
        norm_in_root(root_dir)
    except Exception:
        print("루트 경로 확인 실패. root_dir 값을 점검하세요.")
        sys.exit(1)
    app = App()
    app.draw(save_image=True, image_path="directory_structure.jpg")
    app.run()

