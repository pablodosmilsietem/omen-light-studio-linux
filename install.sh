#!/usr/bin/env bash
# Instala Omen Light Studio + driver hp-rgb-lighting + permisos udev
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

if [[ $EUID -ne 0 ]]; then
  echo -e "${RED}Ejecuta con sudo:${NC} sudo bash $0"
  exit 1
fi

echo -e "${GREEN}=== Omen Light Studio — instalación ===${NC}"

echo -e "${YELLOW}[1/5]${NC} Dependencias..."
dnf install -y dkms kernel-devel kernel-headers gcc make git \
  python3 python3-gobject python3-cairo gtk4 libadwaita

echo -e "${YELLOW}[2/5]${NC} Driver hp-rgb-lighting (DKMS)..."
TMP=$(mktemp -d)
git clone --depth 1 https://github.com/yunusemreyl/OmenCtl.git "$TMP/OmenCtl"
cd "$TMP/OmenCtl/driver"
export FORCE_RGB_ONLY=true
./setup.sh install

echo -e "${YELLOW}[3/5]${NC} Permisos udev (escritura sin sudo)..."
cat > /etc/udev/rules.d/99-hp-rgb-lighting.rules <<'UDEV'
# Permite control RGB HP Omen a usuarios locales
SUBSYSTEM=="platform", KERNEL=="hp-rgb-lighting", MODE="0666"
UDEV
udevadm control --reload-rules
udevadm trigger --subsystem-match=platform

echo -e "${YELLOW}[4/5]${NC} Instalar aplicación..."
# shellcheck source=scripts/install-app.sh
source "$APP_DIR/scripts/install-app.sh"
install_app "$APP_DIR"

echo -e "${YELLOW}[5/5]${NC} Cargar módulo..."
modprobe led_class_multicolor 2>/dev/null || true
modprobe hp-rgb-lighting 2>/dev/null || modprobe hp_rgb_lighting 2>/dev/null || true
echo "hp-rgb-lighting" > /etc/modules-load.d/hp-rgb-lighting.conf

rm -rf "$TMP"

if [[ -d /sys/devices/platform/hp-rgb-lighting ]]; then
  echo -e "${GREEN}Listo.${NC} Abre la app con: omen-light-studio"
  echo "Prueba: echo FF0000 > /sys/devices/platform/hp-rgb-lighting/zone0"
else
  echo -e "${YELLOW}Driver instalado pero no cargado.${NC} Reinicia o ejecuta:"
  echo "  sudo modprobe hp-rgb-lighting"
  echo "  dmesg | grep hp-rgb"
fi
