import pygame
import sys

# --- 색상 ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE  = (70, 130, 180)
LIGHT_BLUE = (100, 160, 210)
DARK_BLUE = (40, 90, 140)

# --- 버튼 클래스 ---
class Button:
    def __init__(self, text, pos, size=(150, 50)):
        self.text = text
        self.pos = pos
        self.size = size
        self.font = pygame.font.SysFont("arial", 24)
        self.rect = pygame.Rect(pos, size)

        # 상태 색상
        self.default_color = BLUE
        self.hover_color = LIGHT_BLUE
        self.active_color = DARK_BLUE
        self.color = self.default_color  

        # 상태 플래그
        self.is_hovered = False
        self.is_pressed = False

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)  # 둥근 모서리
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def update(self, event_list):
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)

        # Hover 상태 반영
        if self.is_hovered:
            self.color = self.hover_color
        else:
            self.color = self.default_color

        # 이벤트 체크
        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.is_hovered:
                    self.is_pressed = True
                    self.color = self.active_color
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.is_pressed and self.is_hovered:
                    self.is_pressed = False
                    return True  # 클릭 완료 이벤트
                self.is_pressed = False
        return False

# --- 메인 ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption("Pygame Button with Hover & Active Effect")
    clock = pygame.time.Clock()

    button = Button("Click Me!", (225, 175))

    while True:
        screen.fill(WHITE)
        event_list = pygame.event.get()

        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 버튼 업데이트 & 이벤트 처리
        if button.update(event_list):
            print("버튼 클릭됨! 이벤트 실행!")

        # 버튼 그리기
        button.draw(screen)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
