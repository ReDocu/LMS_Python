import pygame

from model.SceneDB import SceneDB

class GameApp:
    def __init__(self, size=(1024, 800), title="Empty Space"):
        pygame.init()
        self.size = size
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True

        self.sceneDicts = {}

        # 모듈 선택 내역
        self.model = None
        self.camera = None
        self.renderer = None
        self.scenes = None
        # ---- 모듈 적용 ----

        self.scenes = SceneDB()
        self.scenes.PrintInfo()

        self.scenes.ChangeScene('TITLE')

    # ---- Process ----
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

            # --- 업데이트 ---
            #if self.scenes:
            #    self.scenes.curScene().update()
            # --- 렌더 ---
            if self.scenes:
                if self.scenes == None:
                    font = pygame.font.Font(None, 28)
                    msg = "Not Setting Scene"
                    surf = font.render(msg, True, (230, 230, 230))
                    self.screen.blit(surf, (20, 20))
            #    self.scenes.curScene().render()
            else:
                # 아직 View/Scene 없을 때도 빈 화면이라도 그려주기
                self.screen.fill((18, 22, 30))
                # 가벼운 안내 텍스트
                font = pygame.font.Font(None, 28)
                msg = "No Scene yet. Next: make controller/scene.py, view/, model/."
                surf = font.render(msg, True, (230, 230, 230))
                self.screen.blit(surf, (20, 20))

            pygame.display.flip()

        pygame.quit()