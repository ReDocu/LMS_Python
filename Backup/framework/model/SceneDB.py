from model.model import Model

from scenes.title_scene import TitleScene
from scenes.main_scene import MainScene

class SceneDB(Model):
    def __init__(self):
        super().__init__()
        # 초기 기능 세팅 

        self.curScene = None   
        self.LoadScene()

    # ---- Scene 연결 ---
    def LoadScene(self):
        # 초기값 세팅
        self.AddScene('MAIN',MainScene())
        self.AddScene('TITLE',TitleScene())
    
    def ChangeScene(self, selectScene):
        if self.curScene != None:
            self.dataDicts[self.curScene].destroy()

        self.curScene = self.dataDicts[selectScene]
        self.curScene.awake()

    def NextScene(self, selectData):
        nextIndex = self.dataList.index(selectData) + 1
        if self.dataList.count < nextIndex:
            nextIndex = 0

        self.ChangeScene(self,self.dataList[nextIndex])
    
    def PrevScene(self, selectData):
        nextIndex = self.dataList.index(selectData) - 1
        if 0 > nextIndex:
            nextIndex = self.dataList.count - 1
        
        self.ChangeScene(self,self.dataList[nextIndex])
        
    def CurScene(self):
        return self.curScene