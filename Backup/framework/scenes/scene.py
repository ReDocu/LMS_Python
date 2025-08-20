class Scene():
    def __init__(self):
        print("클래스 Scene 입니다")
    
    def handle_event(self, e):
        cur = self.current()
        if cur: cur.handle_event(e)

    def awake(self):
        print("시작합니다")

    def destroy(self):
        print("종료합니다")

    def render(self):
        print("렌더")
    
    def update(self):
        print("업데이트")