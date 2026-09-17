from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from urllib.parse import urljoin, urlparse

import requests

from monitor_noticias.windows.dpapi import DpapiTextStore
from monitor_noticias.windows.processes import HiddenProcessRunner

log = logging.getLogger(__name__)
UA_HTML = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"


@dataclass(frozen=True, slots=True)
class ExtractorQuality:
    label: str
    selector: str
    compat: str
    max_height: int | None


EXTRACTOR_QUALITIES: tuple[ExtractorQuality, ...] = (
    ExtractorQuality("360p", "bv*[height<=360][ext=mp4]+ba[ext=m4a]/b[height<=360][ext=mp4]/bv*[height<=360]+ba/b[height<=360]/b", "b[height<=360][ext=mp4]/b[height<=360]/b", 360),
    ExtractorQuality("480p", "bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/bv*[height<=480]+ba/b[height<=480]/b", "b[height<=480][ext=mp4]/b[height<=480]/b", 480),
    ExtractorQuality("720p HD", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/b[height<=720]/b", "b[height<=720][ext=mp4]/b[height<=720]/b", 720),
    ExtractorQuality("1080p Full HD", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b[height<=1080]/b", "b[height<=1080][ext=mp4]/b[height<=1080]/b", 1080),
    ExtractorQuality("Melhor disponível", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b", "b[ext=mp4]/b", None),
)


def normalize_r7_url(value: str) -> str:
    url = value.strip()
    matches = list(re.finditer(r"https?://", url, flags=re.I))
    if len(matches) > 1:
        url = url[: matches[1].start()]
    return url.replace(" ", "%20")


def classify_source(url: str) -> str:
    low = url.lower()
    if "youtube.com" in low or "youtu.be" in low:
        return "youtube"
    if "globoplay.globo.com" in low or low.startswith("globo:"):
        return "globoplay"
    if "r7.com" in low or "record" in low:
        return "r7"
    return "generic"


def _proxy_dict(proxy_url: str) -> dict[str, str] | None:
    value = proxy_url.strip()
    return {"http": value, "https": value} if value else None


def _get_html(page_url: str, proxy_url: str) -> str:
    response = requests.get(
        page_url,
        headers={"User-Agent": UA_HTML, "Referer": page_url},
        proxies=_proxy_dict(proxy_url),
        timeout=(30, 30),
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text.replace("\\u0026", "&").replace("\\/", "/").replace("&amp;", "&")


_DIRECT_EXT = (".m3u8", ".mp4", ".m4v", ".webm", ".mov")


def is_direct_media_url(url: str) -> bool:
    try:
        return urlparse(url).path.lower().endswith(_DIRECT_EXT)
    except Exception:
        return False


def direct_media_candidates(page_url: str, proxy_url: str = "") -> list[str]:
    try:
        html = _get_html(page_url, proxy_url)
        absolute = re.findall(
            r"https?://[^\s\"'<>]+?(?:\.m3u8|\.mp4|\.m4v|\.webm|\.mov)(?:\?[^\s\"'<>]*)?",
            html,
            flags=re.I,
        )
        attributed = [
            urljoin(page_url, x)
            for x in re.findall(
                r"(?:src|href|url|file|contentUrl)\s*[:=]\s*[\"']([^\"']+?(?:\.m3u8|\.mp4|\.m4v|\.webm|\.mov)[^\"']*)",
                html,
                flags=re.I,
            )
        ]
        out: list[str] = []
        for raw in [*absolute, *attributed]:
            value = raw.strip().strip("\"'")
            low = value.lower()
            valid = (
                (value.startswith("http://") or value.startswith("https://"))
                and len(value) <= 4096
                and not any(x in low for x in ("doubleclick", "analytics", "pixel", "tracking", "favicon", "logo.", "sprite"))
                and is_direct_media_url(value)
            )
            if valid and value not in out:
                out.append(value)
            if len(out) >= 15:
                break
        return out
    except Exception:
        return []


def r7_media_candidates(page_url: str, proxy_url: str = "") -> list[str]:
    try:
        html = _get_html(page_url, proxy_url)
        absolute = re.findall(
            r"https?://[^\s\"'<>]+?(?:\.m3u8|\.mp4|\.m4v|\.webm)(?:\?[^\s\"'<>]*)?",
            html,
            flags=re.I,
        )
        attributed = [
            urljoin(page_url, x)
            for x in re.findall(
                r"(?:src|url|file|contentUrl)\s*[:=]\s*[\"']([^\"']+?(?:\.m3u8|\.mp4|\.m4v|\.webm)[^\"']*)",
                html,
                flags=re.I,
            )
        ]
        out: list[str] = []
        for raw in [*absolute, *attributed]:
            value = raw.strip().strip("\"'")
            low = value.lower()
            if (
                (value.startswith("http://") or value.startswith("https://"))
                and not any(x in low for x in ("doubleclick", "analytics", "pixel"))
                and value not in out
            ):
                out.append(value)
            if len(out) >= 15:
                break
        return out
    except Exception:
        return []


def globoplay_m3u8_candidates(page_url: str, proxy_url: str = "") -> list[str]:
    try:
        html = _get_html(page_url, proxy_url)
        absolute = re.findall(r"https?://[^\s\"'<>]+?\.m3u8[^\s\"'<>]*", html, flags=re.I)
        attributed = [
            urljoin(page_url, x)
            for x in re.findall(r"(?:src|url|file)\s*[:=]\s*[\"']([^\"']+?\.m3u8[^\"']*)", html, flags=re.I)
        ]
        out: list[str] = []
        for value in [*absolute, *attributed]:
            if (value.startswith("http://") or value.startswith("https://")) and value not in out:
                out.append(value)
            if len(out) >= 15:
                break
        return out
    except Exception:
        return []


class ExtractorPortableStateStore:
    def __init__(self, app_root: Path) -> None:
        self.data_dir = Path(app_root) / "data" / "extractor"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / "settings.properties"
        self.history_file = self.data_dir / "history.txt"

    def load_quality_index(self, default_value: int = 1) -> int:
        safe_default = max(0, min(default_value, len(EXTRACTOR_QUALITIES) - 1))
        try:
            if not self.settings_file.exists():
                return safe_default
            for raw in self.settings_file.read_text(encoding="utf-8", errors="replace").splitlines():
                if raw.strip().startswith("qualityIndex="):
                    value = int(raw.split("=", 1)[1].strip())
                    return max(0, min(value, len(EXTRACTOR_QUALITIES) - 1))
        except Exception:
            pass
        return safe_default

    def save_quality_index(self, value: int) -> None:
        safe = max(0, min(value, len(EXTRACTOR_QUALITIES) - 1))
        keep: list[str] = []
        if self.settings_file.exists():
            keep = [
                x for x in self.settings_file.read_text(encoding="utf-8", errors="replace").splitlines()
                if not x.strip().startswith("qualityIndex=") and not x.startswith("#")
            ]
        self.settings_file.write_text(
            "#Extractor de Videos portable settings\n" + f"qualityIndex={safe}\n" + "\n".join(keep),
            encoding="utf-8",
        )

    def load_history(self, limit: int = 50) -> list[str]:
        if not self.history_file.exists():
            return []
        out: list[str] = []
        for raw in self.history_file.read_text(encoding="utf-8", errors="replace").splitlines():
            value = raw.strip()
            if value and value not in out:
                out.append(value)
            if len(out) >= max(1, limit):
                break
        return out

    def add_history(self, path: str, limit: int = 50) -> list[str]:
        normalized = path.strip()
        if not normalized:
            return self.load_history(limit)
        out = [normalized]
        for item in self.load_history(limit * 2):
            if item not in out:
                out.append(item)
            if len(out) >= max(1, limit):
                break
        self.history_file.write_text(os.linesep.join(out), encoding="utf-8")
        return out

    def clear_history(self) -> bool:
        try:
            self.history_file.unlink()
        except FileNotFoundError:
            pass
        return True


class GloboplaySessionStore:
    def __init__(self, app_root: Path) -> None:
        self.session_dir = Path(app_root) / "data" / "extractor"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.encrypted_file = self.session_dir / "globoplay.session.dpapi"
        self.store = DpapiTextStore(self.encrypted_file)

    def has_saved_session(self) -> bool:
        return self.store.exists()

    def save_netscape_cookies(self, cookie_text: str) -> None:
        if not cookie_text.strip():
            raise ValueError("A sessão do Globoplay está vazia.")
        self.store.save(cookie_text)

    def create_runtime_cookie_file(self) -> Path | None:
        if not self.has_saved_session():
            return None
        try:
            text = self.store.load()
            fd, name = tempfile.mkstemp(prefix="globoplay-session-", suffix=".cookies.txt")
            os.close(fd)
            path = Path(name)
            path.write_text(text, encoding="utf-8")
            return path
        except Exception:
            return None

    def delete_saved_session(self) -> bool:
        return self.store.delete()


@dataclass(frozen=True, slots=True)
class ProcessCapture:
    exit_code: int
    output: str


class ExtractorCancelled(RuntimeError):
    pass


class ExtractorEngine:
    def __init__(self, app_root: Path, runner: HiddenProcessRunner | None = None) -> None:
        self.app_root = Path(app_root)
        self.bin_dir = self.app_root / "bin"
        self.videos_dir = self.app_root / "Videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.yt_dlp = self.bin_dir / "yt-dlp.exe"
        self.yt_dlp_stable = self.bin_dir / "yt-dlp-stable.exe"
        self.ffmpeg = self.bin_dir / "ffmpeg.exe"
        self.ffprobe = self.bin_dir / "ffprobe.exe"
        self.deno = self.bin_dir / "deno.exe"
        self.runner = runner or HiddenProcessRunner()
        self.session_store = GloboplaySessionStore(self.app_root)
        self._lock = threading.Lock()
        self._active = None
        self._cancelled = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            proc = self._active
            self._active = None
        self.runner.destroy_tree(proc)

    def _set_active(self, proc) -> None:
        with self._lock:
            self._active = proc

    def _clear_active(self, proc=None) -> None:
        with self._lock:
            if proc is None or self._active is proc:
                self._active = None

    def _check_cancelled(self) -> None:
        if self._cancelled:
            raise ExtractorCancelled("Download cancelado.")

    def _common_runtime(self, cmd: list[str], proxy: str) -> None:
        if self.deno.exists():
            cmd += ["--js-runtimes", f"deno:{self.deno}"]
        if proxy.strip():
            cmd += ["--proxy", proxy.strip()]

    def _capture(self, cmd: list[str], timeout: float) -> ProcessCapture:
        self._check_cancelled()
        proc = self.runner.start(cmd, directory=self.app_root)
        self._set_active(proc)
        try:
            try:
                output, _ = proc.communicate(timeout=timeout)
            except Exception as exc:
                import subprocess
                if isinstance(exc, subprocess.TimeoutExpired):
                    self.runner.destroy_tree(proc)
                    return ProcessCapture(-1, (exc.output or "") + "\nTimeout")
                raise
            return ProcessCapture(proc.returncode, output or "")
        finally:
            self._clear_active(proc)

    def download(self, url: str, quality: ExtractorQuality, proxy: str = "", update=lambda _p, _m: None) -> Path:
        self._cancelled = False
        if not self.yt_dlp.exists():
            raise FileNotFoundError("yt-dlp.exe não encontrado na pasta bin.")
        if not self.ffmpeg.exists():
            raise FileNotFoundError("ffmpeg.exe não encontrado na pasta bin.")
        clean_url = normalize_r7_url(url)
        if not clean_url:
            raise ValueError("Informe um link válido.")
        source = classify_source(clean_url)
        if source == "youtube":
            return self._download_youtube(clean_url, quality, proxy, update)
        if source == "globoplay":
            return self._download_globoplay(clean_url, quality, proxy, update)
        if source == "r7":
            return self._download_r7(clean_url, quality, proxy, update)
        return self._download_generic_with_html_fallback(clean_url, quality, proxy, update)

    def _probe_youtube(self, url: str, proxy: str) -> tuple[bool, int | None]:
        cmd = [str(self.yt_dlp), "--ignore-config", "--no-playlist", "--dump-single-json", "--skip-download", "--socket-timeout", "30"]
        self._common_runtime(cmd, proxy)
        cmd.append(url)
        result = self._capture(cmd, 90)
        if result.exit_code != 0 or not result.output.strip():
            return False, None
        try:
            line = next(x.strip() for x in reversed(result.output.splitlines()) if x.strip().startswith("{"))
            data = json.loads(line)
            status = str(data.get("live_status", "")).lower()
            live = bool(data.get("is_live", False)) or status == "is_live"
            stamp = data.get("release_timestamp") or data.get("timestamp")
            return live, int(stamp) if stamp and int(stamp) > 0 else None
        except Exception:
            return False, None

    def _download_youtube(self, url: str, quality: ExtractorQuality, proxy: str, update) -> Path:
        live, timestamp = self._probe_youtube(url, proxy)
        if live:
            update(0, "🔴 Live detectada. Baixando do início até o ponto atual...")
            file = self._download_youtube_live(url, quality, proxy, timestamp, update)
        else:
            file = self._download_generic(url, quality, proxy, "YouTube", update)
        return self._ensure_h264(file, update)

    def _download_youtube_live(self, url: str, quality: ExtractorQuality, proxy: str, start_timestamp: int | None, update) -> Path:
        try:
            return self._live_snapshot(url, quality, proxy, start_timestamp, update)
        except ExtractorCancelled:
            raise
        except Exception:
            update(0, "O snapshot HLS não ficou disponível. Tentando modo compatível do yt-dlp…")
        now = int(time.time())
        target = now - start_timestamp if start_timestamp and 0 < start_timestamp < now else None
        if not target or target <= 0:
            raise RuntimeError("Não foi possível determinar o ponto atual da live com segurança. O download foi interrompido para não acompanhar a transmissão indefinidamente.")
        end = self._format_time(target)
        selector = f"b[height<={quality.max_height}]/b" if quality.max_height is not None else "b"
        update(0, f"🔴 Live detectada. Baixando do início até o ponto atual ({end})...")
        return self._run_ytdlp(
            url,
            selector,
            proxy,
            ["--live-from-start", "--hls-use-mpegts", "--download-sections", f"*00:00:00-{end}", "--force-keyframes-at-cuts", "--concurrent-fragments", "4"],
            update,
        )

    def _live_snapshot(self, url: str, quality: ExtractorQuality, proxy: str, known_start: int | None, update) -> Path:
        update(0, "🔴 Confirmando a live e congelando o ponto final…")
        cmd = [str(self.yt_dlp), "--no-playlist", "--dump-single-json", "--skip-download", "--socket-timeout", "25", "--ffmpeg-location", str(self.bin_dir)]
        self._common_runtime(cmd, proxy)
        cmd.append(url)
        captured = self._capture(cmd, 90)
        if captured.exit_code != 0:
            raise RuntimeError(captured.output[-1600:] or "Falha ao confirmar a live.")
        line = next((x.strip() for x in reversed(captured.output.splitlines()) if x.strip().startswith("{")), "")
        if not line:
            raise RuntimeError("O YouTube não retornou metadados válidos para a live.")
        data = json.loads(line)
        status = str(data.get("live_status", ""))
        if not (bool(data.get("is_live", False)) or status == "is_live"):
            raise RuntimeError("O link não está mais ao vivo. Se a transmissão terminou, baixe como vídeo normal.")
        now = int(time.time())
        start = int(data.get("release_timestamp") or data.get("timestamp") or known_start or 0)
        duration = int(float(data.get("duration") or 0))
        if start > 0 and start < now:
            target = max(5, now - start - 2)
        elif duration > 0:
            target = max(5, duration - 2)
        else:
            raise RuntimeError("Não foi possível identificar quando a live começou. Esta transmissão pode estar sem DVR desde o início.")
        update(0, f"🔴 LIVE: baixar 00:00:00 → {self._format_time(target)}. A transmissão continuará, mas o arquivo parará nesse ponto.")
        fmt = self._select_muxed_hls(data, quality.max_height if quality.max_height is not None else 2**31 - 1)
        if fmt is None:
            raise RuntimeError("Nenhuma variante HLS muxada com áudio e vídeo foi encontrada para congelar o DVR.")
        headers = {str(k): str(v) for k, v in dict(fmt.get("http_headers") or {}).items() if str(v)}
        headers.setdefault("User-Agent", "Mozilla/5.0")
        headers.setdefault("Referer", "https://www.youtube.com/")
        frozen, temp_dir, _total = self._freeze_playlist(str(fmt.get("url", "")), headers, proxy, target)
        try:
            title = self._safe_live_name(str(data.get("title") or "Live YouTube"))
            video_id = self._safe_live_name(str(data.get("id") or "live"))
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output = self.videos_dir / f"{title} [LIVE-ATE-AGORA {stamp}] [{video_id}].mp4"
            suffix = 2
            while output.exists():
                output = self.videos_dir / f"{title} [LIVE-ATE-AGORA {stamp}-{suffix}] [{video_id}].mp4"
                suffix += 1
            if self._ffmpeg_snapshot(frozen, headers, proxy, target, output, False, update) and output.exists() and output.stat().st_size > 1024:
                return output
            output.unlink(missing_ok=True)
            update(1, "Remux direto não funcionou; tentando H.264/AAC…")
            if not self._ffmpeg_snapshot(frozen, headers, proxy, target, output, True, update) or not output.exists() or output.stat().st_size <= 1024:
                output.unlink(missing_ok=True)
                raise RuntimeError("FFmpeg não conseguiu processar a playlist DVR congelada.")
            return output
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _select_muxed_hls(self, data: dict, wanted_height: int) -> dict | None:
        candidates = []
        for fmt in data.get("formats") or []:
            url = str(fmt.get("url") or "")
            protocol = str(fmt.get("protocol") or "").lower()
            if not url or ("m3u8" not in protocol and ".m3u8" not in url.lower() and "manifest/hls" not in url.lower()):
                continue
            if str(fmt.get("vcodec", "none")) == "none" or str(fmt.get("acodec", "none")) == "none":
                continue
            height = int(float(fmt.get("height") or 0))
            tbr = float(fmt.get("tbr") or 0)
            over = 1 if height > 0 and height > wanted_height else 0
            distance = abs((height if height > 0 else wanted_height) - wanted_height)
            candidates.append((over, distance, -height, -tbr, fmt))
        candidates.sort(key=lambda x: x[:4])
        return candidates[0][4] if candidates else None

    def _freeze_playlist(self, playlist_url: str, headers: dict[str, str], proxy: str, target_seconds: int) -> tuple[Path, Path, float]:
        r = requests.get(playlist_url, headers=headers, proxies=_proxy_dict(proxy), timeout=(45, 45), allow_redirects=True)
        r.raise_for_status()
        raw = r.text
        if "#EXTM3U" not in raw:
            raise RuntimeError("O YouTube não retornou uma playlist HLS válida para esta live.")
        lines = raw.splitlines()
        if any(x.startswith("#EXT-X-STREAM-INF") for x in lines):
            variant = None
            for i, line in enumerate(lines):
                if not line.startswith("#EXT-X-STREAM-INF"):
                    continue
                for candidate in lines[i + 1 : min(i + 4, len(lines))]:
                    candidate = candidate.strip()
                    if candidate and not candidate.startswith("#"):
                        variant = urljoin(playlist_url, candidate)
                        break
                if variant:
                    break
            if not variant:
                raise RuntimeError("Não foi possível localizar a variante HLS da live.")
            playlist_url = variant
            r = requests.get(playlist_url, headers=headers, proxies=_proxy_dict(proxy), timeout=(45, 45), allow_redirects=True)
            r.raise_for_status()
            lines = r.text.splitlines()
        total = sum(float(m.group(1)) for line in lines if (m := re.match(r"#EXTINF:([0-9.]+)", line)))
        if total <= 0:
            raise RuntimeError("A playlist DVR não informou a duração dos segmentos.")
        tolerance = max(90.0, min(300.0, target_seconds * 0.04))
        if total + tolerance < target_seconds:
            raise RuntimeError(
                f"A janela DVR disponível contém cerca de {self._format_time(int(total))}, mas a live já tem aproximadamente {self._format_time(target_seconds)}. O início não está mais disponível nessa janela HLS."
            )
        uri_rx = re.compile(r'URI="([^"]+)"')
        frozen_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                frozen_lines.append(line)
            elif stripped.startswith("#"):
                frozen_lines.append(uri_rx.sub(lambda m: f'URI="{urljoin(playlist_url, m.group(1))}"', line))
            else:
                frozen_lines.append(urljoin(playlist_url, stripped))
        if not any(x.startswith("#EXT-X-ENDLIST") for x in frozen_lines):
            frozen_lines.append("#EXT-X-ENDLIST")
        temp_dir = Path(tempfile.mkdtemp(prefix="extrator-live-"))
        playlist = temp_dir / "snapshot.m3u8"
        playlist.write_text("\n".join(frozen_lines) + "\n", encoding="utf-8")
        return playlist, temp_dir, total

    def _ffmpeg_snapshot(self, playlist: Path, headers: dict[str, str], proxy: str, target_seconds: int, output: Path, transcode: bool, update) -> bool:
        cmd = [str(self.ffmpeg), "-y", "-hide_banner", "-loglevel", "warning", "-protocol_whitelist", "file,http,https,tcp,tls,crypto"]
        header_blob = "".join(f"{k}: {v}\\r\\n" for k, v in headers.items())
        if header_blob:
            cmd += ["-headers", header_blob]
        cmd += ["-i", str(playlist), "-t", str(max(1, target_seconds)), "-map", "0:v:0?", "-map", "0:a:0?"]
        if transcode:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k"]
        else:
            cmd += ["-c", "copy"]
        cmd += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(output)]
        env = {"http_proxy": proxy, "https_proxy": proxy} if proxy.strip() else None
        proc = self.runner.start(cmd, directory=self.app_root, environment=env)
        self._set_active(proc)
        tail = ""
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                self._check_cancelled()
                tail = (tail + "\n" + line)[-5000:]
                m = re.search(r"out_time_(?:ms|us)=(\d+)", line)
                if m:
                    seconds = int(m.group(1)) / 1_000_000.0
                    update(max(1, min(99, int(seconds * 100.0 / max(1, target_seconds)))), line.strip())
            code = proc.wait()
            if code != 0:
                update(0, tail[-300:])
            return code == 0
        finally:
            self._clear_active(proc)

    def _download_globoplay(self, url: str, quality: ExtractorQuality, proxy: str, update) -> Path:
        exe = self.yt_dlp_stable if self.yt_dlp_stable.exists() else self.yt_dlp
        match = re.search(r"(?:video|videos|v)/(?:[^0-9]*)([0-9]{5,})", url, flags=re.I) or re.search(r"([0-9]{6,})", url)
        video_id = match.group(1) if match else None
        cookie = self.session_store.create_runtime_cookie_file()
        try:
            common = ["--force-ipv4", "--ignore-config", "--no-mtime"]
            last_error = "Falha ao baixar conteúdo do Globoplay."
            attempts = [(url, common, "Globoplay: tentativa 1 — URL original...")]
            if video_id:
                attempts.append((f"globo:{video_id}", common, f"Globoplay: tentativa 2 — globo:{video_id}..."))
            hls_extra = common + ["--hls-use-mpegts", "--downloader", "m3u8:native"]
            attempts.append((url, hls_extra, "Globoplay: tentativa HLS nativa..."))
            for attempt_url, extra, message in attempts:
                update(0, message)
                try:
                    return self._run_ytdlp_quality(attempt_url, quality, proxy, extra, update, exe, cookie, url)
                except Exception as exc:
                    last_error = self._friendly_error(str(exc))
                    if "DRM" in last_error:
                        raise RuntimeError(last_error)
            candidates = globoplay_m3u8_candidates(url, proxy)[:15]
            for index, candidate in enumerate(candidates, start=1):
                update(0, f"Globoplay: mídia HLS {index}/{len(candidates)}...")
                try:
                    return self._run_ytdlp_quality(candidate, quality, proxy, hls_extra, update, exe, cookie, url)
                except Exception as exc:
                    last_error = self._friendly_error(str(exc))
                    if "DRM" in last_error:
                        raise RuntimeError(last_error)
            low = last_error.lower()
            if cookie is None and any(x in low for x in ("autent", "sessão", "login")):
                raise RuntimeError("Globoplay requer autenticação. Abra Configurações > Globoplay, faça login e use SALVAR SESSÃO E VOLTAR.")
            raise RuntimeError(last_error)
        finally:
            if cookie is not None:
                cookie.unlink(missing_ok=True)

    def _download_r7(self, url: str, quality: ExtractorQuality, proxy: str, update) -> Path:
        last_error = "Falha ao baixar conteúdo do R7/Record."
        base = ["--force-ipv4", "--no-mtime"]
        try:
            update(0, "R7/Record: tentando a página diretamente...")
            return self._run_ytdlp_quality(url, quality, proxy, base, update, self.yt_dlp, None, url)
        except Exception as exc:
            last_error = self._friendly_error(str(exc))
        update(0, "R7/Record: método principal falhou. Procurando vídeos dentro da página...")
        candidates = r7_media_candidates(url, proxy)[:15]
        for index, candidate in enumerate(candidates, start=1):
            extra = base + (["--hls-use-mpegts", "--downloader", "m3u8:native"] if ".m3u8" in candidate.lower() else [])
            try:
                update(0, f"R7/Record: mídia {index}/{len(candidates)}...")
                return self._run_ytdlp_quality(candidate, quality, proxy, extra, update, self.yt_dlp, None, url)
            except Exception as exc:
                last_error = self._friendly_error(str(exc))
        raise RuntimeError(last_error)

    def _download_generic_with_html_fallback(self, url: str, quality: ExtractorQuality, proxy: str, update) -> Path:
        if is_direct_media_url(url):
            extra = ["--hls-use-mpegts", "--downloader", "m3u8:native"] if ".m3u8" in url.lower() else []
            return self._run_ytdlp_quality(url, quality, proxy, extra, update, self.yt_dlp, None, url)
        last_error = "Falha ao baixar vídeo."
        try:
            return self._download_generic(url, quality, proxy, "vídeo", update)
        except Exception as exc:
            last_error = self._friendly_error(str(exc))
            if "DRM" in last_error:
                raise RuntimeError(last_error)
        candidates = direct_media_candidates(url, proxy)[:15]
        for index, candidate in enumerate(candidates, start=1):
            extra = ["--hls-use-mpegts", "--downloader", "m3u8:native"] if ".m3u8" in candidate.lower() else []
            try:
                update(0, f"Mídia encontrada na página: {index}/{len(candidates)}...")
                return self._run_ytdlp_quality(candidate, quality, proxy, extra, update, self.yt_dlp, None, url)
            except Exception as exc:
                last_error = self._friendly_error(str(exc))
                if "DRM" in last_error:
                    raise RuntimeError(last_error)
        raise RuntimeError(last_error)

    def _download_generic(self, url: str, quality: ExtractorQuality, proxy: str, source: str, update) -> Path:
        update(0, f"Iniciando download de {source} em {quality.label}...")
        return self._run_ytdlp_quality(url, quality, proxy, [], update)

    def _run_ytdlp_quality(self, url: str, quality: ExtractorQuality, proxy: str, extra: list[str], update, executable: Path | None = None, cookie_file: Path | None = None, referer: str | None = None) -> Path:
        executable = executable or self.yt_dlp
        try:
            return self._run_ytdlp(url, quality.selector, proxy, extra, update, executable, cookie_file, referer)
        except Exception as primary:
            low = str(primary).lower()
            compatibility_failure = any(x in low for x in ("403", "forbidden", "requested format", "format is not available", "qualidade escolhida não está disponível", "player response"))
            if not compatibility_failure or quality.compat == quality.selector:
                raise
            update(0, f"Formato principal incompatível. Tentando modo compatível em {quality.label}...")
            return self._run_ytdlp(url, quality.compat, proxy, extra, update, executable, cookie_file, referer)

    def _run_ytdlp(self, url: str, selector: str, proxy: str, extra: list[str], update, executable: Path | None = None, cookie_file: Path | None = None, referer: str | None = None) -> Path:
        executable = executable or self.yt_dlp
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        before = {str(p.resolve()).lower() for p in self.videos_dir.iterdir() if p.is_file()}
        cmd = [
            str(executable), "--no-playlist", "--newline", "--progress", "--windows-filenames",
            "--trim-filenames", "180", "--continue", "--retries", "10", "--fragment-retries", "10",
            "--retry-sleep", "http:linear=1::3", "--retry-sleep", "fragment:linear=1::3",
            "--socket-timeout", "30", "--ffmpeg-location", str(self.bin_dir),
            "-f", selector, "--merge-output-format", "mp4", "--remux-video", "mp4",
            "-o", str(self.videos_dir / "%(title).150B [%(id)s].%(ext)s"),
            "--print", "after_move:FINAL_FILE:%(filepath)s",
        ]
        self._common_runtime(cmd, proxy)
        if cookie_file is not None and cookie_file.exists():
            cmd += ["--cookies", str(cookie_file)]
        if referer:
            cmd += ["--referer", referer]
        cmd += extra
        cmd.append(url)
        proc = self.runner.start(cmd, directory=self.app_root)
        self._set_active(proc)
        final_path = ""
        tail = ""
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                self._check_cancelled()
                line = raw.rstrip("\r\n")
                tail = (tail + "\n" + line)[-6000:]
                if line.startswith("FINAL_FILE:"):
                    final_path = line.split("FINAL_FILE:", 1)[1].strip().strip('"')
                m = re.search(r"(\d{1,3}(?:\.\d+)?)%", line)
                if m:
                    update(max(0, min(99, int(float(m.group(1))))), line[-220:])
                elif "[download]" in line or "[Merger]" in line or "[ffmpeg]" in line.lower():
                    update(0, line[-220:])
            code = proc.wait()
            if code != 0:
                raise RuntimeError(self._friendly_error(tail))
        finally:
            self._clear_active(proc)
        if final_path:
            final = Path(final_path)
            if final.exists() and final.stat().st_size > 1024:
                return final
        candidates = [p for p in self.videos_dir.iterdir() if p.is_file() and p.stat().st_size > 1024 and str(p.resolve()).lower() not in before]
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_mtime)
        raise RuntimeError("O processo terminou, mas nenhum arquivo de vídeo válido foi criado.")

    def _ensure_h264(self, file: Path, update) -> Path:
        if not self.ffprobe.exists() or not self.ffmpeg.exists():
            return file
        codec = self._probe_codec(file)
        if codec in {"h264", "avc1"}:
            return file
        update(99, "Convertendo vídeo para H.264/AVC compatível com Windows...")
        out = file.with_name(file.stem + ".h264.mp4")
        result = self._capture([
            str(self.ffmpeg), "-y", "-i", str(file),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out),
        ], 3600)
        if result.exit_code != 0 or not out.exists() or out.stat().st_size <= 1024:
            out.unlink(missing_ok=True)
            return file
        backup = file.with_name(file.stem + ".original." + file.suffix.lstrip("."))
        try:
            file.replace(backup)
        except Exception:
            pass
        try:
            out.replace(file)
            backup.unlink(missing_ok=True)
            return file
        except Exception:
            return out

    def _probe_codec(self, file: Path) -> str:
        result = self._capture([
            str(self.ffprobe), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", str(file),
        ], 60)
        return (result.output.strip().splitlines() or [""])[0].lower()

    def _friendly_error(self, raw: str) -> str:
        text = re.sub(r"(?i)(https?|socks5?)://[^\s:@/]+:[^\s@/]+@", r"\1://***:***@", raw)
        low = text.lower()
        if "drm" in low:
            return "Este conteúdo é protegido por DRM. O Extrator apenas detecta e informa; não realiza bypass de DRM."
        if any(x in low for x in ("login", "authentication", "cookies")):
            return "O conteúdo exige autenticação ou a sessão expirou. No Globoplay, use Configurações > Globoplay e salve uma sessão válida."
        if "proxy" in low:
            return "Falha ao usar o proxy configurado. Confira servidor, porta e credenciais."
        if any(x in low for x in ("geo", "region", "country")):
            return "Conteúdo indisponível para esta região ou conta."
        if "subscription" in low or "members" in low:
            return "Este conteúdo exige assinatura/permissão da conta."
        if "unavailable" in low or "not available" in low:
            return "Conteúdo indisponível ou removido pela plataforma."
        if "format" in low:
            return "A qualidade/formato solicitado não está disponível para este vídeo."
        if "timed out" in low or "timeout" in low:
            return "A conexão expirou. Verifique rede ou proxy e tente novamente."
        return "Falha no download. Verifique rede, proxy, autenticação e disponibilidade do vídeo. Detalhe: " + text[-320:]

    @staticmethod
    def _safe_live_name(value: str) -> str:
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")[:145]
        return value or "Live YouTube"

    @staticmethod
    def _format_time(seconds: int) -> str:
        safe = max(1, int(seconds))
        return f"{safe // 3600:02d}:{(safe % 3600) // 60:02d}:{safe % 60:02d}"


@dataclass(frozen=True, slots=True)
class UpdateResult:
    success: bool
    message: str


class YtDlpUpdater:
    URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    UA = "MonitorDeNoticias-Extractor/3.0.1"

    def __init__(self, engine: ExtractorEngine) -> None:
        self.engine = engine
        self.target = engine.yt_dlp

    def _valid(self, path: Path) -> bool:
        if not path.is_file() or path.stat().st_size <= 1_000_000:
            return False
        try:
            result = self.engine.runner.run([str(path), "--version"], directory=self.engine.app_root, timeout=30)
            return result.exit_code == 0 and bool(result.output.strip())
        except Exception:
            return False

    def update(self, callback=lambda _m: None) -> UpdateResult:
        temp = self.target.with_name("yt-dlp.update.tmp.exe")
        backup = self.target.with_name("yt-dlp.backup.exe")
        try:
            callback("Baixando yt-dlp estável...")
            with requests.get(self.URL, headers={"User-Agent": self.UA}, stream=True, timeout=(30, 60)) as response:
                response.raise_for_status()
                with temp.open("wb") as out:
                    for chunk in response.iter_content(1024 * 256):
                        if chunk:
                            out.write(chunk)
            if not self._valid(temp):
                raise RuntimeError("A nova versão do yt-dlp falhou na validação.")
            backup.unlink(missing_ok=True)
            if self.target.exists():
                self.target.replace(backup)
            temp.replace(self.target)
            if not self._valid(self.target):
                raise RuntimeError("O yt-dlp instalado falhou na validação final.")
            backup.unlink(missing_ok=True)
            return UpdateResult(True, "yt-dlp atualizado e validado com sucesso.")
        except Exception as exc:
            try:
                if not self._valid(self.target) and backup.exists():
                    self.target.unlink(missing_ok=True)
                    backup.replace(self.target)
            except Exception:
                pass
            return UpdateResult(False, f"Falha ao atualizar yt-dlp: {exc}")
        finally:
            temp.unlink(missing_ok=True)
