# controller/app.py
import pygame

class GameApp:
    def __init__(self, size=(1024, 800), title="MVC Pygame — Stage 1"):
        pygame.init()
        self.size = size
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True

        # --- 선택적 의존성: 없어도 실행되게 try-import ---
        self.model = None
        self.camera = None
        self.renderer = None
        self.scenes = None

        # Model
        try:
            from model.assets_model import AssetsModel  # 다음 단계에서 만들 예정
            self.model = AssetsModel(base_dir=".")
        except Exception:
            pass  # 아직 파일이 없으면 None 유지

        # Camera
        try:
            from modules.camera import Camera           # 다음 단계에서 만들 예정
            self.camera = Camera(pos=(0, 0), zoom=1.0)
        except Exception:
            pass

        # View(Renderer)
        try:
            from view.renderer import Renderer          # 다음 단계에서 만들 예정
            self.renderer = Renderer(self.screen, self.camera)
        except Exception:
            pass

        # Scene Manager + DemoScene
        try:
            from controller.scene import SceneManager, DemoScene  # 다음 단계에서 만들 예정
            self.scenes = SceneManager()
            if self.model and self.renderer and self.camera:
                # 준비된 경우에만 데모 씬 푸시
                self.scenes.push(DemoScene(self.model, self.renderer, self.camera))
        except Exception:
            pass

    def run(self):
        while self.running:
            dt = self.clock.tick(144) / 1000.0

            # --- 입력 처리 ---
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.scenes:
                    # 씬이 있으면 이벤트 위임
                    self.scenes.handle_event(e)

            # --- 업데이트 ---
            if self.scenes:
                self.scenes.update(dt)

            # --- 렌더 ---
            if self.scenes:
                self.scenes.render()
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
