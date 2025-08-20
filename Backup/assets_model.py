# assets_model.py
# pygame 2.x / Python 3.9+
import os
import pygame
from typing import Dict, Tuple, Any, Optional

# 타입 힌트
Surface = pygame.Surface

class AssetsModel:
    """
    1단계 정의:
      1) 파일을 로드한다.
      2) 파일을 dict 자료구조에 넣는다.
      3) 실제 사용파일의 크기를 줄이거나 늘리거나, 활용 기능 제공.

    지원 타입:
      - image: png/jpg/jpeg/bmp/gif/webp
      - sound: wav/ogg/mp3 (옵션)
      - font : ttf/otf (size는 로드 시 기본값, 사용 시 재지정 가능)
    """

    IMAGE_EXT = {"png", "jpg", "jpeg", "bmp", "gif", "webp"}
    SOUND_EXT = {"wav", "ogg", "mp3"}
    FONT_EXT  = {"ttf", "otf"}

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        # 2) dict에 저장: key -> object
        self.images: Dict[str, Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.fonts:  Dict[str, pygame.font.Font] = {}

        # 크기/옵션별 캐시(불필요한 재계산 방지)
        self._image_scaled_cache: Dict[Tuple[str, Tuple[int,int]], Surface] = {}
        self._font_size_cache:   Dict[Tuple[str, int], pygame.font.Font]   = {}

    # -------------------------
    # 1) 파일 로드 + 2) dict 저장
    # -------------------------
    def load(self, key: str, path: str, *, kind: Optional[str] = None, font_size: int = 24, image_alpha: bool = True):
        """
        kind 미지정 시 확장자로 추론.
        - image: convert_alpha() or convert()
        - sound: pygame.mixer.Sound
        - font : pygame.font.Font (font_size 적용)
        """
        abspath = path if os.path.isabs(path) else os.path.join(self.base_dir, path)
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
            surf = surf.convert_alpha() if image_alpha else surf.convert()
            self.images[key] = surf
        elif kind == "sound":
            self.sounds[key] = pygame.mixer.Sound(abspath)
        elif kind == "font":
            self.fonts[key] = pygame.font.Font(abspath, font_size)
        else:
            raise ValueError(f"지원하지 않는 kind: {kind}")

    # -------------------------
    # 3) 활용 기능 (크기 조절/편의)
    # -------------------------

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
        (w, h) 로 정확히 스케일. 캐시됨.
        """
        cache_key = (key, (int(size[0]), int(size[1])))
        if cache_key in self._image_scaled_cache:
            return self._image_scaled_cache[cache_key]

        src = self.images[key]
        if smooth:
            scaled = pygame.transform.smoothscale(src, size)
        else:
            scaled = pygame.transform.scale(src, size)

        self._image_scaled_cache[cache_key] = scaled
        return scaled

    def image_scale_ratio(self, key: str, ratio: float, *, smooth: bool = True) -> Surface:
        """
        비율 스케일 (예: 2.0 = 2배). 캐시됨.
        """
        src = self.images[key]
        w, h = src.get_width(), src.get_height()
        nw, nh = int(w * ratio), int(h * ratio)
        return self.image_scaled(key, (nw, nh), smooth=smooth)

    def image_fit_contain(self, key: str, box: Tuple[int,int], *, smooth: bool = True) -> Surface:
        """
        'contain' 스케일: 박스 안에 전부 들어오도록 비율 유지.
        """
        src = self.images[key]
        w, h = src.get_width(), src.get_height()
        bw, bh = box
        if w == 0 or h == 0: return src
        r = min(bw / w, bh / h)
        nw, nh = max(1, int(w * r)), max(1, int(h * r))
        return self.image_scaled(key, (nw, nh), smooth=smooth)

    def image_fit_cover(self, key: str, box: Tuple[int,int], *, smooth: bool = True) -> Surface:
        """
        'cover' 스케일: 박스를 가득 채우도록 비율 유지(넘치는 부분은 잘라쓰기 권장).
        """
        src = self.images[key]
        w, h = src.get_width(), src.get_height()
        bw, bh = box
        if w == 0 or h == 0: return src
        r = max(bw / w, bh / h)
        nw, nh = max(1, int(w * r)), max(1, int(h * r))
        return self.image_scaled(key, (nw, nh), smooth=smooth)

    # 이미지 편의(옵션)
    def image_rotate(self, key: str, angle: float) -> Surface:
        return pygame.transform.rotate(self.images[key], angle)

    def image_flip(self, key: str, flip_x: bool, flip_y: bool) -> Surface:
        return pygame.transform.flip(self.images[key], flip_x, flip_y)

    # 폰트 크기 관리
    def font_resized(self, key: str, size: int) -> pygame.font.Font:
        """
        같은 폰트 파일의 다른 size를 캐시해서 반환.
        """
        ckey = (key, int(size))
        if ckey in self._font_size_cache:
            return self._font_size_cache[ckey]

        # 원본 폰트에서 파일 경로를 알 수 없으므로, pygame은 직접 경로를 저장하진 않음.
        # 현실적 대안: 원본 폰트를 surfaces로 렌더링하는 게 아니라,
        # 로드 시점의 파일 경로를 meta로 기록하는 방식이 필요.
        # 여기선 간단히: 원본 font.get_name()은 경로가 아니므로, 동일 family의 새 폰트 보장 X.
        # => 실무에선 load() 호출할 때 font를 '경로 기반'으로 로드하는 것을 권장.
        # 편의상: 원본이 시스템 기본(None)인지 확인 불가하니, 동일 객체를 새 size로 생성 불가.
        # 해결책: 로드 시 font path도 따로 저장하자 → 아래 확장 API 사용.

        raise RuntimeError(
            "font_resized를 쓰려면 경로 기반 로딩이 필요합니다. "
            "아래의 load_font_with_path()를 사용하세요."
        )

    # 폰트 경로/사이즈 관리 확장: 실제 프로젝트에서 이걸 쓰자!
    def load_font_with_path(self, key: str, font_path: Optional[str], size: int):
        """
        font_path가 None이면 시스템 기본 폰트.
        이후 font_resized_safe()로 다른 사이즈 요청 가능.
        """
        self.fonts[key] = pygame.font.Font(font_path, size)
        # 경로 메타 저장
        setattr(self.fonts[key], "_asset_path", font_path)

    def font_resized_safe(self, key: str, size: int) -> pygame.font.Font:
        """
        load_font_with_path()로 로드된 폰트만 안전하게 다른 사이즈 생성/캐싱.
        """
        ckey = (key, int(size))
        if ckey in self._font_size_cache:
            return self._font_size_cache[ckey]

        base = self.fonts[key]
        font_path = getattr(base, "_asset_path", None)  # 우리가 저장한 메타
        new_font = pygame.font.Font(font_path, size)
        self._font_size_cache[ckey] = new_font
        return new_font
