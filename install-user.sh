#!/usr/bin/env bash
# Instala la app en ~/.local (sin root). El driver requiere install.sh con sudo.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${HOME}/.local/share/omen-light-studio"
BIN="${HOME}/.local/bin/omen-light-studio"

mkdir -p "$DEST/profiles" "${HOME}/.local/bin"
install -m 644 "$ROOT"/{effects,hp_rgb,keyboard_layout,omen_light_studio}.py "$DEST/"
install -m 755 "$ROOT/bin/omen-light-studio" "$BIN"

echo "Instalado en $DEST"
echo "Ejecuta: omen-light-studio   (asegúrate de que ~/.local/bin está en PATH)"
