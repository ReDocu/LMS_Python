import pygame
from core.scene_manager import Scene
from ui.textbox import TextBox
from ui.button import Button
from core.theme import get_colors

class LoginScene(Scene):
    def enter(self, **kwargs):
        self.screen = self.app['screen']
        self.state = self.app['state']
        self.font32 = pygame.font.SysFont("arial", 32)
        self.font24 = pygame.font.SysFont("arial", 24)
        colors = get_colors(self.state.theme)
        self.BG = colors["bg"]
        self.TEXT = colors["text"]
        bc = colors["button_colors"]

        cx, cy = self.screen.get_width()//2, self.screen.get_height()//2
        self.txt_user = TextBox((cx-170, cy-80), (340,44), font=self.font24, placeholder="Username")
        self.txt_pass = TextBox((cx-170, cy-20), (340,44), font=self.font24, placeholder="Password", password=True)

        def do_login():
            name = self.txt_user.get_text().strip() or "Guest"
            self.state.username = name
            self.state.save()
            self.app['scenes'].switch(self.app['MainScene'], with_fade=True, username=name)

        self.btn_login = Button("Login", (cx-75, cy+40), (150,48), font=self.font24, on_click=do_login)
        self.btn_login.set_colors(
            default=bc["default"], hover=bc["hover"], active=bc["active"], disabled=bc["disabled"]
        )

    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app['running'] = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                if self.btn_login.on_click:
                    self.btn_login.on_click()
        self.txt_user.update(events); self.txt_pass.update(events); self.btn_login.update(events)

    def draw(self, screen):
        screen.fill(self.BG)
        title = self.font32.render("Sign In", True, self.TEXT)
        screen.blit(title, (screen.get_width()//2 - title.get_width()//2, 120))

        label_u = self.font24.render("Username", True, self.TEXT)
        label_p = self.font24.render("Password", True, self.TEXT)
        screen.blit(label_u, (self.txt_user.rect.x, self.txt_user.rect.y - 26))
        screen.blit(label_p, (self.txt_pass.rect.x, self.txt_pass.rect.y - 26))

        self.txt_user.draw(screen); self.txt_pass.draw(screen); self.btn_login.draw(screen)
