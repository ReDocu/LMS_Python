# scenes/procgen_scene.py
import pygame, random, time
from core.scene_manager import Scene

# ===== 유틸 =====
def clamp(v, lo, hi): return max(lo, min(hi, v))

# ====== ProcGen Scene ======
class ProcGenPlaygroundScene(Scene):
    NAME = "ProcGenPlaygroundScene"

    def enter(self, **kwargs):
        self.app = kwargs.get("app", self.app)  # 혹시 호출부에서 넘겨주면 반영
        self.screen = self.app["screen"]
        self.w, self.h = self.screen.get_size()
        self.font = pygame.font.SysFont("consolas", 18)

        # 전역 설정
        self.tile = 4
        self.grid_w = self.w // self.tile
        self.grid_h = self.h // self.tile

        # 상태
        self.mode = 1  # 1: RandomWalk, 2: Cellular, 3: BSP
        self.seed = int(time.time())
        random.seed(self.seed)

        # 모드 파라미터
        self.params = {
            1: {  # RandomWalk
                "steps": (self.grid_w * self.grid_h // 2, 1, self.grid_w * self.grid_h),  # (val, min, max)
                "batch": (600, 1, 5000),
            },
            2: {  # CellularCave
                "wall_prob": (44, 0, 95),  # 퍼센트(%)
                "smooth_iters": (5, 0, 10),
                "threshold": (5, 3, 7),
            },
            3: {  # BSPDungeon
                "min_size": (12, 6, 32),
                "splits": (8, 1, 20),
            },
        }
        self.param_keys = {m: list(self.params[m].keys()) for m in self.params}
        self.param_idx = 0

        self._build_current()

    # ---------- 공통 빌드/리셋 ----------
    def _reseed(self):
        self.seed = random.randrange(10**9)
        random.seed(self.seed)

    def _build_current(self):
        if self.mode == 1:
            self._build_random_walk()
        elif self.mode == 2:
            self._build_cellular()
        elif self.mode == 3:
            self._build_bsp()

    def _grid_clear(self, fill=1):
        self.grid = [[fill] * self.grid_w for _ in range(self.grid_h)]

    # ---------- 모드 1: RandomWalk ----------
    def _build_random_walk(self):
        self._grid_clear(fill=0)
        self.rw_x = self.grid_w // 2
        self.rw_y = self.grid_h // 2
        self.rw_steps = self.params[1]["steps"][0]

    def _step_random_walk(self):
        batch = self.params[1]["batch"][0]
        while batch > 0 and self.rw_steps > 0:
            self.grid[self.rw_y][self.rw_x] = 1
            dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            self.rw_x = clamp(self.rw_x + dx, 0, self.grid_w - 1)
            self.rw_y = clamp(self.rw_y + dy, 0, self.grid_h - 1)
            self.rw_steps -= 1
            batch -= 1

    # ---------- 모드 2: Cellular Cave ----------
    def _build_cellular(self):
        p = self.params[2]
        wall_prob = p["wall_prob"][0] / 100.0
        self._grid_clear(fill=0)
        # 테두리는 벽
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                edge = (x == 0 or y == 0 or x == self.grid_w-1 or y == self.grid_h-1)
                self.grid[y][x] = 1 if edge or (random.random() < wall_prob) else 0
        for _ in range(p["smooth_iters"][0]):
            self.grid = self._cell_step(self.grid, p["threshold"][0])

    def _cell_step(self, g, T):
        H, W = len(g), len(g[0])
        newg = [[0]*W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                walls = 0
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if dx == 0 and dy == 0: continue
                        nx, ny = x+dx, y+dy
                        if nx<0 or ny<0 or nx>=W or ny>=H: walls += 1
                        else: walls += g[ny][nx]
                if g[y][x] == 1:
                    newg[y][x] = 1 if walls >= 4 else 0
                else:
                    newg[y][x] = 1 if walls >= T else 0
        return newg

    # ---------- 모드 3: BSP Dungeon ----------
    class _Node:
        def __init__(self, x,y,w,h,depth=0):
            self.x,self.y,self.w,self.h = x,y,w,h
            self.left=None; self.right=None
            self.room=None; self.depth=depth

    def _build_bsp(self):
        self._grid_clear(fill=1)
        min_size = self.params[3]["min_size"][0]
        splits   = self.params[3]["splits"][0]
        root = self._Node(1,1,self.grid_w-2,self.grid_h-2)
        leaves = [root]
        for _ in range(splits):
            leaf = random.choice(leaves)
            if self._split(leaf, min_size):
                leaves.remove(leaf)
                leaves.extend([leaf.left, leaf.right])

        self._make_rooms(root)
        self._carve_rooms(root)

    def _split(self, node, min_size):
        # 분할 방향 힌트
        horiz = random.random() < 0.5
        if node.w > node.h*1.25: horiz = False
        if node.h > node.w*1.25: horiz = True

        if node.w < 2*min_size and node.h < 2*min_size:
            return False

        if horiz:
            if node.h < 2*min_size: return False
            cut = random.randint(min_size, node.h - min_size)
            node.left  = self._Node(node.x, node.y, node.w, cut, node.depth+1)
            node.right = self._Node(node.x, node.y+cut, node.w, node.h-cut, node.depth+1)
        else:
            if node.w < 2*min_size: return False
            cut = random.randint(min_size, node.w - min_size)
            node.left  = self._Node(node.x, node.y, cut, node.h, node.depth+1)
            node.right = self._Node(node.x+cut, node.y, node.w-cut, node.h, node.depth+1)
        return True

    def _make_rooms(self, node):
        if node.left or node.right:
            if node.left:  self._make_rooms(node.left)
            if node.right: self._make_rooms(node.right)
        else:
            if node.w >= 4 and node.h >= 4:
                rw = random.randint(node.w//2, max(node.w-2, node.w//2))
                rh = random.randint(node.h//2, max(node.h-2, node.h//2))
                rx = random.randint(node.x+1, node.x+node.w-rw-1)
                ry = random.randint(node.y+1, node.y+node.h-rh-1)
                node.room = (rx,ry,rw,rh)

    def _find_room(self, node):
        if node is None: return None
        if node.room: return node.room
        return self._find_room(node.left) or self._find_room(node.right)

    def _connect_rooms(self, a, b):
        ax, ay = (a[0]+a[2]//2, a[1]+a[3]//2)
        bx, by = (b[0]+b[2]//2, b[1]+b[3]//2)
        # L-커리도
        for x in range(min(ax,bx), max(ax,bx)+1):
            self.grid[ay][x] = 0
        for y in range(min(ay,by), max(ay,by)+1):
            self.grid[y][bx] = 0

    def _carve_rooms(self, node):
        if node.left and node.right:
            self._carve_rooms(node.left)
            self._carve_rooms(node.right)
            a = self._find_room(node.left)
            b = self._find_room(node.right)
            if a and b: self._connect_rooms(a,b)
        elif node.room:
            rx,ry,rw,rh = node.room
            for y in range(ry, ry+rh):
                for x in range(rx, rx+rw):
                    self.grid[y][x] = 0

    # ---------- 이벤트 ----------
    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.app["running"] = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.app["scenes"].switch(self.app["MainScene"], with_fade=True)
                elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.mode = {pygame.K_1:1, pygame.K_2:2, pygame.K_3:3}[ev.key]
                    self._build_current()
                elif ev.key == pygame.K_r:
                    # 파라미터 유지, 동일 시드 유지
                    random.seed(self.seed)
                    self._build_current()
                elif ev.key == pygame.K_s:
                    # 새 시드
                    self._reseed()
                    self._build_current()
                elif ev.key == pygame.K_TAB:
                    self.param_idx = (self.param_idx + 1) % len(self.param_keys[self.mode])
                elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    self._tweak_param(ev.key)

    def _tweak_param(self, key):
        m = self.mode
        k = self.param_keys[m][self.param_idx]
        val, lo, hi = self.params[m][k]
        delta = 1
        if key in (pygame.K_LEFT, pygame.K_DOWN):
            val = clamp(val - delta, lo, hi)
        else:
            val = clamp(val + delta, lo, hi)
        self.params[m][k] = (val, lo, hi)
        # 일부 파라미터는 즉시 재빌드
        if m in (2,3):  # Cellular, BSP는 파라미터가 구조에 영향 → 즉시 반영
            self._build_current()

    # ---------- 업데이트 ----------
    def update(self, dt):
        if self.mode == 1:  # RandomWalk는 프레임마다 진행
            self._step_random_walk()

    # ---------- 드로잉 ----------
    def draw(self, screen):
        # 배경
        screen.fill((20, 24, 28))

        # 그리드 렌더
        if self.mode == 1:
            # random walk: 1이면 밝게
            for y in range(self.grid_h):
                row = self.grid[y]
                for x in range(self.grid_w):
                    if row[x]:
                        pygame.draw.rect(screen, (220, 220, 255), (x*self.tile, y*self.tile, self.tile, self.tile))
        else:
            # 1=벽, 0=바닥
            for y in range(self.grid_h):
                row = self.grid[y]
                for x in range(self.grid_w):
                    color = (35, 32, 40) if row[x] else (240, 240, 230)
                    pygame.draw.rect(screen, color, (x*self.tile, y*self.tile, self.tile, self.tile))

        # UI 오버레이
        self._draw_overlay(screen)

    def _draw_overlay(self, screen):
        pad = 8
        lines = [
            f"[ProcGen Playground] mode={self.mode_name()}  seed={self.seed}",
            "1:RandomWalk  2:Cellular  3:BSP   ESC:Back",
            "R:Reset  S:Reseed  TAB:Next-Param  ←/→/↑/↓:Adjust",
        ]
        # 파라미터 표시
        m = self.mode
        pkeys = self.param_keys[m]
        show = []
        for i,k in enumerate(pkeys):
            v = self.params[m][k][0]
            mark = "▶" if i == self.param_idx else "  "
            show.append(f"{mark} {k}: {v}")
        lines += show

        # 반투명 배경
        surf = pygame.Surface((420, 20*len(lines)+pad*2), pygame.SRCALPHA)
        surf.fill((0,0,0,140))
        screen.blit(surf, (pad, pad))

        # 텍스트
        y = pad + 4
        for line in lines:
            img = self.font.render(line, True, (230, 230, 240))
            screen.blit(img, (pad+8, y))
            y += 20

    def mode_name(self):
        return {1:"RandomWalk", 2:"CellularCave", 3:"BSPDungeon"}[self.mode]
