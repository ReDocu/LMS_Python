import pygame

class LabelBox:
    def __init__(self, text, pos, size, *, font, bg=None, border=None, ink=(40,40,40), radius=8, padding=10):
        self.text = text
        self.rect = pygame.Rect(pos, size)
        self.font = font
        self.bg = bg          # None = 투명 (fill 안 함)
        self.border = border  # None = 테두리 없음
        self.ink = ink
        self.radius = radius
        self.padding = padding

    def set_theme(self, *, bg=None, border=None, ink=None):
        if bg is not None: self.bg = bg
        if border is not None: self.border = border
        if ink is not None: self.ink = ink

    def draw(self, surface):
        # bg가 있으면 카드처럼 칠하고, 없으면 투명
        if self.bg is not None:
            pygame.draw.rect(surface, self.bg, self.rect, border_radius=self.radius)
        if self.border is not None:
            pygame.draw.rect(surface, self.border, self.rect, width=2, border_radius=self.radius)

        label = self.font.render(self.text, True, self.ink)
        surface.blit(label, (self.rect.x + self.padding, self.rect.y + (self.rect.height - label.get_height()) // 2))
