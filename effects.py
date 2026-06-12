"""Motor de efectos RGB — estilo Omen Light Studio (Windows)."""
from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

RGB = Tuple[int, int, int]

EFFECT_CATALOG: List[Tuple[str, str, str]] = [
    ("static", "Estático", "Color fijo por tecla"),
    ("breathing", "Respiración", "Pulsa suavemente"),
    ("color_cycle", "Ciclo de color", "Rota por el espectro"),
    ("rainbow", "Arcoíris", "Arcoíris en todo el teclado"),
    ("rainbow_wave", "Ola arcoíris", "Arcoíris en movimiento"),
    ("wave", "Ola de color", "Onda multicolor"),
    ("spectrum", "Espectro", "Gradiente animado"),
    ("ripple", "Ondulación", "Ondas desde el centro"),
    ("aurora", "Aurora", "Luces boreales"),
    ("fire", "Fuego", "Llama naranja/roja"),
]


@dataclass
class EffectConfig:
    mode: str = "static"
    speed: int = 50          # 1-100
    brightness: int = 100    # 0-100
    power: bool = True
    direction: str = "ltr"   # ltr | rtl
    primary: RGB = (255, 0, 0)
    secondary: RGB = (0, 0, 255)
    palette: List[RGB] = field(default_factory=lambda: [
        (255, 0, 0), (255, 128, 0), (255, 255, 0),
        (0, 255, 0), (0, 255, 255), (0, 0, 255), (128, 0, 255),
    ])
    zone_colors: List[RGB] = field(default_factory=lambda: [(255, 0, 0)] * 8)


def _bri(c: RGB, brightness: float) -> RGB:
    b = max(0.0, min(1.0, brightness))
    return int(c[0] * b), int(c[1] * b), int(c[2] * b)


def _lerp(a: RGB, b: RGB, t: float) -> RGB:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _hsv(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def _palette_color(palette: List[RGB], t: float) -> RGB:
    if not palette:
        return (255, 0, 0)
    n = len(palette)
    ft = (t % 1.0) * n
    i = int(ft) % n
    j = (i + 1) % n
    frac = ft - int(ft)
    return _lerp(palette[i], palette[j], frac)


def key_position(key_id: str, keys_meta: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
    return keys_meta.get(key_id, (0.5, 0.5))


def compute_effect_color(
    cfg: EffectConfig,
    t: float,
    key_id: str,
    key_index: int,
    zone: int,
    static_color: RGB,
    keys_meta: Dict[str, Tuple[float, float]],
) -> RGB:
    """Color de una tecla para el frame actual."""
    bri = cfg.brightness / 100.0
    if not cfg.power:
        return (0, 0, 0)

    nx, ny = key_position(key_id, keys_meta)
    spd = cfg.speed / 100.0

    if cfg.mode == "static":
        return _bri(static_color, bri)

    if cfg.mode == "breathing":
        period = max(1.2, 6.0 - spd * 5.0)
        phase = 0.12 + 0.88 * ((math.sin(2 * math.pi * t / period) + 1) / 2)
        c = cfg.primary
        return int(c[0] * phase * bri), int(c[1] * phase * bri), int(c[2] * phase * bri)

    if cfg.mode == "color_cycle":
        hue = (t * (0.08 + spd * 0.25)) % 1.0
        return _bri(_hsv(hue, 1.0, 1.0), bri)

    if cfg.mode == "rainbow":
        hue = (nx * 0.85 + ny * 0.15 + t * (0.02 + spd * 0.08)) % 1.0
        return _bri(_hsv(hue, 1.0, 1.0), bri)

    if cfg.mode == "rainbow_wave":
        sign = 1.0 if cfg.direction == "ltr" else -1.0
        hue = (nx + sign * t * (0.15 + spd * 0.55)) % 1.0
        return _bri(_hsv(hue, 1.0, 1.0), bri)

    if cfg.mode == "wave":
        pal = cfg.palette[:4] if cfg.palette else [cfg.primary, cfg.secondary, (0, 255, 0), (255, 255, 0)]
        while len(pal) < 4:
            pal.append(pal[-1])
        step = max(0.05, 0.35 - spd * 0.28)
        pos = t / step
        shift = int(pos) if cfg.direction == "ltr" else -int(pos)
        frac = pos - int(pos)
        if cfg.direction == "rtl":
            frac = 1.0 - frac
        # Posición horizontal de la tecla determina fase en la ola
        idx = (int(nx * 4) + shift) % 4
        nxt = (idx + 1) % 4
        return _bri(_lerp(pal[idx], pal[nxt], frac), bri)

    if cfg.mode == "spectrum":
        sign = 1.0 if cfg.direction == "ltr" else -1.0
        pt = (nx + sign * t * (0.1 + spd * 0.4)) % 1.0
        return _bri(_palette_color(cfg.palette, pt), bri)

    if cfg.mode == "ripple":
        cx, cy = 0.45, 0.55
        dist = math.hypot(nx - cx, ny - cy)
        wave = math.sin((dist * 12.0 - t * (2.0 + spd * 8.0)) * math.pi)
        intensity = (wave + 1) / 2
        base = _palette_color(cfg.palette, (dist + t * 0.05) % 1.0)
        dark = (int(base[0] * 0.08), int(base[1] * 0.08), int(base[2] * 0.08))
        return _bri(_lerp(dark, base, intensity), bri)

    if cfg.mode == "aurora":
        h1 = (nx * 0.3 + t * (0.03 + spd * 0.06)) % 1.0
        h2 = (ny * 0.4 + t * (0.02 + spd * 0.04)) % 1.0
        c1 = _hsv(h1, 0.85, 1.0)
        c2 = _hsv(h2, 0.7, 0.9)
        mix = 0.5 + 0.5 * math.sin(t * (1.0 + spd * 2.0) + nx * 4.0)
        return _bri(_lerp(c1, c2, mix), bri)

    if cfg.mode == "fire":
        flicker = abs(math.sin(t * (3.0 + spd * 10.0) + key_index * 0.7))
        flicker *= abs(math.sin(t * (5.0 + spd * 7.0) + nx * 9.0))
        hot = (255, int(80 + 120 * flicker), 0)
        cool = (120, 20, 0)
        heat = max(0.0, 1.0 - ny * 0.9 + flicker * 0.35)
        return _bri(_lerp(cool, hot, heat), bri)

    return _bri(static_color, bri)


def is_animated(mode: str) -> bool:
    return mode != "static"
