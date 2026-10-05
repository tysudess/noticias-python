#!/usr/bin/env bash
set -u

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LOG="$HERE/logs/diagnostico-portable.txt"

mkdir -p "$HERE/logs"

exec > >(tee "$LOG") 2>&1

echo "============================================================"
echo "Central Inteligente de Mídia — Diagnóstico Ubuntu Portable"
echo "Data: $(date -Is 2>/dev/null || date)"
echo "Diretório: $HERE"
echo "============================================================"
echo

fail=0

check_exec() {
  local path="$1"
  local label="$2"

  if [ ! -f "$path" ]; then
    echo "[ERRO] $label ausente: $path"
    fail=1
    return
  fi

  if [ ! -x "$path" ]; then
    echo "[ERRO] $label sem permissão de execução: $path"
    fail=1
    return
  fi

  echo "[OK] $label"
}

check_exec \
  "$HERE/CentralInteligenteDeMidia" \
  "Central"

check_exec \
  "$HERE/bin/ffmpeg" \
  "FFmpeg"

check_exec \
  "$HERE/bin/ffprobe" \
  "FFprobe"

check_exec \
  "$HERE/bin/yt-dlp" \
  "yt-dlp"

check_exec \
  "$HERE/bin/deno" \
  "Deno"

check_exec \
  "$HERE/resources/globoplay-login-helper/GloboplayLoginHelper" \
  "Helper Globoplay"

check_exec \
  "$HERE/tools/news_extractor/ExtratorMateriasPortable-V1.25.19" \
  "Extrator de Matérias"

echo
echo "Sistema:"
uname -a || true

if [ -f /etc/os-release ]; then
  cat /etc/os-release
fi

echo
echo "Sessão gráfica:"
echo "DISPLAY=${DISPLAY:-}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-}"
echo "XAUTHORITY=${XAUTHORITY:-}"

if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  echo "[AVISO] Sessão Wayland: o backend V101 usa QScreen/Qt em Ubuntu on Xorg."
fi

echo
echo "Dependências do executável principal:"
if command -v ldd >/dev/null 2>&1; then
  ldd "$HERE/CentralInteligenteDeMidia" || true

  if ldd "$HERE/CentralInteligenteDeMidia" 2>/dev/null |
     grep -q "not found"; then
    echo
    echo "[ERRO] Há bibliotecas do sistema não encontradas."
    fail=1
  fi
else
  echo "ldd não disponível."
fi

echo
echo "Versões dos binários:"

"$HERE/bin/ffmpeg" -version 2>/dev/null | head -n 1 || true
"$HERE/bin/ffprobe" -version 2>/dev/null | head -n 1 || true
"$HERE/bin/yt-dlp" --version 2>/dev/null || true
"$HERE/bin/deno" --version 2>/dev/null | head -n 3 || true

echo
echo "FFmpeg / codificação do Gravador:"
if [ -x "$HERE/bin/ffmpeg" ]; then
  FFMPEG_ENCODERS="$($HERE/bin/ffmpeg -hide_banner -encoders 2>&1 || true)"

  if printf '%s\n' "$FFMPEG_ENCODERS" | grep -qi "libx264"; then
    echo "[OK] FFmpeg possui libx264"
  else
    echo "[ERRO] FFmpeg do portable não possui libx264"
    fail=1
  fi

  echo "[INFO] V101: a tela é capturada pelo Qt/X11 e enviada ao FFmpeg por rawvideo pipe."
  echo "[INFO] O FFmpeg não precisa mais abrir o DISPLAY via x11grab."
fi

echo
echo "Áudio:"
if command -v pactl >/dev/null 2>&1; then
  echo "[OK] pactl disponível"
  pactl info 2>/dev/null | head -n 20 || true
else
  echo "[AVISO] pactl não encontrado. O Gravador poderá funcionar sem áudio."
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "DIAGNÓSTICO: OK"
  echo "Agora execute: ./INICIAR-CENTRAL.sh"
  exit 0
fi

echo "DIAGNÓSTICO: foram encontrados problemas."
echo "Envie este arquivo para análise:"
echo "$LOG"
exit 1
