"""Layout del teclado OMEN MAX 16 (full-size con numpad)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class KeyDef:
    id: str
    label: str
    x: float
    y: float
    w: float
    h: float
    zone: int  # zona hardware 0-7


# Unidades de grid (1 u ≈ 18 px en el canvas)
def _k(id_: str, label: str, x: float, y: float, w: float, h: float = 1.0, zone: int = 0) -> KeyDef:
    return KeyDef(id_, label, x, y, w, h, zone)


def build_layout() -> List[KeyDef]:
    keys: List[KeyDef] = []
    u = 1.0

    # Fila función
    fx = 0.0
    for i, (kid, lab, z) in enumerate(
        [
            ("esc", "Esc", 0),
            ("f1", "F1", 0),
            ("f2", "F2", 0),
            ("f3", "F3", 0),
            ("f4", "F4", 0),
            ("f5", "F5", 1),
            ("f6", "F6", 1),
            ("f7", "F7", 1),
            ("f8", "F8", 1),
            ("f9", "F9", 2),
            ("f10", "F10", 2),
            ("f11", "F11", 2),
            ("f12", "F12", 2),
            ("prt", "Prt", 2),
            ("ins", "Ins", 3),
            ("del", "Del", 3),
        ]
    ):
        w = 1.5 if kid == "esc" else 1.0
        keys.append(_k(kid, lab, fx, 0, w, zone=z))
        fx += w + 0.15

    # Fila números
    row1 = [
        ("grave", "`", 0),
        ("1", "1", 0),
        ("2", "2", 0),
        ("3", "3", 0),
        ("4", "4", 0),
        ("5", "5", 1),
        ("6", "6", 1),
        ("7", "7", 1),
        ("8", "8", 1),
        ("9", "9", 2),
        ("0", "0", 2),
        ("minus", "-", 2),
        ("equal", "=", 2),
        ("back", "⌫", 2),
    ]
    x = 0.0
    for kid, lab, z in row1:
        w = 2.0 if kid == "back" else 1.0
        keys.append(_k(kid, lab, x, 1.2, w, zone=z))
        x += w + 0.12

    # QWERTY
    row2 = [
        ("tab", "Tab", 0),
        ("q", "Q", 0),
        ("w", "W", 0),
        ("e", "E", 0),
        ("r", "R", 0),
        ("t", "T", 1),
        ("y", "Y", 1),
        ("u", "U", 1),
        ("i", "I", 2),
        ("o", "O", 2),
        ("p", "P", 2),
        ("lbr", "[", 2),
        ("rbr", "]", 2),
        ("bsl", "\\", 2),
    ]
    x = 0.0
    for kid, lab, z in row2:
        w = 1.5 if kid == "tab" else (1.5 if kid == "bsl" else 1.0)
        keys.append(_k(kid, lab, x, 2.4, w, zone=z))
        x += w + 0.12

    # ASDF
    row3 = [
        ("caps", "Caps", 0),
        ("a", "A", 0),
        ("s", "S", 0),
        ("d", "D", 0),
        ("f", "F", 1),
        ("g", "G", 1),
        ("h", "H", 1),
        ("j", "J", 1),
        ("k", "K", 2),
        ("l", "L", 2),
        ("semi", ";", 2),
        ("quote", "'", 2),
        ("enter", "↵", 2),
    ]
    x = 0.0
    for kid, lab, z in row3:
        w = 1.8 if kid == "caps" else (2.2 if kid == "enter" else 1.0)
        keys.append(_k(kid, lab, x, 3.6, w, zone=z))
        x += w + 0.12

    # ZXCV
    row4 = [
        ("lshift", "⇧", 0),
        ("z", "Z", 0),
        ("x", "X", 0),
        ("c", "C", 0),
        ("v", "V", 1),
        ("b", "B", 1),
        ("n", "N", 1),
        ("m", "M", 1),
        ("comma", ",", 2),
        ("dot", ".", 2),
        ("slash", "/", 2),
        ("rshift", "⇧", 2),
    ]
    x = 0.0
    for kid, lab, z in row4:
        w = 2.3 if kid == "lshift" else (2.8 if kid == "rshift" else 1.0)
        keys.append(_k(kid, lab, x, 4.8, w, zone=z))
        x += w + 0.12

    # Fila inferior
    row5 = [
        ("lctrl", "Ctrl", 0),
        ("lwin", "⊞", 0),
        ("lalt", "Alt", 0),
        ("space", "Space", 1),
        ("ralt", "Alt", 2),
        ("rwin", "⊞", 2),
        ("menu", "☰", 2),
        ("rctrl", "Ctrl", 2),
    ]
    x = 0.0
    for kid, lab, z in row5:
        w = 6.5 if kid == "space" else 1.3
        keys.append(_k(kid, lab, x, 6.0, w, zone=z))
        x += w + 0.12

    # Numpad + flechas (zona 7)
    nx = x + 0.5
    numpad = [
        ("numlk", "Num", nx, 1.2, 1.0, 7),
        ("num_slash", "/", nx + 1.12, 1.2, 1.0, 7),
        ("num_star", "*", nx + 2.24, 1.2, 1.0, 7),
        ("num_minus", "-", nx + 3.36, 1.2, 1.0, 7),
        ("num7", "7", nx, 2.4, 1.0, 7),
        ("num8", "8", nx + 1.12, 2.4, 1.0, 7),
        ("num9", "9", nx + 2.24, 2.4, 1.0, 7),
        ("num_plus", "+", nx + 3.36, 2.4, 1.0, 2.2, 7),
        ("num4", "4", nx, 3.6, 1.0, 7),
        ("num5", "5", nx + 1.12, 3.6, 1.0, 7),
        ("num6", "6", nx + 2.24, 3.6, 1.0, 7),
        ("num1", "1", nx, 4.8, 1.0, 7),
        ("num2", "2", nx + 1.12, 4.8, 1.0, 7),
        ("num3", "3", nx + 2.24, 4.8, 1.0, 7),
        ("nument", "↵", nx + 3.36, 4.8, 1.0, 2.2, 7),
        ("num0", "0", nx, 6.0, 2.12, 1.0, 7),
        ("numdot", ".", nx + 2.24, 6.0, 1.0, 7),
    ]
    for item in numpad:
        if len(item) == 6:
            kid, lab, px, py, pw, z = item
            ph = 1.0
        else:
            kid, lab, px, py, pw, ph, z = item
        keys.append(KeyDef(kid, lab, px, py, pw, ph, z))

    # Flechas
    ax = nx + 0.2
    keys += [
        _k("up", "↑", ax + 1.12, 6.0, 1.0, zone=7),
        _k("left", "←", ax, 7.2, 1.0, zone=7),
        _k("down", "↓", ax + 1.12, 7.2, 1.0, zone=7),
        _k("right", "→", ax + 2.24, 7.2, 1.0, zone=7),
    ]

    return keys


KEYS: List[KeyDef] = build_layout()
KEY_BY_ID: Dict[str, KeyDef] = {k.id: k for k in KEYS}
KEY_ZONES: Dict[str, int] = {k.id: k.zone for k in KEYS}
UNIT_PX = 18.0
CANVAS_W = int(max(k.x + k.w for k in KEYS) * UNIT_PX + 40)
CANVAS_H = int(max(k.y + k.h for k in KEYS) * UNIT_PX + 40)


def default_key_colors(default: RGB = (30, 30, 40)) -> Dict[str, RGB]:
    return {k.id: default for k in KEYS}


ZONE_LABELS = [
    "Zona 1 — Esc/F izq",
    "Zona 2 — F der",
    "Zona 3 — Números izq",
    "Zona 4 — Números der",
    "Zona 5 — QWER/ASDF izq",
    "Zona 6 — UIOP/JKL",
    "Zona 7 — ZXCV/Space",
    "Zona 8 — Numpad/Flechas",
]

# Posición normalizada (0-1) centro de cada tecla — para efectos espaciales
_max_x = max(k.x + k.w for k in KEYS)
_max_y = max(k.y + k.h for k in KEYS)
KEYS_META: Dict[str, Tuple[float, float]] = {
    k.id: ((k.x + k.w / 2) / _max_x, (k.y + k.h / 2) / _max_y) for k in KEYS
}
