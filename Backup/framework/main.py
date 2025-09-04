from framework.app import GameApp

def main() -> None:
    # 해상도 : (size=(1024, 800)
    # TITLE : title="My FrameWork"
    app = GameApp(size=(1024, 800), title="My FrameWork")
    app.run()  # 실행 

if __name__ == "__main__":
    main()