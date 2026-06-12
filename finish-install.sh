#!/usr/bin/env bash
# Termina instalación si install.sh se interrumpió (p. ej. en dracut)
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "sudo bash $0"
  exit 1
fi

echo "[1] Cargar módulo hp-rgb-lighting..."
modprobe led_class_multicolor 2>/dev/null || true
modprobe hp-rgb-lighting 2>/dev/null || modprobe hp_rgb_lighting 2>/dev/null || {
  echo "Error cargando módulo. Prueba: dmesg | tail -20"
  exit 1
}
echo "hp-rgb-lighting" > /etc/modules-load.d/hp-rgb-lighting.conf

echo "[2] Regla udev..."
cat > /etc/udev/rules.d/99-hp-rgb-lighting.rules <<'UDEV'
SUBSYSTEM=="platform", KERNEL=="hp-rgb-lighting", MODE="0666"
UDEV
udevadm control --reload-rules
udevadm trigger --subsystem-match=platform

echo "[3] Instalar app..."
# shellcheck source=scripts/install-app.sh
source "$APP_DIR/scripts/install-app.sh"
install_app "$APP_DIR"

if [[ -d /sys/devices/platform/hp-rgb-lighting ]]; then
  echo "OK — driver activo. Ejecuta: omen-light-studio"
  ls /sys/devices/platform/hp-rgb-lighting/
else
  echo "Módulo cargado pero sysfs ausente. Reinicia el portátil."
fi
