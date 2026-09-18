import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QThread, QTimer, QUrl, Signal, QSize
from PySide6.QtGui import QPainter, QPen, QPixmap, QFontMetrics, QShortcut, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from .range_slider import RangeSlider


AUDIO_BITRATE_BPS = 128_000


def format_ms(ms):
    ms = max(0, int(round(ms)))
    total_sec, millis = divmod(ms, 1000)
    h, rem = divmod(total_sec, 3600)
    m, sec = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{sec:02d}.{millis:03d}'


def format_short(ms):
    ms = max(0, int(ms))
    total_sec = ms // 1000
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'


def parse_time(text):
    value = (text or '').strip().replace(',', '.')
    if not value:
        raise ValueError('Informe um tempo. Ex.: 00:00:12.350')
    parts = value.split(':')
    if len(parts) not in (2, 3):
        raise ValueError('Use MM:SS.mmm ou HH:MM:SS.mmm')
    try:
        if len(parts) == 2:
            h = 0
            m = int(parts[0])
            sec = float(parts[1])
        else:
            h = int(parts[0])
            m = int(parts[1])
            sec = float(parts[2])
    except Exception as exc:
        raise ValueError('Tempo inválido. Use HH:MM:SS.mmm') from exc
    if h < 0 or m < 0 or sec < 0 or m >= 60 or sec >= 60:
        raise ValueError('Tempo inválido. Use HH:MM:SS.mmm')
    return max(0, int(round((h * 3600 + m * 60 + sec) * 1000)))


def _seconds_from_ffmpeg_time(value):
    try:
        h, m, s = value.strip().split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0.0


def _safe_output_name(text, default='video_final.mp4'):
    name = (text or '').strip() or default
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    if not name:
        name = default
    if not name.lower().endswith('.mp4'):
        name += '.mp4'
    return name[:180]


def _unique_output(folder, requested):
    output = Path(folder) / _safe_output_name(requested)
    if not output.exists():
        return output
    stem, suffix = output.stem, output.suffix
    for i in range(2, 1000):
        candidate = output.with_name(f'{stem}_{i}{suffix}')
        if not candidate.exists():
            return candidate
    return output.with_name(f'{stem}_novo{suffix}')


def _probe_media_info(path, ffprobe_exe, ffmpeg_exe):
    path = Path(path)
    info = {'duration_ms': 0, 'width': 0, 'height': 0, 'fps': 30.0, 'has_audio': False}
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    if Path(ffprobe_exe).exists():
        try:
            cmd = [
                str(ffprobe_exe), '-v', 'error', '-show_entries',
                'format=duration:stream=codec_type,width,height,r_frame_rate',
                '-of', 'json', str(path),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=flags,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                try:
                    info['duration_ms'] = max(0, int(round(float(data.get('format', {}).get('duration', 0)) * 1000)))
                except Exception:
                    pass
                for stream in data.get('streams', []) or []:
                    if stream.get('codec_type') == 'video' and not info['width']:
                        info['width'] = int(stream.get('width') or 0)
                        info['height'] = int(stream.get('height') or 0)
                        rate = str(stream.get('r_frame_rate') or '')
                        try:
                            if '/' in rate:
                                a, b = rate.split('/', 1)
                                fps = float(a) / float(b) if float(b) else 0.0
                            else:
                                fps = float(rate)
                            if 1 <= fps <= 120:
                                info['fps'] = fps
                        except Exception:
                            pass
                    elif stream.get('codec_type') == 'audio':
                        info['has_audio'] = True
                if info['duration_ms'] > 0:
                    return info
        except Exception:
            pass

    try:
        proc = subprocess.run(
            [str(ffmpeg_exe), '-hide_banner', '-i', str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding='utf-8', errors='replace', creationflags=flags,
        )
        text = proc.stdout or ''
        md = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', text, re.I)
        if md:
            sec = int(md.group(1)) * 3600 + int(md.group(2)) * 60 + float(md.group(3))
            info['duration_ms'] = int(round(sec * 1000))
        mv = re.search(r'Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s*fps', text, re.I | re.S)
        if not mv:
            mv = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', text, re.I | re.S)
        if mv:
            info['width'] = int(mv.group(1))
            info['height'] = int(mv.group(2))
            if len(mv.groups()) >= 3 and mv.group(3):
                try:
                    fps = float(mv.group(3))
                    if 1 <= fps <= 120:
                        info['fps'] = fps
                except Exception:
                    pass
        info['has_audio'] = bool(re.search(r'Audio:\s*', text, re.I))
    except Exception:
        pass
    return info


def _even(value):
    value = max(2, int(round(value)))
    return value - (value % 2)


def resolve_target_dimensions(first_info, resolution_choice):
    source_w = int((first_info or {}).get('width') or 1280)
    source_h = int((first_info or {}).get('height') or 720)
    if resolution_choice == 'Original':
        w, h = _even(source_w), _even(source_h)
        if w > 1920 or h > 1920:
            scale = min(1920 / w, 1920 / h)
            w, h = _even(w * scale), _even(h * scale)
        return w, h

    short_side = {'360p': 360, '480p': 480, '720p': 720, '1080p': 1080}.get(resolution_choice, 720)
    aspect = source_w / max(1.0, float(source_h))
    if source_w >= source_h:
        h = short_side
        w = _even(h * aspect)
    else:
        w = short_side
        h = _even(w / max(0.1, aspect))
    w, h = _even(w), _even(h)
    if w > 1920 or h > 1920:
        scale = min(1920 / w, 1920 / h)
        w, h = _even(w * scale), _even(h * scale)
    return w, h


def bitrate_profile(codec, resolution_choice, first_info=None):
    hevc = codec == 'H.265 / HEVC'
    if hevc:
        fixed = {
            '360p': (300_000, 650_000, 1_600_000),
            '480p': (450_000, 950_000, 2_400_000),
            '720p': (750_000, 1_800_000, 4_200_000),
            '1080p': (1_200_000, 3_200_000, 7_000_000),
        }
    else:
        fixed = {
            '360p': (450_000, 1_000_000, 2_500_000),
            '480p': (700_000, 1_600_000, 4_000_000),
            '720p': (1_200_000, 3_000_000, 7_000_000),
            '1080p': (2_000_000, 5_500_000, 12_000_000),
        }
    if resolution_choice in fixed:
        return fixed[resolution_choice]

    w, h = resolve_target_dimensions(first_info or {}, 'Original')
    long_side, short_side = max(w, h), min(w, h)
    if hevc:
        if short_side <= 480:
            return 450_000, 1_050_000, 2_500_000
        if short_side <= 720:
            return 750_000, 2_000_000, 4_800_000
        if short_side <= 1080 and long_side <= 1920:
            return 1_200_000, 3_500_000, 7_500_000
        return 1_800_000, 4_800_000, 10_000_000
    if short_side <= 480:
        return 700_000, 1_800_000, 4_000_000
    if short_side <= 720:
        return 1_200_000, 3_500_000, 8_000_000
    if short_side <= 1080 and long_side <= 1920:
        return 2_000_000, 6_000_000, 12_000_000
    return 3_000_000, 8_000_000, 16_000_000


def estimated_size_mb(duration_ms, video_bitrate, audio_bitrate=AUDIO_BITRATE_BPS):
    seconds = max(0.0, duration_ms / 1000.0)
    return (seconds * max(1, video_bitrate + audio_bitrate) / 8.0) / (1024.0 * 1024.0)


def bitrate_for_target_size(size_mb, duration_ms, codec, resolution_choice, first_info):
    seconds = max(0.25, duration_ms / 1000.0)
    usable_bits = max(1.0, float(size_mb)) * 1024.0 * 1024.0 * 8.0 * 0.97
    total_bitrate = round(usable_bits / seconds)
    video = int(max(250_000, min(20_000_000, total_bitrate - AUDIO_BITRATE_BPS)))
    lo, _, hi = bitrate_profile(codec, resolution_choice, first_info)
    return max(lo, min(hi, video))


def _ffmpeg_has_encoder(ffmpeg_exe, encoder_name):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc = subprocess.run(
            [str(ffmpeg_exe), '-hide_banner', '-encoders'],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            creationflags=flags,
        )
        return encoder_name.lower() in ((proc.stdout or '') + (proc.stderr or '')).lower()
    except Exception:
        return False


class ThumbnailWorker(QThread):
    ready = Signal(str, object)

    def __init__(self, key, path, start_ms, end_ms, ffmpeg_exe, parent=None):
        super().__init__(parent)
        self.key = key
        self.path = str(path)
        self.start_ms = int(start_ms)
        self.end_ms = int(end_ms)
        self.ffmpeg_exe = Path(ffmpeg_exe)

    def run(self):
        if not self.ffmpeg_exe.exists():
            self.ready.emit(self.key, [])
            return
        duration = max(1, self.end_ms - self.start_ms)
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        frames = []
        count = 6
        for i in range(count):
            pos_ms = self.start_ms + int((duration - 1) * (i / max(1, count - 1)))
            cmd = [
                str(self.ffmpeg_exe), '-hide_banner', '-loglevel', 'error', '-ss', f'{pos_ms / 1000.0:.3f}',
                '-i', self.path, '-frames:v', '1',
                '-vf', 'scale=180:102:force_original_aspect_ratio=increase,crop=180:102',
                '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1',
            ]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=flags, timeout=20)
                if proc.returncode == 0 and proc.stdout:
                    frames.append(bytes(proc.stdout))
            except Exception:
                pass
        self.ready.emit(self.key, frames)


class TimelineWidget(QWidget):
    clipSelected = Signal(int)
    playheadMoved = Signal(int, bool)
    reorderRequested = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clips = []
        self.selected_index = -1
        self.playhead_ms = 0
        self.pixels_per_second = 4.8
        self.left_padding = 16
        self.ruler_h = 30
        self.clip_top = 38
        self.clip_h = 92
        self.min_clip_w = 100
        self.thumb_cache = {}
        self.dragging_playhead = False
        self.drag_source_index = -1
        self.drag_target_index = -1
        self.drag_reordering = False
        self.drag_press_x = 0.0
        self.drag_press_y = 0.0
        self.setToolTip('Clique para posicionar o cursor. Clique e arraste qualquer parte do vídeo para mudar sua posição na timeline.')
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(146)
        self.setMouseTracking(True)
        self._update_width()

    def sizeHint(self):
        return QSize(self._timeline_width(), 146)

    def set_pixels_per_second(self, value):
        self.pixels_per_second = max(0.8, float(value))
        self._update_width()
        self.update()

    def set_clips(self, clips, selected_index=-1):
        self.clips = [dict(c) for c in clips]
        self.selected_index = int(selected_index)
        self.playhead_ms = min(self.playhead_ms, self.total_duration_ms())
        self._update_width()
        self.update()

    def set_selected_index(self, index):
        self.selected_index = int(index)
        self.update()

    def set_playhead_ms(self, value):
        self.playhead_ms = max(0, min(int(value), self.total_duration_ms()))
        self.update()

    def set_thumbnails(self, key, frame_bytes):
        pix = []
        for data in frame_bytes or []:
            p = QPixmap()
            if p.loadFromData(data):
                pix.append(p)
        self.thumb_cache[key] = pix
        self.update()

    def _clip_key(self, clip):
        return f'{clip.get("path", "")}|{int(clip.get("start_ms", 0))}|{int(clip.get("end_ms", 0))}'

    def total_duration_ms(self):
        return sum(max(0, int(c.get('end_ms', 0)) - int(c.get('start_ms', 0))) for c in self.clips)

    def _clip_width(self, clip):
        duration = max(1, int(clip.get('end_ms', 0)) - int(clip.get('start_ms', 0)))
        return max(self.min_clip_w, (duration / 1000.0) * self.pixels_per_second)

    def _timeline_width(self):
        return int(self.left_padding * 2 + sum(self._clip_width(c) for c in self.clips) + 6)

    def _update_width(self):
        self.setMinimumWidth(max(320, self._timeline_width()))
        self.resize(max(320, self._timeline_width()), 146)
        self.updateGeometry()

    def _x_for_global(self, global_ms):
        global_ms = max(0, min(int(global_ms), self.total_duration_ms()))
        x = float(self.left_padding)
        accumulated = 0
        for clip in self.clips:
            duration = max(1, int(clip['end_ms']) - int(clip['start_ms']))
            width = self._clip_width(clip)
            if global_ms <= accumulated + duration:
                ratio = (global_ms - accumulated) / duration
                return x + width * max(0.0, min(1.0, ratio))
            x += width
            accumulated += duration
        return x

    def _global_for_x(self, x):
        if not self.clips:
            return 0
        cursor = float(self.left_padding)
        accumulated = 0
        for clip in self.clips:
            duration = max(1, int(clip['end_ms']) - int(clip['start_ms']))
            width = self._clip_width(clip)
            if x <= cursor + width:
                ratio = (x - cursor) / max(1.0, width)
                ratio = max(0.0, min(1.0, ratio))
                return accumulated + int(round(ratio * duration))
            cursor += width
            accumulated += duration
        return self.total_duration_ms()

    def _clip_index_for_x(self, x):
        if not self.clips:
            return -1
        cursor = float(self.left_padding)
        for idx, clip in enumerate(self.clips):
            width = self._clip_width(clip)
            if cursor <= x <= cursor + width:
                return idx
            cursor += width
        if x < self.left_padding:
            return 0
        return len(self.clips) - 1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        painter.fillRect(self.rect(), pal.base())

        total = self.total_duration_ms()
        if total <= 0:
            painter.setPen(pal.text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Adicione vídeos para montar a timeline')
            return

        pps = self.pixels_per_second
        if pps >= 14:
            step = 5_000
        elif pps >= 7:
            step = 10_000
        elif pps >= 3.5:
            step = 30_000
        else:
            step = 60_000
        painter.setPen(QPen(pal.mid().color(), 1))
        for t in range(0, total + step, step):
            if t > total:
                break
            x = self._x_for_global(t)
            painter.drawLine(int(x), 20, int(x), self.ruler_h)
            painter.drawText(int(x + 3), 16, format_short(t))

        x = float(self.left_padding)
        metrics = QFontMetrics(self.font())
        for idx, clip in enumerate(self.clips):
            width = self._clip_width(clip)
            rect = QRectF(x, self.clip_top, width, self.clip_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(pal.alternateBase())
            painter.drawRoundedRect(rect, 8, 8)

            frames = self.thumb_cache.get(self._clip_key(clip), [])
            if frames:
                tile_w = max(58.0, rect.width() / len(frames))
                tile_count = max(1, int(math.ceil(rect.width() / tile_w)))
                tile_w = rect.width() / tile_count
                for i in range(tile_count):
                    pix = frames[i % len(frames)]
                    target = QRectF(rect.left() + i * tile_w, rect.top(), tile_w + 1, rect.height())
                    painter.drawPixmap(target.toRect(), pix)

            label_h = 24
            label_rect = QRectF(rect.left(), rect.top(), rect.width(), label_h)
            painter.fillRect(label_rect, pal.window())
            title = Path(clip.get('path', '')).name
            title = metrics.elidedText(f'{idx + 1}. {title}', Qt.TextElideMode.ElideRight, max(20, int(rect.width() - 14)))
            painter.setPen(pal.text().color())
            painter.drawText(label_rect.adjusted(7, 0, -30, 0), Qt.AlignmentFlag.AlignVCenter, title)
            # Indicação visual: o clipe inteiro pode ser arrastado com o mouse.
            painter.setPen(pal.midlight().color())
            painter.drawText(label_rect.adjusted(rect.width() - 28, 0, -6, 0), Qt.AlignmentFlag.AlignCenter, '≡')

            if self.drag_reordering and idx == self.drag_target_index:
                target_pen = QPen(pal.highlight().color(), 4, Qt.PenStyle.DashLine)
                painter.setPen(target_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

            pen = QPen(pal.highlight().color() if idx == self.selected_index else pal.mid().color(), 3 if idx == self.selected_index else 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 8, 8)

            if idx > 0 and clip.get('cut_before'):
                painter.setPen(QPen(pal.highlight().color(), 2, Qt.PenStyle.DashLine))
                painter.drawLine(int(rect.left()), self.ruler_h, int(rect.left()), int(rect.bottom() + 8))
                painter.drawText(int(rect.left() - 7), 28, '✂')
            x += width

        px = self._x_for_global(self.playhead_ms)
        painter.setPen(QPen(pal.text().color(), 2))
        painter.drawLine(int(px), 20, int(px), int(self.clip_top + self.clip_h + 10))
        painter.setBrush(pal.text())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(px - 6, 16, 12, 10), 3, 3)

    def mousePressEvent(self, event):
        if not self.clips or event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        x = event.position().x()
        y = event.position().y()
        idx = self._clip_index_for_x(x)

        # Dentro da faixa dos clipes, qualquer ponto do vídeo vira uma área de
        # arraste. Um clique simples continua posicionando o cursor; só após
        # alguns pixels de movimento entramos no modo de reordenação.
        inside_clip_band = self.clip_top <= y <= self.clip_top + self.clip_h
        if inside_clip_band and idx >= 0:
            if idx != self.selected_index:
                self.selected_index = idx
                self.clipSelected.emit(idx)
            self.drag_source_index = idx
            self.drag_target_index = idx
            self.drag_press_x = x
            self.drag_press_y = y
            self.drag_reordering = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.drag_source_index = -1
            self.drag_target_index = -1
            self.drag_reordering = False
            self._move_playhead_from_x(x, False)
        event.accept()

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()

        if not (event.buttons() & Qt.MouseButton.LeftButton):
            if self.clips and self.clip_top <= y <= self.clip_top + self.clip_h:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            return

        if self.drag_source_index >= 0:
            dx = abs(x - self.drag_press_x)
            dy = abs(y - self.drag_press_y)
            if not self.drag_reordering and max(dx, dy) >= 8:
                self.drag_reordering = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

            if self.drag_reordering:
                target = self._clip_index_for_x(x)
                if target >= 0 and target != self.drag_target_index:
                    self.drag_target_index = target
                    self.update()
                event.accept()
                return

            # Ainda é apenas um clique potencial. Não mexemos no playhead antes
            # de saber se o usuário pretende arrastar o vídeo.
            event.accept()
            return

        self._move_playhead_from_x(x, False)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.clips:
            return

        x = event.position().x()
        source = self.drag_source_index
        target = self.drag_target_index
        was_reordering = self.drag_reordering

        self.drag_source_index = -1
        self.drag_target_index = -1
        self.drag_reordering = False
        self.unsetCursor()

        if was_reordering and source >= 0 and target >= 0:
            if source != target:
                self.reorderRequested.emit(source, target)
            else:
                self.selected_index = source
                self.clipSelected.emit(source)
            self.update()
            event.accept()
            return

        # Clique simples no vídeo: seleciona e posiciona o cursor normalmente.
        self._move_playhead_from_x(x, True)
        event.accept()

    def leaveEvent(self, event):
        if not self.drag_reordering:
            self.unsetCursor()
        super().leaveEvent(event)

    def _move_playhead_from_x(self, x, finished):
        self.playhead_ms = self._global_for_x(x)
        idx = self._clip_index_for_x(x)
        if idx >= 0 and idx != self.selected_index:
            self.selected_index = idx
            self.clipSelected.emit(idx)
        self.update()
        self.playheadMoved.emit(self.playhead_ms, bool(finished))


class SmartExportWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, clips, output_path, resolution_choice, codec_choice, target_size_enabled, target_size_mb, ffmpeg_exe, ffprobe_exe, parent=None):
        super().__init__(parent)
        self.clips = [dict(c) for c in clips]
        self.output_path = Path(output_path)
        self.resolution_choice = resolution_choice
        self.codec_choice = codec_choice
        self.target_size_enabled = bool(target_size_enabled)
        self.target_size_mb = int(target_size_mb)
        self.ffmpeg_exe = Path(ffmpeg_exe)
        self.ffprobe_exe = Path(ffprobe_exe)

    def _run_process(self, cmd, duration_sec, base_pct, span_pct):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        tail = []
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding='utf-8', errors='replace', bufsize=1, creationflags=flags,
        )
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if line:
                tail.append(line)
                tail = tail[-50:]
            seconds = None
            if line.startswith('out_time_us='):
                try:
                    seconds = float(line.split('=', 1)[1]) / 1_000_000.0
                except Exception:
                    pass
            elif line.startswith('out_time='):
                seconds = _seconds_from_ffmpeg_time(line.split('=', 1)[1])
            if seconds is not None and duration_sec > 0:
                frac = max(0.0, min(1.0, seconds / duration_sec))
                self.progress.emit(max(0, min(99, int(base_pct + frac * span_pct))))
        return proc.wait(), '\n'.join(tail[-50:])

    def run(self):
        if not self.ffmpeg_exe.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return
        if not self.clips:
            self.failed.emit('Adicione pelo menos um vídeo à timeline.')
            return

        for clip in self.clips:
            path = Path(clip.get('path', ''))
            if not path.exists():
                self.failed.emit(f'Arquivo não encontrado: {path}')
                return
            if int(clip.get('end_ms', 0)) <= int(clip.get('start_ms', 0)):
                self.failed.emit(f'Intervalo inválido: {path.name}')
                return

        first_info = dict(self.clips[0].get('info') or {})
        if not first_info.get('duration_ms'):
            first_info.update(_probe_media_info(self.clips[0]['path'], self.ffprobe_exe, self.ffmpeg_exe))
        target_w, target_h = resolve_target_dimensions(first_info, self.resolution_choice)
        fps = float(first_info.get('fps') or 30.0)
        if not (1 <= fps <= 60):
            fps = 30.0

        requested_codec = self.codec_choice
        codec = requested_codec
        encoder = 'libx265' if codec == 'H.265 / HEVC' else 'libx264'
        if encoder == 'libx265' and not _ffmpeg_has_encoder(self.ffmpeg_exe, 'libx265'):
            codec = 'H.264 / AVC'
            encoder = 'libx264'
            self.message.emit('HEVC não está disponível neste FFmpeg. Usando H.264 automaticamente.')

        total_duration_ms = sum(int(c['end_ms']) - int(c['start_ms']) for c in self.clips)
        if total_duration_ms <= 0:
            self.failed.emit('A duração total da timeline é inválida.')
            return

        profile = bitrate_profile(codec, self.resolution_choice, first_info)
        if self.target_size_enabled:
            video_bitrate = bitrate_for_target_size(
                self.target_size_mb, total_duration_ms, codec, self.resolution_choice, first_info
            )
        else:
            video_bitrate = profile[1]

        output = self.output_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)

        try:
            with tempfile.TemporaryDirectory(prefix='ExtratorVideos-timeline-') as temp_root:
                temp_dir = Path(temp_root)
                temp_files = []
                seg_span = 90.0 / max(1, len(self.clips))
                vf = (
                    f'scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,'
                    f'pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,'
                    f'setsar=1,fps={fps:.3f},format=yuv420p'
                )

                for idx, clip in enumerate(self.clips):
                    source = Path(clip['path'])
                    start_sec = int(clip['start_ms']) / 1000.0
                    duration_sec = (int(clip['end_ms']) - int(clip['start_ms'])) / 1000.0
                    info = dict(clip.get('info') or {})
                    if 'has_audio' not in info:
                        info.update(_probe_media_info(source, self.ffprobe_exe, self.ffmpeg_exe))
                    has_audio = bool(info.get('has_audio'))
                    temp_file = temp_dir / f'parte_{idx + 1:03d}.ts'
                    temp_files.append(temp_file)
                    self.message.emit(f'Renderizando clipe {idx + 1}/{len(self.clips)} — {source.name}')

                    cmd = [
                        str(self.ffmpeg_exe), '-y', '-hide_banner', '-loglevel', 'error', '-i', str(source)
                    ]
                    if not has_audio:
                        cmd += ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000']
                    cmd += [
                        '-ss', f'{start_sec:.3f}', '-t', f'{duration_sec:.3f}',
                        '-map', '0:v:0', '-map', '0:a:0' if has_audio else '1:a:0',
                        '-vf', vf,
                        '-c:v', encoder,
                    ]
                    if encoder == 'libx265':
                        cmd += ['-preset', 'fast', '-x265-params', 'log-level=error']
                    else:
                        cmd += ['-preset', 'fast']
                    cmd += [
                        '-b:v', str(video_bitrate),
                        '-maxrate', str(int(video_bitrate * 1.35)),
                        '-bufsize', str(int(video_bitrate * 2.5)),
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '2',
                        '-af', 'aresample=async=1:first_pts=0',
                        '-shortest', '-avoid_negative_ts', 'make_zero',
                        '-progress', 'pipe:1', '-nostats', '-f', 'mpegts', str(temp_file),
                    ]
                    code, tail = self._run_process(cmd, duration_sec, idx * seg_span, seg_span)
                    if code != 0 or not temp_file.exists() or temp_file.stat().st_size < 1024:
                        self.failed.emit(tail or f'Falha ao renderizar {source.name}.')
                        return

                concat_file = temp_dir / 'lista.txt'
                lines = []
                for item in temp_files:
                    safe = item.resolve().as_posix().replace("'", "\\'")
                    lines.append(f"file '{safe}'")
                concat_file.write_text('\n'.join(lines), encoding='utf-8')

                self.message.emit('Montando o arquivo final...')
                cmd = [
                    str(self.ffmpeg_exe), '-y', '-hide_banner', '-loglevel', 'error',
                    '-fflags', '+genpts', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                    '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy',
                ]
                if codec == 'H.265 / HEVC':
                    cmd += ['-tag:v', 'hvc1']
                cmd += [
                    '-bsf:a', 'aac_adtstoasc', '-movflags', '+faststart',
                    '-progress', 'pipe:1', '-nostats', str(output),
                ]
                code, tail = self._run_process(cmd, total_duration_ms / 1000.0, 90, 9)
                if code != 0 or not output.exists() or output.stat().st_size < 1024:
                    output.unlink(missing_ok=True)
                    self.failed.emit(tail or 'Falha ao montar o arquivo final.')
                    return

            self.progress.emit(100)
            actual_mb = output.stat().st_size / (1024.0 * 1024.0)
            self.done.emit({
                'path': str(output),
                'codec': codec,
                'requested_codec': requested_codec,
                'width': target_w,
                'height': target_h,
                'video_bitrate': video_bitrate,
                'target_size_enabled': self.target_size_enabled,
                'target_size_mb': self.target_size_mb,
                'actual_mb': actual_mb,
            })
        except Exception as exc:
            output.unlink(missing_ok=True)
            self.failed.emit(str(exc))


class AdvancedVideoEditorWidget(QWidget):
    """Editor de timeline portado da versão Android v1.9.10 para Windows."""

    ZOOM_LEVELS = [1.8, 2.8, 4.8, 8.0, 13.0, 20.0]

    def __init__(self, videos_dir, ffmpeg_exe, ffprobe_exe, parent=None):
        super().__init__(parent)
        self.videos_dir = Path(videos_dir)
        self.ffmpeg_exe = Path(ffmpeg_exe)
        self.ffprobe_exe = Path(ffprobe_exe)
        self.clips = []
        self.selected_index = -1
        self.global_playhead_ms = 0
        self.preview_clip_index = -1
        self.preview_clip_end_source_ms = 0
        self.sequence_playing = False
        self._pending_seek_ms = None
        self._pending_autoplay = False
        self.export_worker = None
        self.zoom_index = 2
        self._changing_range = False
        self._thumbnail_queue = []
        self._thumbnail_keys_queued = set()
        self._thumbnail_worker = None
        self._hevc_available = None
        self.target_min_mb = 1
        self.target_max_mb = 100
        self.target_mb = 30

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.monitor = QTimer(self)
        self.monitor.setInterval(55)
        self.monitor.timeout.connect(self._monitor_playback)

        self._build_ui()
        self._connect_player()
        self._refresh_timeline(False)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(12)

        card_css = (
            'background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0a1020, stop:1 #0d1528);'
            'border:1px solid #233152; border-radius:16px;'
        )
        ghost_css = (
            'QPushButton {background:#0d1528; border:1px solid #273758; color:#dce6ff; '
            'border-radius:10px; padding:9px 14px; font-weight:650;} '
            'QPushButton:hover {background:#15203a; border-color:#455b8a;}'
        )
        primary_css = (
            'QPushButton {background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7b2ff7, stop:1 #2b69ff); '
            'border:1px solid #8b63ff; color:white; border-radius:10px; padding:10px 16px; font-weight:750;} '
            'QPushButton:hover {background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8d45ff, stop:1 #3c7bff);}'
        )
        danger_css = (
            'QPushButton {background:#35131f; border:1px solid #8d2945; color:#ffb4c5; '
            'border-radius:10px; padding:9px 14px; font-weight:700;} '
            'QPushButton:hover {background:#4b192a;}'
        )
        field_css = (
            'QLineEdit {background:#090f1c; border:1px solid #2a3a5f; border-radius:9px; '
            'padding:8px 10px; color:#f2f6ff; font-family:Consolas; font-size:10.5pt;} '
            'QLineEdit:focus {border:1px solid #715cff;}'
        )

        # Cabeçalho compacto no estilo da referência aprovada.
        header = QWidget(); header.setStyleSheet(card_css)
        hh = QHBoxLayout(header); hh.setContentsMargins(16, 12, 16, 12); hh.setSpacing(10)
        title_stack = QVBoxLayout(); title_stack.setSpacing(2)
        title = QLabel('EDITOR DE VÍDEO')
        title.setStyleSheet('color:#ffffff; font-size:15pt; font-weight:800; background:transparent; border:none;')
        self.selected_label = QLabel('Nenhum vídeo selecionado')
        self.selected_label.setStyleSheet('color:#a9b5cf; font-size:10pt; background:transparent; border:none;')
        self.selected_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        title_stack.addWidget(title); title_stack.addWidget(self.selected_label)
        hh.addLayout(title_stack, 1)
        self.btn_add = QPushButton('▣  Abrir vídeo')
        self.btn_add.setStyleSheet(ghost_css)
        self.btn_reset_visual = QPushButton('↻  Redefinir')
        self.btn_reset_visual.setStyleSheet(ghost_css)
        hh.addWidget(self.btn_add); hh.addWidget(self.btn_reset_visual)
        root.addWidget(header)

        # Preview grande + marcação rápida à direita.
        top = QHBoxLayout(); top.setSpacing(12)
        preview_card = QWidget(); preview_card.setStyleSheet(card_css)
        pv = QVBoxLayout(preview_card); pv.setContentsMargins(12, 12, 12, 12); pv.setSpacing(8)
        self.video = QVideoWidget(); self.video.setMinimumHeight(300); self.video.setMaximumHeight(430)
        self.player.setVideoOutput(self.video)
        pv.addWidget(self.video, 1)
        controls = QHBoxLayout(); controls.setSpacing(7)
        self.btn_back5 = QPushButton('−5s'); self.btn_back5.setStyleSheet(ghost_css)
        self.btn_play = QPushButton('▶  Reproduzir'); self.btn_play.setStyleSheet(primary_css)
        self.btn_forward5 = QPushButton('+5s'); self.btn_forward5.setStyleSheet(ghost_css)
        self.seq_current = QLabel('00:00.000 / 00:00.000')
        self.seq_current.setStyleSheet('color:#bdc9e2; font-family:Consolas; background:transparent; border:none; padding-left:8px;')
        controls.addWidget(self.btn_back5); controls.addWidget(self.btn_play); controls.addWidget(self.btn_forward5)
        controls.addWidget(self.seq_current); controls.addStretch(1)
        pv.addLayout(controls)
        top.addWidget(preview_card, 7)

        quick = QWidget(); quick.setStyleSheet(card_css); quick.setMinimumWidth(280); quick.setMaximumWidth(360)
        ql = QVBoxLayout(quick); ql.setContentsMargins(14, 14, 14, 14); ql.setSpacing(10)
        qt = QLabel('Marcação rápida')
        qt.setStyleSheet('color:#ffffff; font-size:12pt; font-weight:750; background:transparent; border:none;')
        ql.addWidget(qt)
        mark_row = QHBoxLayout(); mark_row.setSpacing(8)
        self.btn_mark_start = QPushButton('Início aqui'); self.btn_mark_start.setStyleSheet(ghost_css)
        self.btn_mark_end = QPushButton('Fim aqui'); self.btn_mark_end.setStyleSheet(ghost_css)
        mark_row.addWidget(self.btn_mark_start); mark_row.addWidget(self.btn_mark_end)
        ql.addLayout(mark_row)

        self.start_edit = QLineEdit(); self.start_edit.setPlaceholderText('00:00:00.000'); self.start_edit.setStyleSheet(field_css)
        self.end_edit = QLineEdit(); self.end_edit.setPlaceholderText('00:00:00.000'); self.end_edit.setStyleSheet(field_css)
        self.duration_value = QLabel('00:00:00.000')
        self.duration_value.setStyleSheet('color:#f2f6ff; font-family:Consolas; background:#090f1c; border:1px solid #2a3a5f; border-radius:9px; padding:8px 10px;')
        for label_text, widget in [('Início:', self.start_edit), ('Fim:', self.end_edit), ('Duração:', self.duration_value)]:
            row = QHBoxLayout(); lab = QLabel(label_text); lab.setMinimumWidth(66)
            lab.setStyleSheet('color:#bac5dc; background:transparent; border:none;')
            row.addWidget(lab); row.addWidget(widget, 1); ql.addLayout(row)
        self.btn_apply = QPushButton('✓  Aplicar tempos'); self.btn_apply.setStyleSheet(primary_css); ql.addWidget(self.btn_apply)
        self.info_label = QLabel('Selecione um clipe na timeline para ajustar o trecho.')
        self.info_label.setWordWrap(True); self.info_label.setStyleSheet('color:#8f9fbd; background:transparent; border:none; font-size:9.5pt;')
        ql.addWidget(self.info_label); ql.addStretch(1)
        top.addWidget(quick, 3)
        root.addLayout(top)

        # Timeline visual compacta.
        timeline_card = QWidget(); timeline_card.setStyleSheet(card_css)
        tl = QVBoxLayout(timeline_card); tl.setContentsMargins(12, 12, 12, 12); tl.setSpacing(8)
        timeline_head = QHBoxLayout(); timeline_head.setSpacing(8)
        label_tl = QLabel('TIMELINE  •  arraste o próprio vídeo com o mouse para reordenar')
        label_tl.setStyleSheet('color:#ffffff; font-weight:800; letter-spacing:1px; background:transparent; border:none;')
        self.clip_count = QLabel('0 clipes • 00:00')
        self.clip_count.setStyleSheet('color:#96a6c4; background:transparent; border:none;')
        self.local_position = QLabel('CURSOR  •  00:00.000')
        self.local_position.setStyleSheet('color:#67e8f9; background:#0b1e2d; border:1px solid #155e75; border-radius:8px; padding:4px 8px; font-family:Consolas; font-weight:700;')
        self.btn_zoom_out = QPushButton('−'); self.btn_zoom_out.setStyleSheet(ghost_css); self.btn_zoom_out.setFixedWidth(42)
        self.zoom_label = QLabel('Zoom 3/6')
        self.zoom_label.setStyleSheet('color:#72e4ff; background:transparent; border:none; font-weight:700;')
        self.btn_zoom_in = QPushButton('+'); self.btn_zoom_in.setStyleSheet(ghost_css); self.btn_zoom_in.setFixedWidth(42)
        timeline_head.addWidget(label_tl); timeline_head.addWidget(self.clip_count); timeline_head.addStretch(1)
        timeline_head.addWidget(self.local_position); timeline_head.addWidget(self.btn_zoom_out); timeline_head.addWidget(self.zoom_label); timeline_head.addWidget(self.btn_zoom_in)
        tl.addLayout(timeline_head)

        self.timeline_scroll = QScrollArea(); self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_scroll.setMinimumHeight(150); self.timeline_scroll.setMaximumHeight(190)
        self.timeline = TimelineWidget(); self.timeline.set_pixels_per_second(self.ZOOM_LEVELS[self.zoom_index])
        self.timeline_scroll.setWidget(self.timeline); tl.addWidget(self.timeline_scroll)

        # Range do clipe selecionado logo abaixo da timeline.
        self.range = RangeSlider(); self.range.setMinimumHeight(36); self.range.setMaximumHeight(46)
        tl.addWidget(self.range)

        precision = QHBoxLayout(); precision.setSpacing(7)
        self.nudge_buttons = []
        for delta, text in [(-1000, '−1s'), (-100, '−100ms'), (-10, '−10ms'), (10, '+10ms'), (100, '+100ms'), (1000, '+1s')]:
            b = QPushButton(text); b.setStyleSheet(ghost_css); b.setToolTip(f'Mover o cursor {text}')
            b.clicked.connect(lambda _=False, d=delta: self._nudge_local(d)); self.nudge_buttons.append(b); precision.addWidget(b)
        precision.addStretch(1)
        self.btn_cut = QPushButton('✂  Cortar'); self.btn_cut.setStyleSheet(primary_css)
        self.btn_remove = QPushButton('⌫  Excluir trecho'); self.btn_remove.setStyleSheet(danger_css)
        precision.addWidget(self.btn_cut); precision.addWidget(self.btn_remove)
        tl.addLayout(precision)

        manage = QHBoxLayout(); manage.setSpacing(7)
        self.btn_duplicate = QPushButton('⧉  Duplicar'); self.btn_duplicate.setStyleSheet(ghost_css)
        self.btn_up = QPushButton('←  Esquerda'); self.btn_up.setStyleSheet(ghost_css)
        self.btn_down = QPushButton('Direita  →'); self.btn_down.setStyleSheet(ghost_css)
        manage.addWidget(self.btn_duplicate); manage.addWidget(self.btn_up); manage.addWidget(self.btn_down); manage.addStretch(1)
        tl.addLayout(manage)
        root.addWidget(timeline_card)

        # Exportação mantém todas as funções, mas em formato visual compacto.
        export_card = QWidget(); export_card.setStyleSheet(card_css)
        ex = QVBoxLayout(export_card); ex.setContentsMargins(14, 12, 14, 12); ex.setSpacing(8)
        export_head = QHBoxLayout(); export_head.setSpacing(8)
        export_title = QLabel('EXPORTAÇÃO')
        export_title.setStyleSheet('color:#ffffff; font-size:11.5pt; font-weight:750; background:transparent; border:none;')
        export_head.addWidget(export_title)
        self.output_name = QLineEdit('video_final.mp4'); self.output_name.setStyleSheet(field_css)
        self.resolution = QComboBox(); self.resolution.addItems(['Original', '360p', '480p', '720p', '1080p'])
        self.codec = QComboBox(); self.codec.addItems(['H.264 / AVC', 'H.265 / HEVC']); self.codec.setCurrentIndex(1)
        export_head.addWidget(QLabel('Nome:')); export_head.addWidget(self.output_name, 1)
        export_head.addWidget(QLabel('Resolução:')); export_head.addWidget(self.resolution)
        export_head.addWidget(QLabel('Codec:')); export_head.addWidget(self.codec)
        self.btn_export = QPushButton('⇧  EXPORTAR'); self.btn_export.setStyleSheet(primary_css); self.btn_export.setMinimumWidth(150)
        export_head.addWidget(self.btn_export)
        ex.addLayout(export_head)

        self.target_check = QCheckBox('Definir tamanho aproximado do arquivo final')
        ex.addWidget(self.target_check)
        self.target_panel = QWidget(); tp = QHBoxLayout(self.target_panel); tp.setContentsMargins(0,0,0,0); tp.setSpacing(8)
        self.target_min_label = QLabel('1 MB'); self.target_max_label = QLabel('100 MB'); self.target_label = QLabel('≈ 30 MB')
        self.target_slider = QSlider(Qt.Orientation.Horizontal); self.target_slider.setRange(0, 1000)
        tp.addWidget(self.target_min_label); tp.addWidget(self.target_slider, 1); tp.addWidget(self.target_label); tp.addWidget(self.target_max_label)
        ex.addWidget(self.target_panel); self.target_panel.setVisible(False)
        self.estimate_label = QLabel('Adicione um vídeo para calcular bitrate e tamanho estimado.')
        self.estimate_label.setStyleSheet('color:#91a1bf; background:transparent; border:none;'); self.estimate_label.setWordWrap(True)
        ex.addWidget(self.estimate_label)
        progress_row = QHBoxLayout(); self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setFormat('Exportação: %p%')
        self.percent = QLabel('0%'); self.percent.setMinimumWidth(44)
        self.btn_folder = QPushButton('▣  Abrir pasta'); self.btn_folder.setStyleSheet(ghost_css)
        progress_row.addWidget(self.progress, 1); progress_row.addWidget(self.percent); progress_row.addWidget(self.btn_folder); ex.addLayout(progress_row)
        self.status = QLabel('SISTEMA PRONTO  •  Adicione um vídeo à timeline para editar e exportar.')
        self.status.setWordWrap(True); self.status.setStyleSheet('color:#a5b2cb; background:transparent; border:none;')
        ex.addWidget(self.status)
        root.addWidget(export_card)

        # Métricas mantidas para a lógica interna, sem ocupar espaço visual.
        self.metric_clips = QLabel('CLIPES  •  0'); self.metric_clips.hide()
        self.metric_duration = QLabel('DURAÇÃO  •  00:00'); self.metric_duration.hide()
        self.metric_output = QLabel('SAÍDA  •  ORIGINAL / H.265'); self.metric_output.hide()
        self.precision_panel = QWidget(); self.precision_panel.hide()

        self.btn_add.clicked.connect(self.add_videos)
        self.btn_reset_visual.clicked.connect(self._reset_visual_selection)
        self.btn_up.clicked.connect(lambda: self.move_selected(-1))
        self.btn_down.clicked.connect(lambda: self.move_selected(1))
        self.btn_duplicate.clicked.connect(self.duplicate_selected)
        self.btn_cut.clicked.connect(self.cut_at_playhead)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_back5.clicked.connect(lambda: self.seek_global_by(-5000))
        self.btn_forward5.clicked.connect(lambda: self.seek_global_by(5000))
        self.btn_play.clicked.connect(self.toggle_sequence_playback)
        self.btn_zoom_out.clicked.connect(lambda: self.change_zoom(-1))
        self.btn_zoom_in.clicked.connect(lambda: self.change_zoom(1))
        self.timeline.clipSelected.connect(lambda i: self.select_clip(i, False))
        self.timeline.playheadMoved.connect(self._timeline_seek)
        self.timeline.reorderRequested.connect(self.reorder_from_timeline)
        self.range.positionChanged.connect(self._local_seek)
        self.range.positionReleased.connect(lambda pos: self._local_seek(pos))
        self.range.handleMoved.connect(self._range_handle_moved)
        self.range.handleReleased.connect(lambda *_: self._range_finished())
        self.range.valuesChanged.connect(self._range_values_changed)
        self.btn_apply.clicked.connect(lambda: self.apply_times_from_fields(True))
        self.start_edit.editingFinished.connect(lambda: self.apply_times_from_fields(False))
        self.end_edit.editingFinished.connect(lambda: self.apply_times_from_fields(False))
        self.btn_mark_start.clicked.connect(self.mark_start_here)
        self.btn_mark_end.clicked.connect(self.mark_end_here)
        self.resolution.currentIndexChanged.connect(lambda *_: self.update_export_controls(True))
        self.codec.currentIndexChanged.connect(lambda *_: self.update_export_controls(True))
        self.target_check.toggled.connect(self._target_toggled)
        self.target_slider.valueChanged.connect(self._target_slider_changed)
        self.btn_export.clicked.connect(self.export_timeline)
        self.btn_folder.clicked.connect(self.open_folder)

        # Atalho do editor: Delete remove o clipe/trecho selecionado.
        # WidgetWithChildrenShortcut mantém o atalho ativo mesmo quando o foco está
        # nos controles do editor; campos de texto são protegidos no handler.
        self.delete_shortcut = QShortcut(QKeySequence('Delete'), self)
        self.delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.delete_shortcut.activated.connect(self._delete_selected_shortcut)

    def _delete_selected_shortcut(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QComboBox, QSlider)):
            return
        if 0 <= self.selected_index < len(self.clips):
            self.remove_selected()
            self.status.setText('Trecho selecionado removido com a tecla Delete.')

    def reorder_from_timeline(self, source, target):
        source, target = int(source), int(target)
        if source == target or not (0 <= source < len(self.clips)) or not (0 <= target < len(self.clips)):
            return
        keep_playing = self.sequence_playing
        self.pause_sequence()
        clip = self.clips.pop(source)
        self.clips.insert(target, clip)
        self.selected_index = target
        self.global_playhead_ms = self.clip_global_start(target)
        self._refresh_timeline(True)
        self.load_selected_clip(False)
        self.seek_sequence(self.global_playhead_ms, keep_playing)
        self.status.setText(f'Ordem alterada: clipe movido para a posição {target + 1}.')

    def _reset_visual_selection(self):
        self.pause_sequence()
        if self.clips:
            self.global_playhead_ms = 0
            self.select_clip(0, True)
            clip = self._current_clip()
            if clip:
                self.range.setValues(int(clip['start_ms']), int(clip['end_ms']))
        self.status.setText('Editor redefinido para o início da sequência.')

    def _connect_player(self):
        self.player.positionChanged.connect(self._player_position_changed)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.errorOccurred.connect(lambda _err, text: self.status.setText(f'Prévia: {text}'))
        self.monitor.start()

    def _current_clip(self):
        if 0 <= self.selected_index < len(self.clips):
            return self.clips[self.selected_index]
        return None

    def total_duration_ms(self):
        return sum(max(0, int(c['end_ms']) - int(c['start_ms'])) for c in self.clips)

    def clip_global_start(self, index):
        return sum(max(0, int(c['end_ms']) - int(c['start_ms'])) for c in self.clips[:max(0, index)])

    def map_global(self, global_ms):
        if not self.clips:
            return None
        total = self.total_duration_ms()
        g = max(0, min(int(global_ms), total))
        acc = 0
        for idx, clip in enumerate(self.clips):
            d = max(1, int(clip['end_ms']) - int(clip['start_ms']))
            if g < acc + d or idx == len(self.clips) - 1:
                local = max(0, min(d, g - acc))
                return idx, int(clip['start_ms']) + local
            acc += d
        return len(self.clips) - 1, int(self.clips[-1]['end_ms'])

    def _refresh_timeline(self, preserve_playhead=True):
        total = self.total_duration_ms()
        self.global_playhead_ms = max(0, min(self.global_playhead_ms if preserve_playhead else 0, total))
        self.timeline.set_clips(self.clips, self.selected_index)
        self.timeline.set_playhead_ms(self.global_playhead_ms)
        self.clip_count.setText(f'{len(self.clips)} ' + ('clipe' if len(self.clips) == 1 else 'clipes') + f' • {format_short(total)}')
        if hasattr(self, 'metric_clips'):
            self.metric_clips.setText(f'CLIPES  •  {len(self.clips)}')
            self.metric_duration.setText(f'DURAÇÃO  •  {format_short(total)}')
        self.seq_current.setText(f'{format_short(self.global_playhead_ms)} / {format_short(total)}')
        self.update_export_controls(False)
        self._update_controls()

    def _update_controls(self):
        has = bool(self.clips)
        selected = self._current_clip() is not None
        busy = bool(self.export_worker and self.export_worker.isRunning())
        for w in (self.btn_up, self.btn_down, self.btn_duplicate, self.btn_cut, self.btn_remove, self.btn_play, self.btn_back5, self.btn_forward5, self.btn_zoom_out, self.btn_zoom_in):
            w.setEnabled(has and not busy)
        for w in (self.range, self.start_edit, self.end_edit, self.btn_apply, self.btn_mark_start, self.btn_mark_end, *self.nudge_buttons):
            w.setEnabled(selected and not busy)
        self.btn_add.setEnabled(not busy)
        self.btn_export.setEnabled(has and not busy)
        self.resolution.setEnabled(not busy)
        self.codec.setEnabled(not busy)
        self.target_check.setEnabled(not busy)
        self.target_slider.setEnabled(not busy and self.target_check.isChecked())
        self.timeline.setEnabled(not busy)

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Adicionar vídeos à timeline', str(self.videos_dir),
            'Vídeos (*.mp4 *.mkv *.webm *.mov *.avi *.m4v);;Todos os arquivos (*)'
        )
        if not files:
            return
        self.status.setText('Analisando vídeos...')
        QApplication.processEvents()
        first_new = len(self.clips)
        added = 0
        for file in files:
            info = _probe_media_info(file, self.ffprobe_exe, self.ffmpeg_exe)
            duration = int(info.get('duration_ms') or 0)
            if duration <= 0:
                continue
            clip = {
                'path': str(Path(file)), 'duration_ms': duration, 'start_ms': 0, 'end_ms': duration,
                'info': info, 'cut_before': False,
            }
            self.clips.append(clip)
            self._queue_thumbnail(clip)
            added += 1
        if added:
            self.selected_index = first_new
            self.global_playhead_ms = self.clip_global_start(self.selected_index)
            self._refresh_timeline(True)
            self.load_selected_clip(False)
            self.seek_sequence(self.global_playhead_ms, False)
            self.status.setText(f'Timeline pronta: {len(self.clips)} clipe(s) • {format_short(self.total_duration_ms())}')
        else:
            QMessageBox.warning(self, 'Extrator de Vídeos', 'Não foi possível ler os vídeos selecionados.')

    def select_clip(self, index, move_playhead=True):
        if not (0 <= index < len(self.clips)):
            return
        self.selected_index = index
        self.timeline.set_selected_index(index)
        self.load_selected_clip(move_playhead)

    def load_selected_clip(self, move_playhead=True):
        clip = self._current_clip()
        if not clip:
            self.selected_label.setText('Selecione um clipe na timeline')
            self.info_label.setText('')
            self.start_edit.clear(); self.end_edit.clear()
            if hasattr(self, 'duration_value'):
                self.duration_value.setText('00:00:00.000')
            self._update_controls()
            return
        info = clip.get('info') or {}
        fps = float(info.get('fps') or 0)
        res = f"{info.get('width', 0)}x{info.get('height', 0)}" if info.get('width') and info.get('height') else 'resolução --'
        self.selected_label.setText(Path(clip['path']).name)
        self.info_label.setText(
            f"Original {format_ms(clip['duration_ms'])} • trecho {format_ms(clip['end_ms'] - clip['start_ms'])} • "
            f"{res} • {fps:.2f} fps" + (' • áudio' if info.get('has_audio') else ' • sem áudio')
        )
        self._changing_range = True
        self.start_edit.setText(format_ms(clip['start_ms']))
        self.end_edit.setText(format_ms(clip['end_ms']))
        if hasattr(self, 'duration_value'):
            self.duration_value.setText(format_ms(int(clip['end_ms']) - int(clip['start_ms'])))
        self.range.setRange(0, max(1, int(clip['duration_ms'])))
        self.range.setValues(int(clip['start_ms']), int(clip['end_ms']), emit=False)
        self.range.setPosition(int(clip['start_ms']), emit=False)
        self._changing_range = False
        self._update_local_position(int(clip['start_ms']))
        if move_playhead:
            self.global_playhead_ms = self.clip_global_start(self.selected_index)
            self._refresh_timeline(True)
            self.seek_sequence(self.global_playhead_ms, False)
        self._update_controls()

    def move_selected(self, delta):
        if not (0 <= self.selected_index < len(self.clips)):
            return
        target = self.selected_index + int(delta)
        if not (0 <= target < len(self.clips)):
            return
        keep = self.sequence_playing
        self.pause_sequence()
        self.clips[self.selected_index], self.clips[target] = self.clips[target], self.clips[self.selected_index]
        self.selected_index = target
        self.global_playhead_ms = self.clip_global_start(target)
        self._refresh_timeline(True)
        self.load_selected_clip(False)
        self.seek_sequence(self.global_playhead_ms, keep)

    def duplicate_selected(self):
        clip = self._current_clip()
        if not clip:
            return
        self.pause_sequence()
        copy = dict(clip)
        copy['info'] = dict(clip.get('info') or {})
        copy['cut_before'] = False
        insert = self.selected_index + 1
        self.clips.insert(insert, copy)
        self.selected_index = insert
        self.global_playhead_ms = self.clip_global_start(insert)
        self._queue_thumbnail(copy)
        self._refresh_timeline(True)
        self.load_selected_clip(False)
        self.seek_sequence(self.global_playhead_ms, False)

    def cut_at_playhead(self):
        pos = self.map_global(self.global_playhead_ms)
        if not pos:
            return
        idx, source_ms = pos
        original = self.clips[idx]
        guard = 40
        if source_ms <= int(original['start_ms']) + guard or source_ms >= int(original['end_ms']) - guard:
            QMessageBox.information(self, 'Extrator de Vídeos', 'Mova o cursor para dentro do trecho antes de cortar.')
            return
        keep = self.sequence_playing
        self.pause_sequence()
        left = dict(original); left['info'] = dict(original.get('info') or {}); left['end_ms'] = source_ms
        right = dict(original); right['info'] = dict(original.get('info') or {}); right['start_ms'] = source_ms; right['cut_before'] = True
        self.clips[idx] = left
        self.clips.insert(idx + 1, right)
        self.selected_index = idx + 1
        self._queue_thumbnail(left); self._queue_thumbnail(right)
        self._refresh_timeline(True)
        self.load_selected_clip(False)
        self.seek_sequence(self.global_playhead_ms, keep)
        self.status.setText(f'Corte criado em {format_ms(source_ms)}. Selecione um trecho e use EXCLUIR TRECHO para removê-lo.')

    def remove_selected(self):
        if not (0 <= self.selected_index < len(self.clips)):
            return
        self.pause_sequence()
        self.clips.pop(self.selected_index)
        if not self.clips:
            self.selected_index = -1
            self.global_playhead_ms = 0
            self.player.stop(); self.player.setSource(QUrl())
            self._refresh_timeline(False)
            self.load_selected_clip(False)
            return
        if self.selected_index >= len(self.clips):
            self.selected_index = len(self.clips) - 1
        self.global_playhead_ms = self.clip_global_start(self.selected_index)
        self._refresh_timeline(True)
        self.load_selected_clip(False)
        self.seek_sequence(self.global_playhead_ms, False)

    def apply_times_from_fields(self, show_message):
        clip = self._current_clip()
        if not clip:
            return False
        try:
            start = parse_time(self.start_edit.text())
            end = parse_time(self.end_edit.text())
            if start < 0 or end <= start or end > int(clip['duration_ms']) + 5:
                raise ValueError('O fim precisa ser maior que o início e não pode ultrapassar o vídeo.')
            self.pause_sequence()
            clip['start_ms'] = max(0, start)
            clip['end_ms'] = min(int(clip['duration_ms']), end)
            self._changing_range = True
            self.range.setValues(clip['start_ms'], clip['end_ms'], emit=False)
            self.range.setPosition(clip['start_ms'], emit=False)
            self._changing_range = False
            self.global_playhead_ms = self.clip_global_start(self.selected_index)
            self._queue_thumbnail(clip)
            self._refresh_timeline(True)
            self._update_local_position(clip['start_ms'])
            self.seek_sequence(self.global_playhead_ms, False)
            if show_message:
                self.status.setText('Trecho atualizado na timeline.')
            return True
        except ValueError as exc:
            if show_message:
                QMessageBox.warning(self, 'Extrator de Vídeos', str(exc))
            self.start_edit.setText(format_ms(clip['start_ms']))
            self.end_edit.setText(format_ms(clip['end_ms']))
            return False

    def _range_values_changed(self, start, end):
        if self._changing_range:
            return
        clip = self._current_clip()
        if not clip:
            return
        clip['start_ms'] = int(start); clip['end_ms'] = int(end)
        self.start_edit.setText(format_ms(start)); self.end_edit.setText(format_ms(end))
        if hasattr(self, 'duration_value'):
            self.duration_value.setText(format_ms(int(end) - int(start)))
        self._refresh_timeline(True)

    def _range_handle_moved(self, which, pos):
        if self._changing_range:
            return
        self._update_local_position(int(pos))
        clip = self._current_clip()
        if not clip:
            return
        global_ms = self.clip_global_start(self.selected_index) + max(0, min(clip['end_ms'] - clip['start_ms'], int(pos) - clip['start_ms']))
        self.seek_sequence(global_ms, False)

    def _range_finished(self):
        clip = self._current_clip()
        if clip:
            self._queue_thumbnail(clip)
            self._refresh_timeline(True)

    def _local_seek(self, source_ms):
        clip = self._current_clip()
        if not clip:
            return
        source_ms = max(0, min(int(source_ms), int(clip['duration_ms'])))
        self._update_local_position(source_ms)
        local = max(0, min(int(clip['end_ms']) - int(clip['start_ms']), source_ms - int(clip['start_ms'])))
        global_ms = self.clip_global_start(self.selected_index) + local
        self.seek_sequence(global_ms, self.sequence_playing)

    def _nudge_local(self, delta):
        clip = self._current_clip()
        if not clip:
            return
        next_ms = max(0, min(int(clip['duration_ms']), self.range.position() + int(delta)))
        self.range.setPosition(next_ms, emit=False)
        self._local_seek(next_ms)

    def mark_start_here(self):
        clip = self._current_clip()
        if not clip:
            return
        pos = int(self.range.position())
        if pos >= int(clip['end_ms']):
            QMessageBox.warning(self, 'Extrator de Vídeos', 'O início precisa ficar antes do fim.')
            return
        self.pause_sequence()
        clip['start_ms'] = pos
        self.start_edit.setText(format_ms(pos))
        if hasattr(self, 'duration_value'):
            self.duration_value.setText(format_ms(int(clip['end_ms']) - int(clip['start_ms'])))
        self._changing_range = True
        self.range.setValues(clip['start_ms'], clip['end_ms'], emit=False)
        self._changing_range = False
        self.global_playhead_ms = self.clip_global_start(self.selected_index)
        self._queue_thumbnail(clip)
        self._refresh_timeline(True)
        self.seek_sequence(self.global_playhead_ms, False)

    def mark_end_here(self):
        clip = self._current_clip()
        if not clip:
            return
        pos = int(self.range.position())
        if pos <= int(clip['start_ms']):
            QMessageBox.warning(self, 'Extrator de Vídeos', 'O fim precisa ficar depois do início.')
            return
        self.pause_sequence()
        clip['end_ms'] = pos
        self.end_edit.setText(format_ms(pos))
        if hasattr(self, 'duration_value'):
            self.duration_value.setText(format_ms(int(clip['end_ms']) - int(clip['start_ms'])))
        self._changing_range = True
        self.range.setValues(clip['start_ms'], clip['end_ms'], emit=False)
        self._changing_range = False
        self.global_playhead_ms = self.clip_global_start(self.selected_index) + (clip['end_ms'] - clip['start_ms'])
        self._queue_thumbnail(clip)
        self._refresh_timeline(True)
        self.seek_sequence(self.global_playhead_ms, False)

    def _update_local_position(self, source_ms):
        clip = self._current_clip()
        if not clip:
            self.local_position.setText('CURSOR  •  --:--')
            return
        self.local_position.setText(f'CURSOR  •  {format_ms(source_ms)}  /  {format_ms(clip["duration_ms"])}')

    def toggle_sequence_playback(self):
        if not self.clips:
            return
        if self.sequence_playing:
            self.pause_sequence()
            return
        if self.global_playhead_ms >= self.total_duration_ms():
            self.global_playhead_ms = 0
        self.sequence_playing = True
        self.seek_sequence(self.global_playhead_ms, True)

    def pause_sequence(self):
        self.sequence_playing = False
        self.player.pause()
        self.btn_play.setText('▶ PLAY')

    def seek_global_by(self, delta):
        if not self.clips:
            return
        self.seek_sequence(self.global_playhead_ms + int(delta), self.sequence_playing)

    def _timeline_seek(self, global_ms, finished):
        self.global_playhead_ms = max(0, min(int(global_ms), self.total_duration_ms()))
        pos = self.map_global(self.global_playhead_ms)
        if pos:
            idx, source_ms = pos
            if idx != self.selected_index:
                self.select_clip(idx, False)
            self._changing_range = True
            self.range.setPosition(source_ms, emit=False)
            self._changing_range = False
            self._update_local_position(source_ms)
        self._update_global_ui(auto_scroll=False)
        self.seek_sequence(self.global_playhead_ms, self.sequence_playing if finished else False)

    def seek_sequence(self, global_ms, keep_playing=False):
        if not self.clips:
            return
        total = self.total_duration_ms()
        global_ms = max(0, min(int(global_ms), total))
        if global_ms >= total and total > 0:
            global_ms = max(0, total - 1)
        mapped = self.map_global(global_ms)
        if not mapped:
            return
        idx, source_ms = mapped
        self.global_playhead_ms = global_ms
        self.preview_clip_index = idx
        clip = self.clips[idx]
        self.preview_clip_end_source_ms = int(clip['end_ms'])
        self._pending_seek_ms = int(source_ms)
        self._pending_autoplay = bool(keep_playing)
        current = self.player.source().toLocalFile() if not self.player.source().isEmpty() else ''
        if Path(current) != Path(clip['path']):
            self.player.setSource(QUrl.fromLocalFile(str(clip['path'])))
        else:
            self._apply_pending_seek()
        self._update_global_ui(auto_scroll=True)

    def _apply_pending_seek(self):
        if self._pending_seek_ms is None:
            return
        pos = int(self._pending_seek_ms)
        auto = bool(self._pending_autoplay)
        self._pending_seek_ms = None
        self._pending_autoplay = False
        self.player.setPosition(pos)
        if auto:
            self.sequence_playing = True
            self.player.play()
        else:
            self.player.pause()

    def _media_status_changed(self, status):
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            self._apply_pending_seek()

    def _player_position_changed(self, source_pos):
        if not (0 <= self.preview_clip_index < len(self.clips)):
            return
        clip = self.clips[self.preview_clip_index]
        local = max(0, min(int(clip['end_ms']) - int(clip['start_ms']), int(source_pos) - int(clip['start_ms'])))
        self.global_playhead_ms = self.clip_global_start(self.preview_clip_index) + local
        self._update_global_ui(auto_scroll=True)
        if self.selected_index == self.preview_clip_index:
            self._changing_range = True
            self.range.setPosition(max(int(clip['start_ms']), min(int(clip['end_ms']), int(source_pos))), emit=False)
            self._changing_range = False
            self._update_local_position(int(source_pos))

    def _monitor_playback(self):
        if not self.sequence_playing or not (0 <= self.preview_clip_index < len(self.clips)):
            return
        clip = self.clips[self.preview_clip_index]
        if self.player.position() >= int(clip['end_ms']) - 35:
            next_idx = self.preview_clip_index + 1
            if next_idx >= len(self.clips):
                self.sequence_playing = False
                self.player.pause()
                self.global_playhead_ms = self.total_duration_ms()
                self._update_global_ui(auto_scroll=True)
                self.btn_play.setText('▶ PLAY')
                return
            self.selected_index = next_idx
            self.timeline.set_selected_index(next_idx)
            self.load_selected_clip(False)
            self.global_playhead_ms = self.clip_global_start(next_idx)
            self.seek_sequence(self.global_playhead_ms, True)

    def _playback_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.btn_play.setText('⏸ PAUSAR' if playing else '▶ PLAY')
        if not playing and self.sequence_playing and self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self.sequence_playing = False

    def _update_global_ui(self, auto_scroll=False):
        total = self.total_duration_ms()
        self.global_playhead_ms = max(0, min(int(self.global_playhead_ms), total))
        self.timeline.set_playhead_ms(self.global_playhead_ms)
        self.seq_current.setText(f'{format_short(self.global_playhead_ms)} / {format_short(total)}')
        if auto_scroll and total > 0:
            x = self.timeline._x_for_global(self.global_playhead_ms)
            bar = self.timeline_scroll.horizontalScrollBar()
            viewport = self.timeline_scroll.viewport().width()
            target = int(x - viewport * 0.45)
            bar.setValue(max(bar.minimum(), min(bar.maximum(), target)))

    def change_zoom(self, delta):
        self.zoom_index = max(0, min(len(self.ZOOM_LEVELS) - 1, self.zoom_index + int(delta)))
        pps = self.ZOOM_LEVELS[self.zoom_index]
        self.timeline.set_pixels_per_second(pps)
        self.zoom_label.setText(f'Zoom {self.zoom_index + 1}/{len(self.ZOOM_LEVELS)}')
        self._update_global_ui(auto_scroll=True)

    def _target_toggled(self, checked):
        self.target_panel.setVisible(bool(checked))
        self.target_slider.setEnabled(bool(checked))
        self.update_export_controls(False)

    def _target_slider_changed(self, progress):
        if self.target_max_mb <= self.target_min_mb:
            self.target_mb = self.target_min_mb
        else:
            ratio = max(0.0, min(1.0, int(progress) / 1000.0))
            self.target_mb = int(round(self.target_min_mb + ratio * (self.target_max_mb - self.target_min_mb)))
        self.update_export_controls(False)

    def _target_to_progress(self, size_mb):
        if self.target_max_mb <= self.target_min_mb:
            return 0
        ratio = (size_mb - self.target_min_mb) / float(self.target_max_mb - self.target_min_mb)
        return max(0, min(1000, int(round(ratio * 1000))))

    def _effective_codec_for_estimate(self):
        requested = self.codec.currentText()
        if requested == 'H.265 / HEVC':
            if self._hevc_available is None:
                self._hevc_available = _ffmpeg_has_encoder(self.ffmpeg_exe, 'libx265')
            if not self._hevc_available:
                return 'H.264 / AVC'
        return requested

    def update_export_controls(self, reset_to_recommended=True):
        duration = self.total_duration_ms()
        if not self.clips or duration <= 0:
            self.target_min_mb, self.target_max_mb = 1, 100
            if reset_to_recommended:
                self.target_mb = 30
            self.target_slider.blockSignals(True)
            self.target_slider.setValue(self._target_to_progress(self.target_mb))
            self.target_slider.blockSignals(False)
            self._update_target_labels()
            self.estimate_label.setText('Adicione um vídeo para calcular bitrate e tamanho estimado.')
            if hasattr(self, 'metric_output'):
                self.metric_output.setText(f'SAÍDA  •  {self.resolution.currentText().upper()} / {self.codec.currentText().split()[0]}')
            return

        first_info = self.clips[0].get('info') or {}
        codec = self._effective_codec_for_estimate()
        resolution = self.resolution.currentText()
        lo, rec, hi = bitrate_profile(codec, resolution, first_info)
        self.target_min_mb = max(1, int(math.ceil(estimated_size_mb(duration, lo))))
        self.target_max_mb = max(self.target_min_mb + 1, int(math.ceil(estimated_size_mb(duration, hi))))
        recommended_mb = max(self.target_min_mb, min(self.target_max_mb, int(round(estimated_size_mb(duration, rec)))))
        if reset_to_recommended or self.target_mb < self.target_min_mb or self.target_mb > self.target_max_mb:
            self.target_mb = recommended_mb
        self.target_slider.blockSignals(True)
        self.target_slider.setValue(self._target_to_progress(self.target_mb))
        self.target_slider.blockSignals(False)
        self._update_target_labels()

        w, h = resolve_target_dimensions(first_info, resolution)
        fallback = self.codec.currentText() == 'H.265 / HEVC' and codec != 'H.265 / HEVC'
        fallback_text = ' • HEVC indisponível → H.264' if fallback else ''
        if hasattr(self, 'metric_output'):
            codec_short = codec.split()[0]
            self.metric_output.setText(f'SAÍDA  •  {resolution.upper()} / {codec_short}')
        if self.target_check.isChecked():
            vb = bitrate_for_target_size(self.target_mb, duration, codec, resolution, first_info)
            self.estimate_label.setText(
                f'Alvo aproximado: {self.target_mb} MB • {w}×{h} • {codec}/AAC 128 kbps • vídeo ~{vb / 1_000_000:.1f} Mbps{fallback_text}'
            )
        else:
            estimate = estimated_size_mb(duration, rec)
            self.estimate_label.setText(
                f'Compressão automática • {w}×{h} • {codec} • estimativa ~{max(1, round(estimate))} MB{fallback_text}'
            )

    def _update_target_labels(self):
        self.target_min_label.setText(f'{self.target_min_mb} MB')
        self.target_max_label.setText(f'{self.target_max_mb} MB')
        self.target_label.setText(f'≈ {self.target_mb} MB')

    def export_timeline(self):
        if not self.clips:
            QMessageBox.warning(self, 'Extrator de Vídeos', 'Adicione pelo menos um vídeo à timeline.')
            return
        if self.export_worker and self.export_worker.isRunning():
            return
        if not self.apply_times_from_fields(False) and self._current_clip():
            QMessageBox.warning(self, 'Extrator de Vídeos', 'Confira os tempos do clipe selecionado.')
            return
        self.pause_sequence()
        output = _unique_output(self.videos_dir, self.output_name.text())
        self.progress.setValue(0); self.percent.setText('0%')
        self.status.setText('Preparando a timeline para exportação...')
        self.export_worker = SmartExportWorker(
            self.clips, output, self.resolution.currentText(), self.codec.currentText(),
            self.target_check.isChecked(), self.target_mb, self.ffmpeg_exe, self.ffprobe_exe, self,
        )
        self.export_worker.progress.connect(self._export_progress)
        self.export_worker.message.connect(self.status.setText)
        self.export_worker.done.connect(self._export_done)
        self.export_worker.failed.connect(self._export_failed)
        self.export_worker.finished.connect(self._update_controls)
        self.export_worker.start()
        self._update_controls()

    def _export_progress(self, value):
        value = max(0, min(100, int(value)))
        self.progress.setValue(value); self.percent.setText(f'{value}%')

    def _export_done(self, result):
        self._export_progress(100)
        path = Path(result['path'])
        self.status.setText(f'✓ Exportação concluída: {path.name} • {result["actual_mb"]:.1f} MB')
        msg = (
            f'O vídeo foi salvo na pasta Videos.\n\n'
            f'Tamanho gerado: {result["actual_mb"]:.1f} MB\n'
            f'Codec: {result["codec"]}\n'
            f'Resolução: {result["width"]}×{result["height"]}'
        )
        if result.get('target_size_enabled'):
            msg += f'\nTamanho solicitado: ~{result["target_size_mb"]} MB'
        if result.get('requested_codec') != result.get('codec'):
            msg += '\n\nHEVC não estava disponível; foi usado H.264 automaticamente.'
        msg += '\n\nOs vídeos originais foram mantidos.'
        box = QMessageBox(self)
        box.setWindowTitle('Exportação concluída')
        box.setText(msg)
        open_button = box.addButton('ABRIR PASTA', QMessageBox.ButtonRole.AcceptRole)
        box.addButton('FECHAR', QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == open_button:
            self.open_folder()

    def _export_failed(self, message):
        self.status.setText('Falha na exportação.')
        QMessageBox.critical(self, 'Extrator de Vídeos', message)

    def open_folder(self):
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            os.startfile(str(self.videos_dir))
        else:
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.videos_dir)))

    def _queue_thumbnail(self, clip):
        key = self.timeline._clip_key(clip)
        if key in self.timeline.thumb_cache or key in self._thumbnail_keys_queued:
            return
        self._thumbnail_keys_queued.add(key)
        self._thumbnail_queue.append((key, clip['path'], clip['start_ms'], clip['end_ms']))
        self._start_next_thumbnail()

    def _start_next_thumbnail(self):
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            return
        if not self._thumbnail_queue:
            self._thumbnail_worker = None
            return
        key, path, start, end = self._thumbnail_queue.pop(0)
        worker = ThumbnailWorker(key, path, start, end, self.ffmpeg_exe, self)
        self._thumbnail_worker = worker
        worker.ready.connect(self._thumbnail_ready)
        worker.finished.connect(self._start_next_thumbnail)
        worker.start()

    def _thumbnail_ready(self, key, frames):
        self._thumbnail_keys_queued.discard(key)
        self.timeline.set_thumbnails(key, frames)

    def shutdown(self):
        self.monitor.stop()
        self.sequence_playing = False
        self.player.stop()
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.wait(3000)
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            self._thumbnail_worker.wait(1500)
