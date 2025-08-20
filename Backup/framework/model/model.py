class Model():
    def __init__(self):
        # Model이 안 만들어 준다면 아래 두 줄로 자체 초기화
        self.dataDicts = {}
        self.dataList = [] 
    
    def AddScene(self, name, scene):
        self.dataDicts[name] = scene
        # sceneList가 list라면:
        if name not in self.dataList:
            self.dataList.append(name)

    def PrintInfo(self):
        print("[SceneDB] registered scenes:", ", ".join(map(str, self.dataList)))
        return list(self.dataList)