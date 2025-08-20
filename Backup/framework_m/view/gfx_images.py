# view/gfx_images.py
import pygame
from view.renderer import Renderer

def draw_image(r: Renderer, image: pygame.Surface, pos, *,
               use_camera=True, anchor="topleft",
               angle=0.0, scale=1.0, flip_x=False, flip_y=False, alpha=None):
    surf = image
    if flip_x or flip_y:
        surf = pygame.transform.flip(surf, flip_x, flip_y)
    if scale != 1.0:
        w,h = surf.get_size()
        surf = pygame.transform.smoothscale(surf, (int(w*scale), int(h*scale)))
    if angle:
        surf = pygame.transform.rotate(surf, angle)
    if alpha is not None:
        surf = surf.copy(); surf.set_alpha(alpha)
    r.blit(surf, pos, use_camera=use_camera, anchor=anchor)
