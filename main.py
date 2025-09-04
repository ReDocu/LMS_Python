import sys, pygame
from core.scene_manager import SceneManager
from core.app_state import AppState
from scenes.login_scene import LoginScene
from scenes.main_scene import MainScene
from scenes.directory_visualizer_scene import DirectoryVisualizerScene
from scenes.ytdownload_scene import YTDownloadScene

# Logical design resolution (do not change)
LOGICAL_W, LOGICAL_H = 1280, 720

def draw_overlay(surface, alpha=80):
    """화면 전체를 살짝 어둡게(가독성↑). alpha=0~255"""
    w, h = surface.get_size()
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    mask.fill((0, 0, 0, alpha))
    surface.blit(mask, (0, 0))

def draw_vignette(surface, strength=120):
    """모서리를 어둡게: 간단 방사형 비네트"""
    w, h = surface.get_size()
    vign = pygame.Surface((w, h), pygame.SRCALPHA)
    # 네 귀퉁이에 점점 어두워지는 원을 겹쳐서 비네트 흉내
    for r, a in ((int(min(w,h)*0.75), int(strength*0.20)),
                 (int(min(w,h)*0.55), int(strength*0.35)),
                 (int(min(w,h)*0.40), int(strength*0.50))):
        pygame.draw.ellipse(vign, (0,0,0,a), (-r//2, -r//2, w+r, h+r))
    surface.blit(vign, (0,0))


def compute_scale_to_fit(win_w, win_h):
    """Keep aspect ratio, return scale and letterbox offsets."""
    sx = win_w / LOGICAL_W
    sy = win_h / LOGICAL_H
    s = min(sx, sy)
    draw_w = int(LOGICAL_W * s)
    draw_h = int(LOGICAL_H * s)
    off_x = (win_w - draw_w) // 2
    off_y = (win_h - draw_h) // 2
    return s, off_x, off_y, draw_w, draw_h

def make_display(state: AppState):
    """Create window according to resizable + ui_scale."""
    base_w = int(LOGICAL_W * state.ui_scale)
    base_h = int(LOGICAL_H * state.ui_scale)
    flags = 0
    if state.resizable:
        flags |= pygame.RESIZABLE
    screen = pygame.display.set_mode((base_w, base_h), flags)
    return screen

def main():
    pygame.init()
    pygame.display.set_caption("DevFox Toolkit (Game Development Tool)")
    clock = pygame.time.Clock()

    # global state
    scenes = SceneManager()
    state = AppState().load()

    # window per settings
    screen = make_display(state)

    # logical render target (always 1280x720)
    logical_surface = pygame.Surface((LOGICAL_W, LOGICAL_H)).convert_alpha()

    # app context, scenes
    app = {'screen': logical_surface, 'scenes': scenes, 'state': state, 'running': True}

    # 씬 등록
    app["MainScene"] = MainScene(app)
    app["LoginScene"] = LoginScene(app)
    app["DirectoryVisualizerScene"] = DirectoryVisualizerScene(app)  # ← 추가!
    app["YTDownloadScene"] = YTDownloadScene(app)


    # 초기화
    app["scenes"].add(app["MainScene"])
    app["scenes"].add(app["LoginScene"])
    app["scenes"].add(app["DirectoryVisualizerScene"])
    app["scenes"].add(app["YTDownloadScene"])
    # 첫 화면
    app["scenes"].switch(app["YTDownloadScene"], with_fade=False)

    # 필요시 페이드 시간 조절
    app["scenes"].set_fade(0.5)

    # track window size when resizable
    win_w, win_h = screen.get_size()

    while app['running']:
        dt = clock.tick(60) / 1000.0
        events = pygame.event.get()

        # Handle resize if allowed
        for ev in events:
            if ev.type == pygame.QUIT:
                app['running'] = False
            elif ev.type == pygame.VIDEORESIZE and state.resizable:
                win_w, win_h = ev.size
                # recreate display surface on resize (keeps RESIZABLE flag)
                screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)

        # forward input only when not in fade-out stage
        scenes.handle_events(events)
        scenes.update(dt)

        # draw scenes to logical surface
        logical_surface.fill((0,0,0,0))
        scenes.draw(logical_surface)

        # scale + letterbox to window
        win_w, win_h = screen.get_size()
        scale, ox, oy, dw, dh = compute_scale_to_fit(win_w, win_h)
        # letterbox background (optional: theme background)
        screen.fill((0, 0, 0))
        if scale == 1.0 and (win_w, win_h) == (LOGICAL_W, LOGICAL_H):
            # perfect 1:1
            screen.blit(logical_surface, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(logical_surface, (dw, dh))
            screen.blit(scaled, (ox, oy))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
