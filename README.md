# OMEN Light Studio for Linux

Open-source RGB keyboard control for **HP OMEN** and **Victus** laptops on Linux — inspired by HP OMEN Light Studio on Windows.

Paint keys in real time, pick from 10 lighting effects, adjust brightness and speed. Changes apply instantly to the physical keyboard.

> **Not affiliated with HP.** Community project using the [`hp-rgb-lighting`](https://github.com/yunusemreyl/OmenCtl) kernel driver.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

## Features

- **Real-time control** — no Apply button; every click, drag, or slider change goes live (~30 FPS)
- **Per-key painting** — click or drag on the visual keyboard
- **Zone mode** — paint an entire hardware zone at once
- **10 effects**: Static, Breathing, Color Cycle, Rainbow, Rainbow Wave, Color Wave, Spectrum, Ripple, Aurora, Fire
- **Brightness & speed** sliders, direction toggle for waves
- **Profiles** — save/load JSON lighting profiles
- **Dark OMEN-style UI** (GTK4 + Libadwaita)

## Hardware support

Works with HP laptops that expose keyboard RGB via WMI through the **`hp-rgb-lighting`** kernel module (8 zones).

Tested conceptually on **HP OMEN MAX 16** class machines. Your mileage may vary depending on keyboard type (4-zone vs per-key hardware — the app maps per-key colors to zones automatically).

### Requirements

- Linux (Fedora, Ubuntu, Arch, etc.)
- Python 3.10+
- GTK4, Libadwaita, PyGObject, pycairo
- `hp-rgb-lighting` DKMS module (installed automatically by our script)

## Quick start

### 1. Clone

```bash
git clone https://github.com/pablodosmilsietem/omen-light-studio-linux.git
cd omen-light-studio-linux
```

### 2. Install driver + app

```bash
sudo bash install.sh
```

If the install was interrupted (e.g. during `dracut`), finish with:

```bash
sudo bash finish-install.sh
```

### 3. Run

```bash
omen-light-studio
```

Or without system install:

```bash
python3 omen_light_studio.py
```

## Manual driver check

```bash
# Module loaded?
ls /sys/devices/platform/hp-rgb-lighting/

# Load manually if needed
sudo modprobe hp-rgb-lighting

# Quick test (zone 0 = red)
echo FF0000 | sudo tee /sys/devices/platform/hp-rgb-lighting/zone0
```

## How it works

HP firmware exposes keyboard RGB through WMI. The [`hp-rgb-lighting`](https://github.com/yunusemreyl/OmenCtl/tree/main/driver) driver creates sysfs files `zone0`–`zone7`.

This app:

1. Renders a full keyboard layout in GTK4
2. Computes colors per key (static paint or animated effects)
3. Averages key colors per hardware zone
4. Writes hex colors to sysfs in real time

Per-key painting on screen is **visual**; the physical keyboard receives **zone** colors. This is a Linux/WMI limitation, not a bug in this app.

## Project structure

```
omen-light-studio/
├── omen_light_studio.py   # GTK4 application
├── effects.py             # Animation engine
├── hp_rgb.py              # sysfs backend
├── keyboard_layout.py     # Key positions & zones
├── bin/omen-light-studio  # Launcher (sets install path)
├── install.sh             # Full install (driver + app)
├── finish-install.sh      # Finish interrupted install
└── profiles/              # Saved lighting profiles (local)
```

## Uninstall

```bash
sudo rm -rf /usr/share/omen-light-studio
sudo rm -f /usr/local/bin/omen-light-studio
sudo rm -f /usr/share/applications/omen-light-studio.desktop
sudo rm -f /etc/udev/rules.d/99-hp-rgb-lighting.rules
sudo dkms remove hp-rgb-lighting/1.5.3 --all  # version may differ
sudo rm -f /etc/modules-load.d/hp-rgb-lighting.conf
```

## Credits

- Kernel driver based on [OmenCtl / hp-rgb-lighting](https://github.com/yunusemreyl/OmenCtl) by yunusemreyl and contributors
- Original `hp-wmi` work by Matthew Garrett, TUXOV, and the Linux platform drivers community

## License

MIT — see [LICENSE](LICENSE).

---

## Español

Control RGB del teclado HP Omen en Linux, en **tiempo real**, similar a OMEN Light Studio en Windows.

```bash
git clone https://github.com/pablodosmilsietem/omen-light-studio-linux.git
cd omen-light-studio-linux
sudo bash install.sh
omen-light-studio
```

Pinta teclas con clic o arrastre, elige efectos en el panel izquierdo, ajusta brillo y velocidad. Todo se aplica al instante.

**Limitación:** el hardware HP usa 8 zonas; pintar tecla a tecla en pantalla se traduce a zonas en el teclado físico.
