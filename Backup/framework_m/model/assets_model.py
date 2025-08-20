# model/assets_model.py
# pygame 2.x / Python 3.9+
import os
from typing import Dict, Tuple, Optional
import pygame

Surface = pygame.Surface

class AssetsModel:
    """
    1단계 Model:
      1) 파일을 로드한다.
      2) 파일을 dict 자료구조에 넣는다.
      3) 실제 사용파일의 크기를 줄이거나 늘리는 유틸을 제공한다.

    지원 타입:
      - image: png/jpg/jpeg/bmp/gif/webp
      - sound: wav/ogg/mp3  (※ pygame.mixer.init() 필요)
      - font : ttf/otf      (경로 기반 로드 권장)
    """

    IMAGE_EXT = {"png", "jpg", "jpeg", "bmp", "gif", "webp"}
    SOUND_EXT = {"wav", "ogg", "mp3"}
    FONT_EXT  = {"ttf", "otf"}

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)

        # 2) dict 저장: key -> object
        self.images: Dict[str, Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.fonts:  Dict[str, pygame.font.Font] = {}

        # 크기/옵션 캐시 (재계산 방지)
        self._image_scaled_cache: Dict[Tuple[str, Tuple[int,int]], Surface] = {}
        self._font_size_cache:   Dict[Tuple[str, int], pygame.font.Font]   = {}

    # ---------- 내부 유틸 ----------
    def _abs(self, path: str) -> str:
        return path if os.path.isabs(path) else os.path.join(self.base_dir, path)

    # ---------- 1) 로드 + 2) dict 저장 ----------
    def load(self, key: str, path: str, *, kind: Optional[str] = None,
             font_size: int = 24, image_alpha: bool = True):
        """
        kind 미지정 시 파일 확장자로 자동 추론.
        - image: convert_alpha() / convert()
        - sound: pygame.mixer.Sound
        - font : pygame.font.Font (font_size 적용)
        """
        abspath = self._abs(path)
        ext = os.path.splitext(abspath)[1].lower().lstrip(".")

        if kind is None:
            if ext in self.IMAGE_EXT:
                kind = "image"
            elif ext in self.SOUND_EXT:
                kind = "sound"
            elif ext in self.FONT_EXT:
                kind = "font"
            else:
                raise ValueError(f"지원하지 않는 확장자: .{ext}")

        if kind == "image":
            surf = pygame.image.load(abspath)
            self.images[key] = surf.convert_alpha() if image_alpha else surf.convert()

        elif kind == "sound":
            # 주의: pygame.mixer.init()이 되어 있어야 함
            self.sounds[key] = pygame.mixer.Sound(abspath)

        elif kind == "font":
            self.fonts[key] = pygame.font.Font(abspath, font_size)
            # 폰트 재사이즈를 위해 경로 메타 심어둔다
            setattr(self.fonts[key], "_asset_path", abspath)

        else:
            raise ValueError(f"지원하지 않는 kind: {kind}")

    # 경로를 명시해서 폰트 로드 (권장)
    def load_font_with_path(self, key: str, font_path: Optional[str], size: int):
        """
        font_path=None 이면 시스템 기본 폰트.
        이후 font_resized_safe()로 다른 크기 요청 가능.
        """
        abspath = None if font_path is None else self._abs(font_path)
        font = pygame.font.Font(abspath, size)
        setattr(font, "_asset_path", abspath)
        self.fonts[key] = font

    # ---------- 3) 활용: 크기 관리 유틸 ----------
    # 원본 접근
    def image(self, key: str) -> Surface:
        return self.images[key]

    def sound(self, key: str) -> pygame.mixer.Sound:
        return self.sounds[key]

    def font(self, key: str) -> pygame.font.Font:
        return self.fonts[key]

    # 이미지 크기 조절
    def image_scaled(self, key: str, size: Tuple[int, int], *, smooth: bool = True) -> Surface:
        """
        (w, h) 정확 스케일. 캐시됨.
        """
        size = (int(size[0]), int(size[1]))
        ckey = (key, size)
        if ckey in self._image_scaled_cache:
            return self._image_scaled_cache[ckey]

        src = self.images[key]
        scaled = pygame.transform.smoothscale(src, size) if smooth else pygame.transform.scale(src, size)
        self._image_scaled_cache[ckey] = scaled
        return scaled

    def image_scale_ratio(self, key: str, ratio: float, *, smooth: bool = True) -> Surface:
        """
        비율 스케일 (예: 2.0 = 2배). 캐시됨.
        """
        src = self.images[key]
        w, h = src.get_width(), src.get_height()
        return self.image_scaled(key, (int(w * ratio), int(h * ratio)), smooth=smooth)

    def image_fit_contain(self, key: str, box: Tuple[int, int], *, smooth: bool = True) -> Surface:
        """
        contain: 박스 안에 이미지 전부 들어오도록 비율 유지.
        """
        src = self.images[key]
        w, h = src.get_width(), src.get_height()
        bw, bh = box
        if w == 0 or h == 0:
            return src
        r = min(bw / w, bh / h)
        return self.image_scaled(key, (max(1, int(w * r)), max(1, int(h * r))), smooth=smooth)

    def image_fit_cover(self, key: str, box: Tuple[int, int], *, smooth: bool = True) -> Surface:
        """
        cover: 박스를 가득 채우도록 비율 유지(넘치는 부분은 잘라 쓰기).
        """
        src = self.images[key]
        w, h = src.get_width(), src.get_height()
        bw, bh = box
        if w == 0 or h == 0:
            return src
        r = max(bw / w, bh / h)
        return self.image_scaled(key, (max(1, int(w * r)), max(1, int(h * r))), smooth=smooth)

    # 이미지 기타 편의
    def image_rotate(self, key: str, angle: float) -> Surface:
        return pygame.transform.rotate(self.images[key], angle)

    def image_flip(self, key: str, flip_x: bool, flip_y: bool) -> Surface:
        return pygame.transform.flip(self.images[key], flip_x, flip_y)

    # 폰트 크기 관리 (경로 기반 로드 필수)
    def font_resized_safe(self, key: str, size: int) -> pygame.font.Font:
        """
        같은 폰트 파일로 다른 size를 안전하게 생성/캐시.
        """
        ckey = (key, int(size))
        if ckey in self._font_size_cache:
            return self._font_size_cache[ckey]

        base = self.fonts[key]
        font_path = getattr(base, "_asset_path", None)  # load()/load_font_with_path()에서 저장됨
        new_font = pygame.font.Font(font_path, size)
        setattr(new_font, "_asset_path", font_path)
        self._font_size_cache[ckey] = new_font
        return new_font
