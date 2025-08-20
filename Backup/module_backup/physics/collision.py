# physics/collision.py
from typing import Tuple
import math

Rect = Tuple[float, float, float, float] # x,y,w,h

def rect_rect(a: Rect, b: Rect) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax < bx + bw) and (ax + aw > bx) and (ay < by + bh) and (ay + ah > by)

def circle_circle(a_center, a_r, b_center, b_r) -> bool:
    dx = a_center[0] - b_center[0]
    dy = a_center[1] - b_center[1]
    return (dx*dx + dy*dy) <= (a_r + b_r)*(a_r + b_r)

def rect_circle(rect: Rect, c, r) -> bool:
    # 원의 중심에서 사각형으로 최근접점 구해서 거리 비교
    x, y, w, h = rect
    cx, cy = c
    nx = max(x, min(cx, x + w))
    ny = max(y, min(cy, y + h))
    dx, dy = cx - nx, cy - ny
    return dx*dx + dy*dy <= r*r

def overlap_amount(a: Rect, b: Rect):
    # 충돌 시 최소분리벡터(맨해튼 축) 리턴 (없으면 (0,0))
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if not rect_rect(a, b):
        return (0.0, 0.0)
    dx1 = (bx + bw) - ax   # b가 a의 왼쪽을 얼마나 침범?
    dx2 = (ax + aw) - bx   # b가 a의 오른쪽을 얼마나 침범?
    dy1 = (by + bh) - ay
    dy2 = (ay + ah) - by
    # 작은 쪽으로 밀어내기
    mx = dx1 if abs(dx1) < abs(dx2) else -dx2
    my = dy1 if abs(dy1) < abs(dy2) else -dy2
    if abs(mx) < abs(my):
        return (mx, 0.0)
    else:
        return (0.0, my)