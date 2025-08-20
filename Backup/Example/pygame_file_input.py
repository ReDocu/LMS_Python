# rename_images_pygame.py
# -*- coding: utf-8 -*-
import os
import sys
import uuid
import pygame
from pathlib import Path
from typing import List, Tuple

# -------- 설정 --------
WIN_SIZE = (900, 520)
BG = (18, 18, 20)
FG = (235, 235, 240)
MUTED = (160, 160, 170)
ACCENT = (120, 200, 255)
OK = (90, 200, 140)
ERR = (250, 120, 120)

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

HELP_TEXT = [
    "1) 폴더를 창으로 드래그 앤 드롭 하세요 (폴더 경로만 가능)",
    "   또는, 아래 입력창에 폴더 경로를 타이핑 후 [Enter]",
    "2) [RENAME] 버튼을 클릭하면 1, 2, 3... 으로 일괄 변경됩니다.",
    "   - 확장자는 그대로 유지됩니다 (예: 1.jpg, 2.png)",
    "   - 충돌 방지를 위해 임시 폴더로 이동 후 안전하게 처리합니다.",
    "   - 대상은 이미지 확장자 파일만입니다.",
]

pygame.init()
pygame.display.set_caption("Image Renamer (pygame only)")
screen = pygame.display.set_mode(WIN_SIZE)
clock = pygame.time.Clock()
font = pygame.font.SysFont("malgun gothic", 18)
font_small = pygame.font.SysFont("malgun gothic", 14)
font_mono = pygame.font.SysFont("consolas", 16)

# UI rects
INPUT_RECT = pygame.Rect(20, 80, WIN_SIZE[0] - 40, 36)
BTN_RECT = pygame.Rect(20, 130, 140, 36)
PREVIEW_RECT = pygame.Rect(20, 185, WIN_SIZE[0] - 40, WIN_SIZE[1] - 205)

input_text = ""
selected_dir: Path | None = None
message = ""
message_color = MUTED
preview_pairs: List[Tuple[str, str]] = []  # (old_name, new_name)
file_count = 0

def draw_text(surf, text, pos, color=FG, fnt=font):
    surf.blit(fnt.render(text, True, color), pos)

def list_images(folder: Path) -> List[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS],
        key=lambda p: p.name.lower(),
    )

def next_available_name(folder: Path, base: str, ext: str) -> Path:
    """
    base는 '1' 같은 숫자 문자열. 같은 이름이 이미 있으면 '1 (1)', '1 (2)'... 로 피해감.
    """
    candidate = folder / f"{base}{ext}"
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = folder / f"{base} ({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1

def build_preview(folder: Path) -> Tuple[List[Tuple[str, str]], int]:
    imgs = list_images(folder)
    pairs = []
    for idx, p in enumerate(imgs, start=1):
        pairs.append((p.name, f"{idx}{p.suffix}"))
    return pairs, len(imgs)

def rename_images(folder: Path) -> Tuple[int, List[Tuple[str, str]], List[str]]:
    """
    실작업 수행.
    1) __rename_tmp__<uuid> 하위폴더로 모두 이동
    2) 1.ext, 2.ext ... 로 이름 매기며 다시 상위로 이동
    충돌 시 ' (1)', ' (2)'로 회피.
    반환: (성공개수, [(old->new)], [오류메시지])
    """
    imgs = list_images(folder)
    if not imgs:
        return 0, [], ["이미지 파일이 없습니다."]

    tmp_dir = folder / ("__rename_tmp__" + uuid.uuid4().hex)
    tmp_dir.mkdir(exist_ok=False)

    moved: List[Path] = []
    mapping: List[Tuple[str, str]] = []
    errors: List[str] = []

    try:
        # 1) 임시 폴더로 이동
        for p in imgs:
            dst = tmp_dir / p.name
            try:
                os.replace(p, dst)  # 원자적 이동 시도
                moved.append(dst)
            except Exception as e:
                errors.append(f"이동 실패: {p.name} -> {e}")

        # 2) 순차명으로 상위로 되돌리기
        success = 0
        for idx, p in enumerate(sorted(moved, key=lambda x: x.name.lower()), start=1):
            ext_preserve = p.suffix  # 확장자 유지 (대소문자 포함 원본 유지)
            target = next_available_name(folder, str(idx), ext_preserve)
            try:
                os.replace(p, target)
                success += 1
                mapping.append((p.name, target.name))
            except Exception as e:
                errors.append(f"이름 변경 실패: {p.name} -> {target.name}: {e}")

        # 로그 남기기
        try:
            log_path = folder / "renaming_log.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("[Image Renamer Log]\n")
                f.write(f"총 대상: {len(imgs)}개, 성공: {success}개\n\n")
                for old, new in mapping:
                    f.write(f"{old} -> {new}\n")
                if errors:
                    f.write("\n[오류]\n")
                    for err in errors:
                        f.write(f"- {err}\n")
        except Exception:
            # 로그 실패는 치명적이지 않으니 무시
            pass

        return success, mapping, errors
    finally:
        # 임시 폴더가 비어 있으면 삭제 시도
        try:
            if tmp_dir.exists() and not any(tmp_dir.iterdir()):
                tmp_dir.rmdir()
        except Exception:
            pass

def set_selected_dir(path_str: str):
    global selected_dir, preview_pairs, file_count, message, message_color, input_text
    p = Path(path_str.strip('"')).expanduser()
    if p.exists() and p.is_dir():
        selected_dir = p
        preview_pairs, file_count = build_preview(p)
        input_text = str(p)
        if file_count == 0:
            message = "폴더는 찾았지만, 이미지 파일이 없어요."
            message_color = ERR
        else:
            message = f"준비 완료! 이미지 {file_count}개 발견."
            message_color = OK
    else:
        selected_dir = None
        preview_pairs, file_count = [], 0
        message = "유효한 폴더 경로가 아닙니다."
        message_color = ERR

def handle_drop(path_str: str):
    # SDL_DROPFILE는 파일/폴더 모두 올 수 있음. 폴더만 허용.
    p = Path(path_str)
    if p.is_dir():
        set_selected_dir(str(p))
    else:
        # 파일을 드래그하면 그 파일의 상위 폴더를 자동 선택하는 옵션
        set_selected_dir(str(p.parent))

running = True
cursor_visible = True
cursor_timer = 0

while running:
    dt = clock.tick(60)
    cursor_timer += dt
    if cursor_timer >= 500:
        cursor_timer = 0
        cursor_visible = not cursor_visible

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 드롭 이벤트 (pygame 2.x)
        if event.type == pygame.DROPFILE:
            handle_drop(event.file)

        # 마우스 클릭
        if event.type == pygame.MOUSEBUTTONDOWN:
            if BTN_RECT.collidepoint(event.pos):
                if selected_dir and file_count > 0:
                    cnt, mapping, errs = rename_images(selected_dir)
                    if cnt > 0:
                        message = f"이름 변경 완료! {cnt}개 성공"
                        message_color = OK
                        # 완료 후 미리보기 업데이트
                        preview_pairs, file_count = build_preview(selected_dir)
                    else:
                        message = "변경할 이미지가 없거나 실패했어요."
                        message_color = ERR
                        if errs:
                            message += f" (오류 {len(errs)}건)"
                else:
                    message = "먼저 유효한 폴더를 선택하세요."
                    message_color = ERR

            # 입력창 포커스 느낌만 주기 위해 클릭 체크 (실제 포커스 개념은 없음)
            if INPUT_RECT.collidepoint(event.pos):
                pass

        # 키 입력 (경로 타이핑)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if input_text.strip():
                    set_selected_dir(input_text)
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_ESCAPE:
                running = False
            else:
                # 붙여넣기(Ctrl+V) 처리: pygame에서는 키로 직접 처리
                if (event.key == pygame.K_v) and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    try:
                        # pygame.scrap은 플랫폼 의존적이라, 여기서는 OS 클립보드 미사용.
                        # 대신 사용자에게 직접 Ctrl+V로 경로 타이핑 들어오는 수준만 처리.
                        pass
                    except Exception:
                        pass
                else:
                    # 일반 문자
                    ch = event.unicode
                    if ch:
                        input_text += ch

    # --- Render ---
    screen.fill(BG)

    draw_text(screen, "Image Renamer (pygame only)", (20, 20), ACCENT)
    for i, line in enumerate(HELP_TEXT):
        draw_text(screen, line, (20, 40 + i * 18), MUTED, font_small)

    # 입력창
    pygame.draw.rect(screen, (40, 40, 48), INPUT_RECT, border_radius=6)
    pygame.draw.rect(screen, (70, 70, 80), INPUT_RECT, width=1, border_radius=6)
    txt = input_text + ("|" if cursor_visible else "")
    screen.blit(font_mono.render(txt, True, FG), (INPUT_RECT.x + 10, INPUT_RECT.y + 8))

    # 버튼
    pygame.draw.rect(screen, (40, 80, 60), BTN_RECT, border_radius=6)
    pygame.draw.rect(screen, (70, 150, 110), BTN_RECT, width=1, border_radius=6)
    draw_text(screen, "RENAME", (BTN_RECT.x + 28, BTN_RECT.y + 8), (220, 255, 230))

    # 상태 메시지
    draw_text(screen, message, (180, 138), message_color)

    # 선택 폴더 표시
    sel = f"선택된 폴더: {selected_dir}" if selected_dir else "선택된 폴더: (없음)"
    draw_text(screen, sel, (20, 172), MUTED, font_small)

    # 미리보기 박스
    pygame.draw.rect(screen, (28, 28, 32), PREVIEW_RECT, border_radius=8)
    pygame.draw.rect(screen, (60, 60, 70), PREVIEW_RECT, width=1, border_radius=8)
    draw_text(screen, "미리보기 (상위 20개):", (PREVIEW_RECT.x + 12, PREVIEW_RECT.y + 8), FG)

    y = PREVIEW_RECT.y + 32
    if preview_pairs:
        for old, new in preview_pairs[:20]:
            screen.blit(font_small.render(f"{old}  →  {new}", True, (210, 210, 220)), (PREVIEW_RECT.x + 16, y))
            y += 18
        if file_count > 20:
            draw_text(screen, f"... 외 {file_count - 20}개", (PREVIEW_RECT.x + 16, y + 6), MUTED, font_small)
    else:
        draw_text(screen, "표시할 항목이 없습니다.", (PREVIEW_RECT.x + 16, y), MUTED, font_small)

    pygame.display.flip()

pygame.quit()
