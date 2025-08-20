# modules/input.py
import pygame

class Command:
    def execute(self, scene, dt: float): ...

class Move(Command):
    def __init__(self, dx=0.0, dy=0.0, speed=260):
        self.dx, self.dy, self.speed = dx, dy, speed
    def execute(self, scene, dt):
        scene.pos.x += self.dx * self.speed * dt
        scene.pos.y += self.dy * self.speed * dt

class Zoom(Command):
    def __init__(self, dz=0.0):
        self.dz = dz
    def execute(self, scene, dt):
        scene.camera.zoom = max(0.25, min(3.0, scene.camera.zoom + self.dz))

class ToggleVignette(Command):
    def execute(self, scene, dt):
        scene.show_vignette = not getattr(scene, "show_vignette", True)

class InputMap:
    def __init__(self):
        self.down = {}   # KEYDOWN 시 1회성
        self.hold = {}   # 키가 눌려있는 동안 반복

    def bind_hold(self, key, cmd: Command):
        self.hold[key] = cmd; return self
    def bind_down(self, key, cmd: Command):
        self.down[key] = cmd; return self

    def handle_event(self, e, scene):
        if e.type == pygame.KEYDOWN and e.key in self.down:
            self.down[e.key].execute(scene, 0.0)

    def tick(self, scene, dt):
        keys = pygame.key.get_pressed()
        for k, cmd in self.hold.items():
            if keys[k]:
                cmd.execute(scene, dt)
