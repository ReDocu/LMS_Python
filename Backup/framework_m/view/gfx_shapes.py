# view/gfx_shapes.py
from view.renderer import Renderer

def rect(r: Renderer, color, xywh, width=0, *, use_camera=True):
    r.draw_rect(color, xywh, width, use_camera=use_camera)

def line(r: Renderer, color, a, b, width=1, *, use_camera=True):
    r.draw_line(color, a, b, width, use_camera=use_camera)

def circle(r: Renderer, color, center, radius, width=0, *, use_camera=True):
    r.draw_circle(color, center, radius, width, use_camera=use_camera)
