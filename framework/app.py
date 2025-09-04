import pygame
from module.Background import Background

class GameApp:
    def __init__(self, size=(1280, 768), title="Empty Space"):
        pygame.init()
        self.size = size
        self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True

        # 배경 생성
        # 1) 커버형
        self.bg = Background("images/background1.png", self.size, mode="cover")
        # 2) 타일 + 자동 스크롤 원하면:
        # self.bg = Background("images/bg01.jpg", self.size, mode="tile",
        #                      speed=(20, 0), parallax=(0.2, 0.0))

        # (선택) 씬 매니저가 있다면
        self.scenes = None

        # 카메라 예시(패럴럭스용)
        self.camera_px = [0.0, 0.0]

    def run(self):
        while self.running:
            dt = self.clock.tick(144) / 1000.0

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.running = False
                    elif e.key == pygame.K_LEFT and self.scenes:
                        self.scenes.NextScene()
                    elif e.key == pygame.K_RIGHT and self.scenes:
                        self.scenes.PrevScene()
                elif e.type == pygame.VIDEORESIZE:
                    self.size = (max(1, e.w), max(1, e.h))
                    self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)
                    self.bg.on_resize(self.size)

            # (예시) 카메라 움직임 모킹
            # self.camera_px[0] += 30 * dt

            # 업데이트 & 그리기
            self.bg.update(dt, camera_px=tuple(self.camera_px))
            self.bg.draw(self.screen)

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    GameApp().run()