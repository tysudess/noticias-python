from __future__ import annotations

import io
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from monitor_noticias.extractor import (
    EXTRACTOR_QUALITIES, ExtractorEngine, ExtractorPortableStateStore,
    classify_source, direct_media_candidates, is_direct_media_url, normalize_r7_url,
)
from monitor_noticias.extractor.core import ProcessCapture
from monitor_noticias.ui.extractor_page import ExtractorPage


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_exact_quality_contract():
    assert [q.label for q in EXTRACTOR_QUALITIES] == [
        "360p", "480p", "720p HD", "1080p Full HD", "Melhor disponível"
    ]
    assert [q.max_height for q in EXTRACTOR_QUALITIES] == [360, 480, 720, 1080, None]
    assert EXTRACTOR_QUALITIES[1].compat == "b[height<=480][ext=mp4]/b[height<=480]/b"


def test_source_detection_and_r7_normalization():
    assert classify_source("https://www.youtube.com/watch?v=x") == "youtube"
    assert classify_source("https://youtu.be/x") == "youtube"
    assert classify_source("https://globoplay.globo.com/v/123456/") == "globoplay"
    assert classify_source("globo:123456") == "globoplay"
    assert classify_source("https://noticias.r7.com/video") == "r7"
    assert classify_source("https://record.r7.com/a") == "r7"
    assert classify_source("https://example.test/video") == "generic"
    assert normalize_r7_url(" https://r7.com/a https://evil.invalid/b ") == "https://r7.com/a%20"


def test_direct_media_detection():
    assert is_direct_media_url("https://cdn.test/a.m3u8?token=1")
    assert is_direct_media_url("https://cdn.test/a.mp4")
    assert is_direct_media_url("https://cdn.test/a.mov")
    assert not is_direct_media_url("https://site.test/page")


def test_html_fallback_filters_and_limits(monkeypatch):
    html = """
      <video src='https://cdn.test/video.mp4'></video>
      <a href='/stream/live.m3u8?x=1'>x</a>
      <script>var p='https://analytics.test/pixel.mp4';</script>
    """

    class Response:
        text = ""
        def raise_for_status(self): return None

    response = Response()
    response.text = html
    monkeypatch.setattr("monitor_noticias.extractor.core.requests.get", lambda *a, **k: response)
    result = direct_media_candidates("https://site.test/page")
    assert "https://cdn.test/video.mp4" in result
    assert "https://site.test/stream/live.m3u8?x=1" in result
    assert all("analytics" not in x for x in result)
    assert len(result) <= 15


def test_portable_state_quality_and_history(tmp_path):
    store = ExtractorPortableStateStore(tmp_path)
    assert store.load_quality_index() == 1
    store.save_quality_index(4)
    assert store.load_quality_index() == 4
    store.add_history("C:/Videos/a.mp4")
    store.add_history("C:/Videos/b.mp4")
    store.add_history("C:/Videos/a.mp4")
    assert store.load_history() == ["C:/Videos/a.mp4", "C:/Videos/b.mp4"]
    assert store.clear_history()
    assert store.load_history() == []


class FakeProcess:
    def __init__(self, lines: str, code: int = 0):
        self.stdout = io.StringIO(lines)
        self.stdin = io.StringIO()
        self.returncode = code
        self.pid = 123
        self._code = code
    def wait(self, timeout=None): self.returncode = self._code; return self._code
    def poll(self): return self.returncode
    def communicate(self, input=None, timeout=None): self.returncode=self._code; return (self.stdout.read(), "")
    def kill(self): self.returncode=-9


class FakeRunner:
    def __init__(self, outputs=None):
        self.outputs = list(outputs or [])
        self.commands = []
        self.destroyed = []
    def start(self, command, *, directory, environment=None, merge_stderr=True):
        self.commands.append((list(command), Path(directory), environment))
        lines, code = self.outputs.pop(0) if self.outputs else ("", 0)
        return FakeProcess(lines, code)
    def run(self, command, *, directory, environment=None, stdin_text="", timeout=None):
        self.commands.append((list(command), Path(directory), environment))
        lines, code = self.outputs.pop(0) if self.outputs else ("2026.01.01\n", 0)
        return SimpleNamespace(exit_code=code, output=lines)
    def destroy_tree(self, process): self.destroyed.append(process); process.kill() if process else None


def make_engine(tmp_path, runner=None):
    bin_dir = tmp_path / "bin"; bin_dir.mkdir(parents=True, exist_ok=True)
    for name in ("yt-dlp.exe", "yt-dlp-stable.exe", "ffmpeg.exe", "ffprobe.exe", "deno.exe"):
        (bin_dir / name).write_bytes(b"x")
    return ExtractorEngine(tmp_path, runner=runner or FakeRunner())


def test_ytdlp_command_contract_and_progress(tmp_path):
    output_file = tmp_path / "Videos" / "teste [abc].mp4"
    output_file.parent.mkdir(parents=True, exist_ok=True); output_file.write_bytes(b"x" * 2048)
    runner = FakeRunner([(f"[download] 42.7%\nFINAL_FILE:{output_file}\n", 0)])
    engine = make_engine(tmp_path, runner)
    progress=[]
    result = engine._run_ytdlp("https://example.test/a", EXTRACTOR_QUALITIES[2].selector, "", [], lambda p,m: progress.append((p,m)))
    assert result == output_file
    command = runner.commands[0][0]
    required = ["--no-playlist", "--newline", "--progress", "--windows-filenames", "--trim-filenames", "180", "--continue", "--retries", "10", "--fragment-retries", "10", "--socket-timeout", "30", "--merge-output-format", "mp4", "--remux-video", "mp4"]
    for value in required: assert value in command
    assert "--js-runtimes" in command
    assert progress[0][0] == 42


def test_compat_retry_only_for_format_failures(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    calls=[]
    def run(*args, **kwargs):
        calls.append(args[1])
        if len(calls)==1: raise RuntimeError("ERROR: Requested format is not available")
        return tmp_path / "ok.mp4"
    monkeypatch.setattr(engine, "_run_ytdlp", run)
    assert engine._run_ytdlp_quality("u", EXTRACTOR_QUALITIES[0], "", [], lambda *_:None) == tmp_path/"ok.mp4"
    assert calls == [EXTRACTOR_QUALITIES[0].selector, EXTRACTOR_QUALITIES[0].compat]
    calls.clear()
    def auth(*args, **kwargs): calls.append(args[1]); raise RuntimeError("Sign in to confirm your age")
    monkeypatch.setattr(engine, "_run_ytdlp", auth)
    with pytest.raises(RuntimeError): engine._run_ytdlp_quality("u", EXTRACTOR_QUALITIES[0], "", [], lambda *_:None)
    assert calls == [EXTRACTOR_QUALITIES[0].selector]


def test_ffprobe_and_h264_command_contract(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    video=tmp_path/"Videos"/"x.mp4"; video.parent.mkdir(exist_ok=True); video.write_bytes(b"x"*2048)
    captures=[]
    def capture(cmd, timeout):
        captures.append((cmd,timeout))
        if str(engine.ffprobe) == cmd[0]: return ProcessCapture(0,"vp9\n")
        return ProcessCapture(1,"fail")
    monkeypatch.setattr(engine,"_capture",capture)
    assert engine._ensure_h264(video,lambda *_:None)==video
    assert captures[0][0][1:5] == ["-v","error","-select_streams","v:0"]
    ff=captures[1][0]
    for x in ("libx264","veryfast","20","yuv420p","aac","160k","+faststart"): assert x in ff


def test_cancel_uses_process_tree(tmp_path):
    runner=FakeRunner(); engine=make_engine(tmp_path,runner); proc=FakeProcess("")
    engine._set_active(proc); engine.cancel()
    assert runner.destroyed == [proc]


def test_extractor_page_contract(app,tmp_path):
    page=ExtractorPage(tmp_path)
    assert [page.tabs.tabText(i) for i in range(page.tabs.count())] == ["Download","Histórico","Configurações"]
    assert [b.text() for b in page.quality_buttons] == [q.label for q in EXTRACTOR_QUALITIES]
    assert page.download_button.text() == "⇩  BAIXAR VÍDEO"
    assert page.open_videos_button.text() == "Abrir Vídeos"
    assert page.cancel_button.text() == "CANCELAR"
    assert page.login_button.text() == "LOGIN GLOBOPLAY"
    assert page.delete_session_button.text() == "APAGAR SESSÃO"
    assert page.update_button.text() == "ATUALIZAR YT-DLP"
    assert page.quality_group.checkedId() == 1
