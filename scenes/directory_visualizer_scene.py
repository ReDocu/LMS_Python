import pygame
from core.scene_manager import Scene

class DirectoryVisualizerScene(Scene):
    def enter(self, **kwargs):
        self.screen = self.app["screen"]
        self.font = pygame.font.SysFont("arial", 32)
        self.msg = "Directory Visualizer Scene"
        self.running = True

    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app["running"] = False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    # ESC를 누르면 MainScene으로 돌아가기
                    self.app["scenes"].switch(self.app["MainScene"], with_fade=True)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((50, 80, 120))  # 배경색
        txt = self.font.render(self.msg, True, (255, 255, 255))
        screen.blit(txt, (screen.get_width()//2 - txt.get_width()//2,
                          screen.get_height()//2 - txt.get_height()//2))
