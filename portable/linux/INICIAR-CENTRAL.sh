#!/usr/bin/env bash
set -u

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

cd "$HERE" || exit 1

mkdir -p \
  "$HERE/data" \
  "$HERE/logs" \
  "$HERE/temp" \
  "$HERE/Videos" \
  "$HERE/VideoEditorExports"

export PATH="$HERE/bin:$PATH"

LOG="$HERE/logs/inicializacao.log"

{
  echo
  echo "============================================================"
  echo "Central Inteligente de Mídia — Ubuntu Portable"
  echo "Início: $(date -Is 2>/dev/null || date)"
  echo "Diretório: $HERE"
  echo "DISPLAY=${DISPLAY:-}"
  echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
  echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-}"
  echo "============================================================"
} >> "$LOG"

exec \
  "$HERE/CentralInteligenteDeMidia" \
  "$@" \
  >> "$LOG" \
  2>&1
