install_app() {
  local src="$1"
  local dest="/usr/share/omen-light-studio"
  install -d "$dest/profiles"
  for f in effects.py hp_rgb.py keyboard_layout.py omen_light_studio.py; do
    install -m 644 "$src/$f" "$dest/"
  done
  install -m 755 "$src/bin/omen-light-studio" /usr/local/bin/omen-light-studio
  install -d /usr/share/applications
  cat > /usr/share/applications/omen-light-studio.desktop <<'DESK'
[Desktop Entry]
Name=OMEN Light Studio
Comment=HP Omen keyboard RGB control for Linux
Exec=omen-light-studio
Icon=preferences-desktop-keyboard
Terminal=false
Type=Application
Categories=Settings;Utility;
DESK
}
