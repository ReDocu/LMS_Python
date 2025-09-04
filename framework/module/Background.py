import pygame
from typing import Tuple, Optional

Vec2 = Tuple[float, float]
Size = Tuple[int, int]

class Background:
    """
    Pygame Background Manager
    modes: 'cover' | 'contain' | 'stretch' | 'tile'
    - cover   : 비율 유지, 화면 꽉 채우기(잘림)
    - contain : 비율 유지, 전부 보이게(레터박스)
    - stretch : 화면 크기에 딱 맞게 왜곡 허용
    - tile    : 타일 반복, speed로 자동 스크롤 가능
    """

    def __init__(
        self,
        image_path: str,
        size: Size,
        mode: str = "cover",
        *,
        letterbox_color: Tuple[int, int, int] = (0, 0, 0),
        speed: Vec2 = (0.0, 0.0),          # tile 모드에서 자동 스크롤 속도(px/sec)
        parallax: Vec2 = (0.0, 0.0),       # 카메라 대비 이동 비율 (tile 모드 전용)
    ) -> None:
        self.mode = mode
        self.letterbox_color = letterbox_color
        self.speed = speed
        self.parallax = parallax

        # 이미지 로드
        try:
            img = pygame.image.load(image_path)
            # 알파 유무에 따라 convert/convert_alpha 선택
            self.src: pygame.Surface = img.convert_alpha() if img.get_alpha() else img.convert()
        except Exception as e:
            print(f"[Background] 이미지 로드 실패: {e}")
            self.src = pygame.Surface((32, 32))
            self.src.fill((32, 32, 32))

        self.size: Size = size
        self._scaled_cache: Optional[pygame.Surface] = None
        self._cache_for: Optional[Size] = None

        # 자동 스크롤/패럴럭스용 오프셋
        self._scroll_x: float = 0.0
        self._scroll_y: float = 0.0
        self._camera_px: Vec2 = (0.0, 0.0)  # 외부 카메라 좌표(px)

        self._rescale_if_needed()

    # ---------- 공용 API ----------
    def set_mode(self, mode: str) -> None:
        if mode not in ("cover", "contain", "stretch", "tile"):
            raise ValueError("mode must be one of: cover, contain, stretch, tile")
        self.mode = mode
        self._invalidate_cache()

    def set_speed(self, speed: Vec2) -> None:
        self.speed = speed

    def set_parallax(self, parallax: Vec2) -> None:
        self.parallax = parallax

    def on_resize(self, new_size: Size) -> None:
        """창 리사이즈 시 호출"""
        self.size = new_size
        self._invalidate_cache()

    def update(self, dt: float, camera_px: Vec2 = (0.0, 0.0)) -> None:
        """dt: 초 단위 프레임 간격, camera_px: 카메라 픽셀 좌표(패럴럭스 용)"""
        self._rescale_if_needed()
        self._camera_px = camera_px

        # tile 모드 자동 스크롤
        if self.mode == "tile":
            self._scroll_x = (self._scroll_x + self.speed[0] * dt) % self.src.get_width()
            self._scroll_y = (self._scroll_y + self.speed[1] * dt) % self.src.get_height()

    def draw(self, screen: pygame.Surface) -> None:
        """화면에 배경을 그림"""
        self._rescale_if_needed()

        if self.mode == "tile":
            self._draw_tiled(screen)
        elif self.mode == "stretch":
            screen.blit(self._scaled_cache, (0, 0))
        elif self.mode == "cover":
            # cover는 중앙 크롭 이미지를 캐시에 만들어둠
            screen.blit(self._scaled_cache, (0, 0))
        elif self.mode == "contain":
            # 레터박스 중앙 배치
            sw, sh = self._scaled_cache.get_size()
            tw, th = self.size
            x = (tw - sw) // 2
            y = (th - sh) // 2
            # 배경 색으로 레터박스 채우기
            screen.fill(self.letterbox_color)
            screen.blit(self._scaled_cache, (x, y))

    # ---------- 내부 구현 ----------
    def _invalidate_cache(self) -> None:
        self._scaled_cache = None
        self._cache_for = None

    def _rescale_if_needed(self) -> None:
        if self._cache_for == self.size and self._scaled_cache is not None:
            return

        tw, th = self.size
        sw, sh = self.src.get_width(), self.src.get_height()

        if self.mode == "stretch":
            self._scaled_cache = pygame.transform.smoothscale(self.src, (tw, th))
        elif self.mode in ("cover", "contain"):
            if sw == 0 or sh == 0:
                self._scaled_cache = pygame.Surface((tw, th))
                self._scaled_cache.fill(self.letterbox_color)
            else:
                # 비율 유지 스케일
                scale = max(tw / sw, th / sh) if self.mode == "cover" else min(tw / sw, th / sh)
                new_size = (max(1, int(sw * scale)), max(1, int(sh * scale)))
                scaled = pygame.transform.smoothscale(self.src, new_size)

                if self.mode == "cover":
                    # 중앙 크롭해서 타겟 크기와 동일하게
                    x = (scaled.get_width() - tw) // 2
                    y = (scaled.get_height() - th) // 2
                    rect = pygame.Rect(x, y, tw, th)
                    self._scaled_cache = scaled.subsurface(rect).copy()
                else:
                    # contain은 레터박스는 draw에서 fill 처리, 여기선 스케일만 캐시
                    self._scaled_cache = scaled
        elif self.mode == "tile":
            # tile은 원본을 그대로 사용 (draw에서 타일링)
            # 다만, 화면 크기가 달라도 캐시할 필요 없음
            self._scaled_cache = self.src
        else:
            self._scaled_cache = self.src

        self._cache_for = self.size

    def _draw_tiled(self, screen: pygame.Surface) -> None:
        """타일 모드 렌더링(+자동 스크롤 + 패럴럭스)"""
        tw, th = self.size
        tile = self._scaled_cache  # = self.src
        w, h = tile.get_width(), tile.get_height()

        # 카메라 패럴럭스 보정
        camx = self._camera_px[0] * self.parallax[0]
        camy = self._camera_px[1] * self.parallax[1]

        # 시작 오프셋 (자동 스크롤 + 패럴럭스)
        start_x = -int(self._scroll_x + camx) % w
        start_y = -int(self._scroll_y + camy) % h

        # 화면을 덮을 만큼 반복 블릿
        y = start_y - h
        while y < th:
            x = start_x - w
            while x < tw:
                screen.blit(tile, (x, y))
                x += w
            y += h
