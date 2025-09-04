from typing import Tuple, Dict

Color = Tuple[int,int,int]

THEMES: Dict[str, dict] = {
    "light": {
        "bg": (245,248,252),
        "panel": (255,255,255),
        "panel_border": (200,200,200),
        "text": (40,40,60),
        "button_colors": { # default, hover, active, disabled
            "default": (70,130,180),
            "hover":   (100,160,210),
            "active":  (40,90,140),
            "disabled":(180,180,180),
        }
    },
    "dark": {
        "bg": (24,28,32),
        "panel": (36,40,46),
        "panel_border": (70,70,80),
        "text": (230,230,235),
        "button_colors": {
            "default": (90,140,200),
            "hover":   (120,170,230),
            "active":  (60,100,150),
            "disabled":(90,90,90),
        }
    }
}

def get_colors(theme_name: str):
    base = THEMES.get(theme_name, THEMES["light"]).copy()
    base["name"] = theme_name if theme_name in THEMES else "light"
    return base
    #return THEMES.get(theme_name, THEMES["light"])
