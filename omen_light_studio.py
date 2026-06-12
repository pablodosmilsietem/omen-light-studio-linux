#!/usr/bin/env python3
"""
Omen Light Studio — clon funcional de HP Omen Light Studio para Linux.
Tiempo real: cada cambio se aplica al teclado al instante.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk
import cairo

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from effects import EFFECT_CATALOG, EffectConfig, compute_effect_color, is_animated
from hp_rgb import HpRgbBackend
from keyboard_layout import (
    CANVAS_H,
    CANVAS_W,
    KEYS,
    KEYS_META,
    KEY_ZONES,
    UNIT_PX,
    ZONE_LABELS,
    default_key_colors,
)

RGB = Tuple[int, int, int]
PROFILES_DIR = APP_DIR / "profiles"
FPS_MS = 33  # ~30 FPS tiempo real

OMEN_CSS = """
window, .omen-root { background-color: #0a0a0f; }
headerbar { background: #111118; color: #eee; }
.omen-title { color: #ff3657; font-weight: 800; font-size: 15px; letter-spacing: 1px; }
.omen-sidebar { background: #12121a; border-right: 1px solid #252530; }
.omen-section { color: #888; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; margin-top: 8px; }
.effect-card { background: #1a1a24; border: 2px solid #252530; border-radius: 10px; padding: 10px; min-height: 52px; }
.effect-card.active { border-color: #ff3657; background: rgba(255,54,87,0.12); }
.effect-name { color: #fff; font-weight: 600; font-size: 13px; }
.effect-desc { color: #666; font-size: 10px; }
.color-swatch { min-width: 32px; min-height: 32px; border-radius: 8px; border: 2px solid #333; padding: 0; }
.color-swatch.active { border-color: #ff3657; box-shadow: 0 0 8px rgba(255,54,87,0.5); }
.live-badge { color: #00e676; font-size: 11px; font-weight: 600; }
.kb-frame { background: #0d0d14; border: 1px solid #252530; border-radius: 12px; padding: 12px; }
"""

PRESETS = [
    "#FF3657", "#FF0000", "#FF6600", "#FFCC00", "#00FF88",
    "#00CCFF", "#0066FF", "#9900FF", "#FF00FF", "#FFFFFF",
]


def hex_to_rgb(h: str) -> RGB:
    h = h.lstrip("#").upper()
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb: RGB) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


class KeyboardCanvas(Gtk.DrawingArea):
    def __init__(self, app: "OmenLightStudio") -> None:
        super().__init__()
        self.app = app
        self.set_content_width(CANVAS_W)
        self.set_content_height(CANVAS_H)
        self.set_draw_func(self._draw)
        self._hover: Optional[str] = None
        self._painting = False

        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_press)
        click.connect("released", self._on_release)
        self.add_controller(click)

        drag = Gtk.GestureDrag.new()
        drag.connect("drag-update", self._on_drag)
        self.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)

    def _key_at(self, x: float, y: float) -> Optional[str]:
        for key in reversed(KEYS):
            kx = key.x * UNIT_PX + 12
            ky = key.y * UNIT_PX + 12
            kw = key.w * UNIT_PX - 4
            kh = key.h * UNIT_PX - 4
            if kx <= x <= kx + kw and ky <= y <= ky + kh:
                return key.id
        return None

    def _paint_at(self, x: float, y: float) -> None:
        kid = self._key_at(x, y)
        if not kid:
            return
        if self.app.paint_mode == "zone":
            self.app.paint_zone(KEY_ZONES[kid], live=True)
        else:
            self.app.paint_key(kid, live=True)
        self.queue_draw()

    def _on_press(self, _g, _n, x, y) -> None:
        self._painting = True
        self.app.switch_to_static_for_paint()
        self._paint_at(x, y)

    def _on_release(self, *_a) -> None:
        self._painting = False

    def _on_drag(self, gest, offset_x, offset_y) -> None:
        if not self._painting:
            return
        ok, sx, sy = gest.get_start_point()
        if ok:
            self._paint_at(sx + offset_x, sy + offset_y)

    def _on_motion(self, _c, x, y) -> None:
        kid = self._key_at(x, y)
        if kid != self._hover:
            self._hover = kid
            self.queue_draw()
        if self._painting:
            self._paint_at(x, y)

    def _on_leave(self, *_a) -> None:
        self._hover = None
        self.queue_draw()

    def _draw(self, _area, cr, _w, _h) -> None:
        for key in KEYS:
            kx = key.x * UNIT_PX + 12
            ky = key.y * UNIT_PX + 12
            kw = key.w * UNIT_PX - 4
            kh = key.h * UNIT_PX - 4
            rgb = self.app.display_colors.get(key.id, (25, 25, 35))
            r, g, b = [c / 255.0 for c in rgb]

            # Glow
            cr.save()
            cr.append_path(self._rounded_rect(kx - 1, ky - 1, kw + 2, kh + 2, 4))
            cr.set_source_rgba(r * 0.5, g * 0.5, b * 0.5, 0.35)
            cr.fill()
            cr.restore()

            cr.set_source_rgb(r * 0.75, g * 0.75, b * 0.75)
            cr.append_path(self._rounded_rect(kx, ky, kw, kh, 3))
            cr.fill()

            cr.set_source_rgb(min(1, r * 1.3 + 0.05), min(1, g * 1.3 + 0.05), min(1, b * 1.3 + 0.05))
            cr.set_line_width(1.0)
            cr.append_path(self._rounded_rect(kx + 0.5, ky + 0.5, kw - 1, kh - 1, 3))
            cr.stroke()

            cr.set_source_rgb(0.92, 0.92, 0.96)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(9 if len(key.label) > 3 else 10)
            te = cr.text_extents(key.label)
            cr.move_to(kx + (kw - te.width) / 2, ky + (kh + te.height) / 2 - 1)
            cr.show_text(key.label)

            if key.id == self._hover:
                cr.set_source_rgba(1, 1, 1, 0.25)
                cr.append_path(self._rounded_rect(kx, ky, kw, kh, 3))
                cr.fill()

    @staticmethod
    def _rounded_rect(x, y, w, h, r):
        p = cairo.Path()
        p.move_to(x + r, y)
        p.line_to(x + w - r, y)
        p.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        p.line_to(x + w, y + h - r)
        p.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        p.line_to(x + r, y + h)
        p.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        p.line_to(x, y + r)
        p.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        p.close_path()
        return p


class OmenLightStudio(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="com.pablomontes.omen-light-studio")
        self.backend = HpRgbBackend()
        self.key_colors: Dict[str, RGB] = default_key_colors((20, 20, 28))
        self.display_colors: Dict[str, RGB] = dict(self.key_colors)
        self.paint_mode = "key"
        self.brush: RGB = (255, 54, 87)
        self.fx = EffectConfig(primary=self.brush)
        self._zone_direct: List[RGB] = [(255, 54, 87)] * 8
        self._tick_id: Optional[int] = None
        self._dirty_hw = True
        self._effect_cards: Dict[str, Gtk.Box] = {}
        self._active_effect = "static"
        self._swatch_btns: List[Gtk.Button] = []
        self.win: Optional[Adw.ApplicationWindow] = None
        self.canvas: Optional[KeyboardCanvas] = None
        self.live_label: Optional[Gtk.Label] = None
        self.brightness_scale: Optional[Gtk.Scale] = None
        self.speed_scale: Optional[Gtk.Scale] = None

    def do_activate(self) -> None:
        self._load_css()
        self.win = Adw.ApplicationWindow(application=self, title="OMEN Light Studio")
        self.win.set_default_size(1280, 780)
        self.win.add_css_class("omen-root")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(root)

        header = Adw.HeaderBar()
        title = Gtk.Label(label="OMEN LIGHT STUDIO", css_classes=["omen-title"])
        header.set_title_widget(title)

        prof_btn = Gtk.MenuButton(icon_name="document-open-symbolic")
        prof_menu = Gio.Menu()
        prof_menu.append("Guardar perfil", "app.save")
        prof_menu.append("Cargar perfil", "app.load")
        prof_btn.set_menu_model(prof_menu)
        header.pack_end(prof_btn)

        self.live_label = Gtk.Label(label="● EN VIVO", css_classes=["live-badge"])
        header.pack_end(self.live_label)

        root.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        root.append(body)

        sidebar = Gtk.ScrolledWindow(vscrollbar_policy=Gtk.PolicyType.NEVER)
        sidebar.set_size_request(280, -1)
        sidebar.add_css_class("omen-sidebar")
        sidebar.set_child(self._build_sidebar())
        body.append(sidebar)

        main = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12,
            hexpand=True, vexpand=True,
            margin_top=16, margin_bottom=16, margin_start=16, margin_end=16,
        )
        body.append(main)

        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["kb-frame"], vexpand=True)
        self.canvas = KeyboardCanvas(self)
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, vexpand=True)
        center.append(self.canvas)
        frame.append(center)
        main.append(frame)

        if not self.backend.available:
            banner = Adw.Banner(
                title="Driver no detectado — ejecuta: sudo bash install.sh",
                reveal=True,
            )
            main.prepend(banner)

        self._add_actions()
        self.win.present()
        self._select_effect("static")
        self._start_live_loop()

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_string(OMEN_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _add_actions(self) -> None:
        save = Gio.SimpleAction.new("save", None)
        save.connect("activate", lambda *_: self.save_profile_dialog())
        load = Gio.SimpleAction.new("load", None)
        load.connect("activate", lambda *_: self.load_profile_dialog())
        self.add_action(save)
        self.add_action(load)

    def _build_sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=10,
            margin_top=16, margin_bottom=16, margin_start=14, margin_end=14,
        )

        # ── Efectos (como Windows Light Studio) ──
        box.append(Gtk.Label(label="EFECTOS", css_classes=["omen-section"], xalign=0))
        for mode, name, desc in EFFECT_CATALOG:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, css_classes=["effect-card"])
            card.append(Gtk.Label(label=name, css_classes=["effect-name"], xalign=0))
            card.append(Gtk.Label(label=desc, css_classes=["effect-desc"], xalign=0))
            card.set_cursor(Gdk.Cursor.new_from_name("pointer"))
            click = Gtk.GestureClick.new()
            click.connect("released", lambda _g, _n, _x, _y, m=mode: self._select_effect(m))
            card.add_controller(click)
            self._effect_cards[mode] = card
            box.append(card)

        # ── Color ──
        box.append(Gtk.Label(label="COLOR", css_classes=["omen-section"], xalign=0))
        sw_row = Gtk.FlowBox(homogeneous=True, max_children_per_line=5, selection_mode=Gtk.SelectionMode.NONE)
        for i, preset in enumerate(PRESETS):
            btn = Gtk.Button(css_classes=["color-swatch"])
            btn.set_size_request(36, 36)
            prov = Gtk.CssProvider()
            prov.load_from_string(f".color-swatch {{ background: {preset}; }}")
            btn.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            btn.connect("clicked", self._on_preset, preset, i)
            sw_row.append(btn)
            self._swatch_btns.append(btn)
        box.append(sw_row)

        pick = Gtk.Button(label="Selector de color personalizado")
        pick.add_css_class("suggested-action")
        pick.connect("clicked", self._pick_color)
        box.append(pick)

        # ── Sliders ──
        box.append(Gtk.Label(label="BRILLO", css_classes=["omen-section"], xalign=0))
        self.brightness_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment.new(100, 0, 100, 1, 5, 0),
            draw_value=True,
            value_pos=Gtk.PositionType.RIGHT,
        )
        self.brightness_scale.connect("value-changed", self._on_brightness)
        box.append(self.brightness_scale)

        box.append(Gtk.Label(label="VELOCIDAD", css_classes=["omen-section"], xalign=0))
        self.speed_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment.new(50, 1, 100, 1, 5, 0),
            draw_value=True,
            value_pos=Gtk.PositionType.RIGHT,
        )
        self.speed_scale.connect("value-changed", self._on_speed)
        box.append(self.speed_scale)

        # ── Modo pintura ──
        box.append(Gtk.Label(label="EDICIÓN", css_classes=["omen-section"], xalign=0))
        mode_grp = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_key_mode = Gtk.ToggleButton(label="Por tecla", active=True)
        self.btn_zone_mode = Gtk.ToggleButton(label="Por zona")
        self.btn_zone_mode.set_group(self.btn_key_mode)
        self.btn_key_mode.connect("toggled", self._on_paint_mode)
        mode_grp.append(self.btn_key_mode)
        mode_grp.append(self.btn_zone_mode)
        box.append(mode_grp)

        pwr = Adw.SwitchRow(title="Iluminación encendida", active=True)
        pwr.connect("notify::active", self._on_power)
        box.append(pwr)
        self.power_row = pwr

        dir_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_ltr = Gtk.ToggleButton(label="→ Izda a dcha", active=True)
        self.btn_rtl = Gtk.ToggleButton(label="← Dcha a izda")
        self.btn_rtl.set_group(self.btn_ltr)
        self.btn_ltr.connect("toggled", self._on_direction)
        dir_row.append(self.btn_ltr)
        dir_row.append(self.btn_rtl)
        box.append(dir_row)

        return box

    def _select_effect(self, mode: str) -> None:
        self._active_effect = mode
        self.fx.mode = mode
        for m, card in self._effect_cards.items():
            if m == mode:
                card.add_css_class("active")
            else:
                card.remove_css_class("active")
        self._dirty_hw = True
        if self.canvas:
            self.canvas.queue_draw()

    def switch_to_static_for_paint(self) -> None:
        if self.fx.mode != "static":
            self._select_effect("static")

    def _on_paint_mode(self, btn) -> None:
        self.paint_mode = "key" if btn.get_active() else "zone"

    def _on_power(self, row, _pspec) -> None:
        self.fx.power = row.get_active()
        self._dirty_hw = True

    def _on_brightness(self, scale) -> None:
        self.fx.brightness = int(scale.get_value())
        self._dirty_hw = True

    def _on_speed(self, scale) -> None:
        self.fx.speed = int(scale.get_value())
        self._dirty_hw = True

    def _on_direction(self, btn) -> None:
        self.fx.direction = "ltr" if btn.get_active() else "rtl"
        self._dirty_hw = True

    def _on_preset(self, btn, preset: str, index: int) -> None:
        self.brush = hex_to_rgb(preset)
        self.fx.primary = self.brush
        for i, b in enumerate(self._swatch_btns):
            if i == index:
                b.add_css_class("active")
            else:
                b.remove_css_class("active")

    def _pick_color(self, _btn) -> None:
        dialog = Gtk.ColorDialog(title="Color")
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue = [c / 255 for c in self.brush]
        rgba.alpha = 1.0
        dialog.choose_rgba(self.win, rgba, None, self._color_chosen)

    def _color_chosen(self, dialog, result) -> None:
        try:
            rgba = dialog.choose_rgba_finish(result)
            self.brush = (int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255))
            self.fx.primary = self.brush
            for b in self._swatch_btns:
                b.remove_css_class("active")
        except GLib.Error:
            pass

    def paint_key(self, key_id: str, live: bool = True) -> None:
        self.key_colors[key_id] = self.brush
        self.display_colors[key_id] = self.brush
        if live:
            self._dirty_hw = True
            self._push_hardware_immediate()

    def paint_zone(self, zone: int, live: bool = True) -> None:
        self._zone_direct[zone] = self.brush
        for key in KEYS:
            if key.zone == zone:
                self.key_colors[key.id] = self.brush
                self.display_colors[key.id] = self.brush
        if live:
            self._dirty_hw = True
            self._push_hardware_immediate()

    def _push_hardware_immediate(self) -> None:
        if not self.backend.available or not self.fx.power:
            if not self.fx.power:
                self.backend.set_power(False)
            return
        bri = self.fx.brightness / 100.0
        if is_animated(self.fx.mode):
            return  # el loop en vivo lo maneja
        self.backend.apply_key_map(self.display_colors, KEY_ZONES, bri, True)
        self._dirty_hw = False

    def _start_live_loop(self) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
        self._tick_id = GLib.timeout_add(FPS_MS, self._live_tick)

    def _live_tick(self) -> bool:
        t = time.time()
        animated = is_animated(self.fx.mode)

        for i, key in enumerate(KEYS):
            static = self.key_colors.get(key.id, (20, 20, 28))
            self.display_colors[key.id] = compute_effect_color(
                self.fx, t, key.id, i, key.zone, static, KEYS_META,
            )

        if self.canvas:
            self.canvas.queue_draw()

        if self.backend.available and self.fx.power and (animated or self._dirty_hw):
            bri = self.fx.brightness / 100.0
            self.backend.apply_key_map(self.display_colors, KEY_ZONES, bri, True)
            self._dirty_hw = False
            if self.live_label:
                self.live_label.set_label("● EN VIVO")
        elif not self.fx.power and self.backend.available:
            self.backend.set_power(False)
            if self.live_label:
                self.live_label.set_label("○ APAGADO")

        return True  # keep timer

    def save_profile_dialog(self) -> None:
        PROFILES_DIR.mkdir(exist_ok=True)
        dialog = Gtk.FileDialog(title="Guardar perfil", initial_folder=Gio.File.new_for_path(str(PROFILES_DIR)))
        dialog.save(self.win, None, self._save_profile)

    def _save_profile(self, dialog, result) -> None:
        try:
            f = dialog.save_finish(result)
            data = {
                "key_colors": {k: list(v) for k, v in self.key_colors.items()},
                "effect": self.fx.mode,
                "brightness": self.fx.brightness,
                "speed": self.fx.speed,
                "primary": list(self.fx.primary),
            }
            Path(f.get_path()).write_text(json.dumps(data, indent=2))
        except GLib.Error:
            pass

    def load_profile_dialog(self) -> None:
        PROFILES_DIR.mkdir(exist_ok=True)
        dialog = Gtk.FileDialog(title="Cargar perfil", initial_folder=Gio.File.new_for_path(str(PROFILES_DIR)))
        dialog.open(self.win, None, self._load_profile)

    def _load_profile(self, dialog, result) -> None:
        try:
            f = dialog.open_finish(result)
            data = json.loads(Path(f.get_path()).read_text())
            self.key_colors = {k: tuple(v) for k, v in data.get("key_colors", {}).items()}
            self.display_colors = dict(self.key_colors)
            self.fx.brightness = data.get("brightness", 100)
            self.fx.speed = data.get("speed", 50)
            self.fx.primary = tuple(data.get("primary", [255, 54, 87]))
            self.brush = self.fx.primary
            if self.brightness_scale:
                self.brightness_scale.set_value(self.fx.brightness)
            if self.speed_scale:
                self.speed_scale.set_value(self.fx.speed)
            self._select_effect(data.get("effect", "static"))
            self._dirty_hw = True
        except (GLib.Error, json.JSONDecodeError, OSError):
            pass


def main() -> int:
    Adw.init()
    return OmenLightStudio().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
