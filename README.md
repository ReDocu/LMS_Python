# LMS_Python

project_root/
├─ run.py                         # 진입 스크립트(개발 중엔 이거로 실행)
├─ requirements.txt               # 의존성 (pygame 등)
└─ src/
   ├─ __init__.py
   ├─ game.py                     # App/Settings 조립 + main()
   │
   ├─ core/                       # 최소 코어(엔진 뼈대)
   │  ├─ __init__.py
   │  ├─ app.py                   # App(메인 루프, 초기화)
   │  ├─ scene.py                 # Scene 베이스 + SceneManager
   │  └─ config.py                # Settings(dataclass)
   │
   ├─ model/                      # 데이터/레지스트리 계층
   │  ├─ __init__.py
   │  └─ scene_db.py              # SceneDB: 이름→팩토리 매핑(상향식 확장 포인트)
   │
   ├─ scenes/                     # 게임 상태/화면(독립 모듈 단위)
   │  ├─ __init__.py              # register_scenes(db): 씬 등록
   │  ├─ title.py                 # TitleScene
   │  └─ main.py                  # MainScene(데모)
   │
   ├─ modules/                    # 기능 모듈 (배경, 텍스트, 오디오 등)
   │  ├─ __init__.py
   │  ├─ background/
   │  │  ├─ __init__.py
   │  │  └─ system.py             # BackgroundSystem(레이어 관리 예시)
   │  └─ text/
   │     ├─ __init__.py
   │     └─ font_manager.py       # FontManager(폰트 캐시)
   │
   ├─ assets/                     # 리소스(이미지/폰트/사운드)
   │  ├─ images/
   │  ├─ fonts/
   │  └─ sounds/
   │
   └─ utils/                      # 범용 유틸(필요 시)
      ├─ __init__.py
      └─ geometry.py