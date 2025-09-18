# core/asset_registry.py
from __future__ import annotations

import pygame
from pathlib import Path
from typing import Dict, Iterable, Tuple, Optional, List, Literal

KeyMode = Literal["stem", "name", "path"]  # stem: 확장자 없는 파일명, name: 파일명+확장자, path: 하위경로 포함

class AssetRegistry:
    """
    Pygame 전용 에셋 레지스트리.
    - 시작 시 assets/images, assets/audio를 스캔하여 전부 메모리 로드
    - 이미지: pygame.Surface (convert/convert_alpha 적용)
    - 오디오: pygame.mixer.Sound
    - 딕셔너리 조회: images[key], audio[key]
      * key 규칙은 key_mode 옵션으로 제어(stem|name|path)
      * 파일명 중복 시 자동으로 '상대경로 키'를 사용하여 충돌 회피
    - 단건 리로드/언로드 지원
    """

    SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    SUPPORTED_AUDIO_EXTS = {".wav", ".ogg", ".mp3"}

    def __init__(
        self,
        base_dir: str | Path = "assets",
        image_dir: str = "images",
        audio_dir: str = "audio",
        recursive: bool = True,
        key_mode: KeyMode = "stem",
        convert_images: bool = True,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.image_root = self.base_dir / image_dir
        self.audio_root = self.base_dir / audio_dir
        self.recursive = recursive
        self.key_mode: KeyMode = key_mode
        self.convert_images = convert_images

        # Public dicts
        self.images: Dict[str, pygame.Surface] = {}
        self.audio: Dict[str, pygame.mixer.Sound] = {}

        # 내부: 경로 <-> 키 매핑 (역추적/리로드용)
        self._image_path_by_key: Dict[str, Path] = {}
        self._audio_path_by_key: Dict[str, Path] = {}

        # 충돌 감지용
        self._taken_keys: set[str] = set()

    # ---------------------------
    # Public API
    # ---------------------------

    def preload(self) -> None:
        """images, audio 전부 로드."""
        # mixer가 안 켜져 있으면 안전하게 초기화
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()  # 기본 파라미터
            except pygame.error:
                # 일부 환경(오디오 디바이스 없음)에서 실패할 수 있음 → 오디오만 스킵
                pass

        self._load_dir(self.image_root, "image", self.SUPPORTED_IMAGE_EXTS)
        self._load_dir(self.audio_root, "audio", self.SUPPORTED_AUDIO_EXTS)

    def get_image(self, key: str) -> pygame.Surface:
        return self.images[key]

    def get_audio(self, key: str) -> pygame.mixer.Sound:
        return self.audio[key]

    def try_get_image(self, key: str) -> Optional[pygame.Surface]:
        return self.images.get(key)

    def try_get_audio(self, key: str) -> Optional[pygame.mixer.Sound]:
        return self.audio.get(key)

    def has_image(self, key: str) -> bool:
        return key in self.images

    def has_audio(self, key: str) -> bool:
        return key in self.audio

    def list_images(self) -> List[str]:
        return sorted(self.images.keys())

    def list_audio(self) -> List[str]:
        return sorted(self.audio.keys())

    def reload_image(self, key: str) -> bool:
        """해당 key의 이미지를 파일에서 다시 로드."""
        path = self._image_path_by_key.get(key)
        if not path or not path.exists():
            return False
        surf = self._load_image_file(path)
        self.images[key] = surf
        return True

    def reload_audio(self, key: str) -> bool:
        """해당 key의 오디오를 파일에서 다시 로드."""
        path = self._audio_path_by_key.get(key)
        if not path or not path.exists():
            return False
        snd = self._load_audio_file(path)
        self.audio[key] = snd
        return True

    def unload_image(self, key: str) -> bool:
        if key in self.images:
            del self.images[key]
            self._taken_keys.discard(key)
            self._image_path_by_key.pop(key, None)
            return True
        return False

    def unload_audio(self, key: str) -> bool:
        if key in self.audio:
            del self.audio[key]
            self._taken_keys.discard(key)
            self._audio_path_by_key.pop(key, None)
            return True
        return False

    # ---------------------------
    # Internal loading
    # ---------------------------

    def _load_dir(self, root: Path, kind: Literal["image", "audio"], exts: set[str]) -> None:
        if not root.exists():
            return
        files = self._iter_files(root, exts)
        for f in files:
            key = self._make_key(f, root)
            # 키 충돌 시: 상대경로 키('images/ui/button')로 강등
            if key in self._taken_keys:
                key = self._relative_key_from_root(f, root)  # path 모드 강제
            self._taken_keys.add(key)

            try:
                if kind == "image":
                    surf = self._load_image_file(f)
                    self.images[key] = surf
                    self._image_path_by_key[key] = f
                else:
                    snd = self._load_audio_file(f)
                    self.audio[key] = snd
                    self._audio_path_by_key[key] = f
            except Exception as e:
                # 실패해도 전체 진행을 막지 않음
                print(f"[AssetRegistry] Failed to load {kind}: {f} ({e})")

    def _iter_files(self, root: Path, exts: set[str]) -> Iterable[Path]:
        if self.recursive:
            it = root.rglob("*")
        else:
            it = root.glob("*")
        for p in it:
            if p.is_file() and p.suffix.lower() in exts:
                yield p

    def _make_key(self, file_path: Path, root: Path) -> str:
        """key_mode에 따른 키 생성. 충돌 시 호출부에서 상대경로 키로 대체."""
        if self.key_mode == "path":
            return self._relative_key_from_root(file_path, root)
        elif self.key_mode == "name":
            return file_path.name
        else:  # stem
            return file_path.stem

    def _relative_key_from_root(self, file_path: Path, root: Path) -> str:
        # 루트 기준 상대경로에서 확장자는 제거, 구분자는 '/'로 통일
        rel = file_path.relative_to(root).as_posix()
        # 'ui/button.png' → 'ui/button' (확장자 제거)
        if rel.lower().endswith(file_path.suffix.lower()):
            rel = rel[: -len(file_path.suffix)]
        return rel

    def _load_image_file(self, path: Path) -> pygame.Surface:
        img = pygame.image.load(str(path))
        if not self.convert_images:
            return img
        # 알파 채널 포함 여부에 따라 convert/convert_alpha
        try:
            return img.convert_alpha() if img.get_alpha() is not None else img.convert()
        except pygame.error:
            # display 초기화 전이면 convert가 실패할 수 있음
            return img

    def _load_audio_file(self, path: Path) -> pygame.mixer.Sound:
        # mixer 미초기화 환경이면 예외가 날 수 있음 → 호출부에서 mixer.init 시도함
        return pygame.mixer.Sound(str(path))

    # ---------------------------
    # 헬퍼(디버그/메타)
    # ---------------------------

    def debug_summary(self) -> str:
        return (
            f"[AssetRegistry] images: {len(self.images)}, "
            f"audio: {len(self.audio)}, base: {self.base_dir}"
        )

    def get_image_path(self, key: str) -> Optional[Path]:
        return self._image_path_by_key.get(key)

    def get_audio_path(self, key: str) -> Optional[Path]:
        return self._audio_path_by_key.get(key)
