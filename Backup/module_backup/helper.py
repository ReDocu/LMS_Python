import pygame
from core.camera import Camera
from core.renderer import Renderer
from core.assets import load_image, load_font
from gfx.images import draw_image
from gfx.shapes import rect as draw_rect, circle as draw_circle, line as draw_line
from gfx.text import draw_text
from physics.collision import rect_rect, overlap_amount
from ui.debug import draw_fps

from assets_model import AssetModel

pygame.init()
W, H = 960, 540
screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()

cam = Camera(pos=(0, 0), zoom=1.0)
renderer = Renderer(screen, cam)

# 에셋
player_img = load_image("player.png") if False else pygame.Surface((48,48)); player_img.fill((80,180,250))
enemy_img  = load_image("enemy.png")  if False else pygame.Surface((48,48)); enemy_img.fill((250,120,120))

# 한글 폰트 로드 (Windows 맑은 고딕 예시)
font_path = "C:/Windows/Fonts/malgun.ttf"
font = load_font(font_path, 20)  # 시스템 기본 폰트

player = pygame.Rect(100, 100, 48, 48)
enemy  = pygame.Rect(260, 120, 48, 48)

running = True
speed = 200

# Model
model = AssetModel(base_dir=".")
model.subscribe(lambda ev, p: print("[EVENT]", ev, p))  # 디버그 로그

while running:
    dt = clock.tick(144)/1000.0
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    # 입력
    keys = pygame.key.get_pressed()
    move_x = (keys[pygame.K_d]-keys[pygame.K_a]) * speed * dt
    move_y = (keys[pygame.K_s]-keys[pygame.K_w]) * speed * dt
    player.x += move_x
    player.y += move_y

    # 카메라는 플레이어를 따라감
    cam.pos.x = player.centerx - W/2 / cam.zoom
    cam.pos.y = player.centery - H/2 / cam.zoom

    # 충돌 체크 + 간단 해결
    if rect_rect(player, enemy):
        ox, oy = overlap_amount(player, enemy)
        player.x += ox
        player.y += oy

    # ---- Render ----
    renderer.clear((18,22,30))

    # 월드 그리기 (카메라 적용)
    draw_rect(renderer, (40,50,70), (0, 300, 800, 30), 0, use_camera=True)           # 바닥
    draw_line(renderer, (90,120,200), (0, 300), (800, 300), 2, use_camera=True)

    # 스프라이트
    renderer.blit(player_img, (player.x, player.y))                                   # 플레이어
    renderer.blit(enemy_img,  (enemy.x, enemy.y))                                     # 적

    # 디버그 충돌 박스
    draw_rect(renderer, (80,200,255), player, 2, use_camera=True)
    draw_rect(renderer, (255,120,120), enemy,  2, use_camera=True)

    # UI (카메라 무시)
    draw_text(renderer, font, "모듈화 렌더 데모", (235,235,235), (W//2, 14), anchor="midtop", use_camera=False)
    draw_fps(renderer, clock, font)

    pygame.display.flip()

pygame.quit()