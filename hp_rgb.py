"""Backend RGB para HP Omen — sysfs hp-rgb-lighting + síntesis tecla→zona."""
from __future__ import annotations

import colorsys
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DRIVER_PATHS = (
    "/sys/devices/platform/hp-rgb-lighting",
    "/sys/devices/platform/hp_rgb_lighting",
)
HEX6 = re.compile(r"^[0-9A-Fa-f]{6}$")
RGB = Tuple[int, int, int]


@dataclass
class DriverState:
    available: bool
    path: Optional[str] = None
    zone_count: int = 8
    error: str = ""


def find_driver() -> DriverState:
    for path in DRIVER_PATHS:
        if os.path.isdir(path) and os.path.exists(f"{path}/zone0"):
            return DriverState(True, path)
    try:
        with open("/proc/modules") as f:
            if "hp_rgb_lighting" in f.read():
                return DriverState(
                    False,
                    error="Módulo cargado pero sysfs no encontrado. ¿Reiniciaste tras instalar?",
                )
    except OSError:
        pass
    return DriverState(
        False,
        error="Driver hp-rgb-lighting no instalado. Ejecuta: sudo bash install.sh",
    )


def _hex(rgb: RGB) -> str:
    return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _parse_hex(value: str) -> RGB:
    v = value.strip().lstrip("#").upper()
    if not HEX6.match(v):
        raise ValueError(f"Color inválido: {value!r}")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def scale_rgb(rgb: RGB, brightness: float) -> RGB:
    b = max(0.0, min(1.0, brightness))
    return int(rgb[0] * b), int(rgb[1] * b), int(rgb[2] * b)


class HpRgbBackend:
    """Control de hardware vía sysfs (8 zonas)."""

    def __init__(self) -> None:
        self.state = find_driver()
        self.path = self.state.path
        self._last_zones: List[Optional[str]] = [None] * 8

    @property
    def available(self) -> bool:
        return bool(self.path)

    def read_zone(self, zone: int) -> Optional[RGB]:
        if not self.path or not 0 <= zone < 8:
            return None
        try:
            raw = Path(f"{self.path}/zone{zone}").read_text().strip()
            return _parse_hex(raw.split()[0][:6])
        except OSError:
            return None

    def write_zone(self, zone: int, rgb: RGB) -> bool:
        if not self.path or not 0 <= zone < 8:
            return False
        hx = _hex(rgb)
        if self._last_zones[zone] == hx:
            return True
        try:
            Path(f"{self.path}/zone{zone}").write_text(hx)
            self._last_zones[zone] = hx
            return True
        except PermissionError:
            self.state.error = "Sin permiso en sysfs. Ejecuta install.sh (regla udev) o sudo."
            return False
        except OSError as e:
            self.state.error = str(e)
            return False

    def write_all_zones(self, colors: Iterable[RGB]) -> bool:
        ok = True
        for i, rgb in enumerate(list(colors)[:8]):
            ok = self.write_zone(i, rgb) and ok
        return ok

    def set_power(self, on: bool) -> bool:
        if not self.path:
            return False
        try:
            Path(f"{self.path}/brightness").write_text("1" if on else "0")
            return True
        except OSError:
            return False

    @staticmethod
    def synthesize_zones(
        key_colors: Dict[str, RGB],
        key_zones: Dict[str, int],
        zone_count: int = 8,
        fallback: RGB = (255, 0, 0),
    ) -> List[RGB]:
        """Promedia colores de teclas por zona hardware."""
        buckets: List[List[RGB]] = [[] for _ in range(zone_count)]
        for key_id, rgb in key_colors.items():
            z = key_zones.get(key_id, 0)
            if 0 <= z < zone_count:
                buckets[z].append(rgb)
        out: List[RGB] = []
        for z in range(zone_count):
            if buckets[z]:
                n = len(buckets[z])
                out.append(
                    (
                        sum(c[0] for c in buckets[z]) // n,
                        sum(c[1] for c in buckets[z]) // n,
                        sum(c[2] for c in buckets[z]) // n,
                    )
                )
            else:
                out.append(fallback)
        return out

    def apply_key_map(
        self,
        key_colors: Dict[str, RGB],
        key_zones: Dict[str, int],
        brightness: float = 1.0,
        power: bool = True,
    ) -> bool:
        if not self.available:
            return False
        self.set_power(power)
        if not power:
            return self.write_all_zones([(0, 0, 0)] * 8)
        zones = self.synthesize_zones(key_colors, key_zones)
        zones = [scale_rgb(c, brightness) for c in zones]
        return self.write_all_zones(zones)

    def apply_direct_zones(self, zone_colors: List[RGB], brightness: float = 1.0, power: bool = True) -> bool:
        if not self.available:
            return False
        self.set_power(power)
        if not power:
            return self.write_all_zones([(0, 0, 0)] * 8)
        scaled = [scale_rgb(c, brightness) for c in zone_colors[:8]]
        while len(scaled) < 8:
            scaled.append(scaled[-1] if scaled else (0, 0, 0))
        return self.write_all_zones(scaled)


@dataclass
class EffectState:
    mode: str = "static"  # static, breathing, rainbow, wave, cycle
    speed: int = 50
    brightness: int = 100
    power: bool = True
    direction: str = "ltr"
    base_color: RGB = (255, 0, 0)
    zone_colors: List[RGB] = field(default_factory=lambda: [(255, 0, 0)] * 8)


def effect_frame(state: EffectState, t: float, key_index: int = 0, zone_index: int = 0) -> RGB:
    """Calcula color para un frame de animación."""
    bri = state.brightness / 100.0
    if not state.power:
        return (0, 0, 0)

    if state.mode == "static":
        if len(state.zone_colors) > zone_index:
            return scale_rgb(state.zone_colors[zone_index], bri)
        return scale_rgb(state.base_color, bri)

    if state.mode == "breathing":
        period = max(1.5, 8.0 - state.speed * 0.06)
        phase = 0.15 + 0.85 * ((__import__("math").sin(2 * __import__("math").pi * t / period) + 1) / 2)
        c = state.base_color
        return int(c[0] * phase * bri), int(c[1] * phase * bri), int(c[2] * phase * bri)

    if state.mode == "rainbow" or state.mode == "cycle":
        hue = (t * (state.speed * 0.004) + key_index * 0.02 + zone_index * 0.08) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, bri)
        return int(r * 255), int(g * 255), int(b * 255)

    if state.mode == "wave":
        cols = state.zone_colors[:4] or [state.base_color]
        while len(cols) < 4:
            cols.append(cols[-1])
        step = max(0.06, 0.42 - state.speed * 0.0036)
        pos = t / step
        shift = int(pos) if state.direction == "ltr" else -int(pos)
        frac = pos - int(pos)
        idx = (zone_index + shift) % 4
        nxt = (idx + 1) % 4
        c0, c1 = cols[idx], cols[nxt]
        if state.direction == "rtl":
            frac = 1.0 - frac
        r = int((c0[0] + (c1[0] - c0[0]) * frac) * bri)
        g = int((c0[1] + (c1[1] - c0[1]) * frac) * bri)
        b = int((c0[2] + (c1[2] - c0[2]) * frac) * bri)
        return r, g, b

    return scale_rgb(state.base_color, bri)
