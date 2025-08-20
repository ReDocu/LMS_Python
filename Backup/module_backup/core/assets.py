# core/assets.py
import pygame
from functools import lru_cache

@lru_cache(maxsize=256)
def load_image(path, alpha=True):
    img = pygame.image.load(path)
    return img.convert_alpha() if alpha else img.convert()

@lru_cache(maxsize=64)
def load_font(path, size):
    return pygame.font.Font(path, size)