"""
Color schemes matching SecureCRT presets and ANSI 16/256-color palettes.
"""

from typing import Dict, Tuple

# Predefined palettes (Foreground, Background, Cursor)
COLOR_SCHEMES: Dict[str, Dict[str, str]] = {
    "Monochrome": {
        "foreground": "#000000",
        "background": "#FFFFFF",
        "cursor": "#000000",
    },
    "Traditional": {
        "foreground": "#00FF00",
        "background": "#000000",
        "cursor": "#00FF00",
    },
    "Yellow / Black": {
        "foreground": "#FFFF00",
        "background": "#000000",
        "cursor": "#FFFF00",
    },
    "Black / Floral White": {
        "foreground": "#000000",
        "background": "#FFFAF0",
        "cursor": "#000000",
    },
    "White / Black": {
        "foreground": "#FFFFFF",
        "background": "#000000",
        "cursor": "#FFFFFF",
    },
    "Windows": {
        "foreground": "#000000",
        "background": "#FFFFFF",
        "cursor": "#000000",
    },
    "Black / Cyan": {
        "foreground": "#000000",
        "background": "#00FFFF",
        "cursor": "#000000",
    },
    "Solarized Dark": {
        "foreground": "#839496",
        "background": "#002B36",
        "cursor": "#93A1A1",
    },
    "OneDark": {
        "foreground": "#ABB2BF",
        "background": "#282C34",
        "cursor": "#528BFF",
    },
}

# Standard 16 ANSI colors (Index 0-7 Normal, 8-15 Bright)
ANSI_16_COLORS: Tuple[str, ...] = (
    "#000000",  # 0: Black
    "#C00000",  # 1: Red
    "#00C000",  # 2: Green
    "#C0C000",  # 3: Yellow
    "#0000C0",  # 4: Blue
    "#C000C0",  # 5: Magenta
    "#00C0C0",  # 6: Cyan
    "#C0C0C0",  # 7: White (Light Gray)
    "#808080",  # 8: Bright Black (Dark Gray)
    "#FF0000",  # 9: Bright Red
    "#00FF00",  # 10: Bright Green
    "#FFFF00",  # 11: Bright Yellow
    "#0000FF",  # 12: Bright Blue
    "#FF00FF",  # 13: Bright Magenta
    "#00FFFF",  # 14: Bright Cyan
    "#FFFFFF",  # 15: Bright White
)


def get_scheme(name: str) -> Dict[str, str]:
    """Returns color scheme dictionary with foreground, background, cursor."""
    return COLOR_SCHEMES.get(name, COLOR_SCHEMES["Traditional"])
