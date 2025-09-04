import json, os
from typing import List, Dict, Any

DEFAULT_PATH = "userdata.json"

class AppState:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self.username: str = "Guest"
        self.theme: str = "dark"         # default: dark
        self.recent: List[str] = []

        # NEW: window & UI options
        self.resizable: bool = False     # lock/allow window resize
        self.ui_scale: float = 1.0       # 1.0 = 100%, 1.25 = 125%, etc.

    def push_recent(self, name: str, limit: int = 8):
        if not name: return
        if name in self.recent:
            self.recent.remove(name)
        self.recent.insert(0, name)
        if len(self.recent) > limit:
            self.recent = self.recent[:limit]

    def load(self):
        if not os.path.exists(self.path):
            return self
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            self.username = data.get("username", self.username)
            self.theme    = data.get("theme", self.theme)
            self.recent   = list(data.get("recent", self.recent))
            self.resizable= bool(data.get("resizable", self.resizable))
            self.ui_scale = float(data.get("ui_scale", self.ui_scale))
        except Exception:
            pass
        return self

    def save(self):
        data = {
            "username": self.username,
            "theme":    self.theme,
            "recent":   self.recent,
            "resizable": self.resizable,
            "ui_scale":  self.ui_scale,
        }
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
