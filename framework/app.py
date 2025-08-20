import pygame

class GameApp:
    def __init__(self, size=(1024, 800), title="Empty Space"):
        pygame.init()

        #############################
        # 맵 사이즈 세팅하기
        self.size = size
        self.screen = pygame.display.set_mode(self.size)
        # 타이틀 세팅하기
        pygame.display.set_caption(title)
        # 시간 세팅
        self.clock = pygame.time.Clock()
        # 러닝중
        self.running = True

    def run(self):
        while self.running:
            dt = self.clock.tick(144) / 1000.0
            # --- 입력 처리 ---
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.running = False
                elif e.type == pygame.K_LEFT:
                    self.scenes.NextScene()
                elif e.type == pygame.K_RIGHT:
                    self.scenes.PrevScene()

            pygame.display.flip()
        
        pygame.quit()