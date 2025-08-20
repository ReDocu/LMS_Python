# main.py
from controller.app import GameApp

def main() -> None:
    # 해상도 / 제목 세팅
    app = GameApp(size=(1024, 800), title="MVC Pygame — Stage 1")
    app.run()  # 실행! 

if __name__ == "__main__":
    main()