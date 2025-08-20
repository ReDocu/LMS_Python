# ui/debug.py
import pygame
from gfx.text import draw_text

def draw_fps(renderer, clock, font, color=(240,240,240)):
    draw_text(renderer, font, f"FPS: {int(clock.get_fps())}", color, (10, 10), anchor="topleft", use_camera=False)