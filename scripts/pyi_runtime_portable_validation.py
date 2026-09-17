from __future__ import annotations

# Runtime hook de EMPACOTAMENTO. No uso normal é um no-op. Somente a workflow
# do portable define MONITOR_PORTABLE_SMOKE=1 para validar o próprio runtime
# congelado, sem Python do sistema e sem alterar o fluxo normal de run.py.
import os

if os.environ.get("MONITOR_PORTABLE_SMOKE") == "1":
    import json
    from datetime import datetime
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from pathlib import Path
    import subprocess
    import sys
    import threading
    import time
    import traceback
    from urllib.parse import quote

    root = Path(sys.executable).resolve().parent
    result_path = Path(
        os.environ.get(
            "MONITOR_PORTABLE_SMOKE_RESULT",
            str(root / "temp" / "portable-smoke-result.json"),
        )
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_name = result_path.stem.lower()
    if result_name.endswith("-original"):
        portable_news_link = "https://example.test/portable-noticia-smoke-1"
        portable_news_title = "Marinha realiza exercício naval smoke 1"
    elif result_name.endswith("-moved"):
        portable_news_link = "https://example.test/portable-noticia-smoke-2"
        portable_news_title = "Marinha realiza exercício naval smoke 2"
    else:
        portable_news_link = "https://example.test/portable-noticia-local"
        portable_news_title = "Marinha realiza exercício naval local"
    payload: dict[str, object] = {"ok": False, "root": str(root)}

    try:
        import winreg
        from PIL import Image
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QMediaPlayer
        from PySide6.QtWidgets import QApplication
        from pypdf import PdfReader

        from monitor_noticias.app.paths import AppPaths
        from monitor_noticias.app.preferences import SharedPreferences
        from monitor_noticias.app.runtime_runners import RuntimeNewsRunner, RuntimeVideoRunner
        from monitor_noticias.automation import AutomationService, AutomationSettings
        from monitor_noticias.database import NewsDb, VideoDb
        from monitor_noticias.models import News, VideoItem
        from monitor_noticias.networking.proxy import ProxySettings
        from monitor_noticias.pdf_editor.core import PdfCrop
        from monitor_noticias.repositories import NewsRepository, VideoRepository, VideoTermStore
        from monitor_noticias.ui.main_window import MainWindow
        from monitor_noticias.ui.runtime_controller import RuntimeUiController
        from monitor_noticias.ui.sections import SECTION_ORDER, Section
        from monitor_noticias.video_editor.core import Clip, build_export_command, probe_video
        from monitor_noticias.windows.dpapi import DpapiTextStore
        from monitor_noticias.windows.startup import RUN_KEY, VALUE_NAME, StartupManager, startup_command

        app = QApplication.instance() or QApplication([])
        paths = AppPaths(root)
        paths.ensure_runtime_dirs()

        def wait_until(predicate, timeout: float = 8.0, interval: float = 0.02) -> bool:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return True
                time.sleep(interval)
            app.processEvents()
            return bool(predicate())

        def wait_automation_idle(service: AutomationService, attr: str, timeout: float = 8.0) -> None:
            if not wait_until(lambda: not bool(getattr(service.state, attr)), timeout=timeout):
                raise RuntimeError(f"AutomationService não ficou ocioso: {attr}")

        class FakeProxy:
            def load(self):
                class C:
                    status_label = "Proxy desativado"
                return C()

        class FakeStartup:
            def configure(self, _enabled):
                return True

        # UI real empacotada: constrói todas as páginas e navega pelo mesmo stack.
        main = MainWindow(paths=paths)
        navigated: list[str] = []
        for section in SECTION_ORDER:
            main.navigate(section)
            app.processEvents()
            navigated.append(section.name)

        # Persistência básica no banco/prefs reais da raiz portable.
        persist_term = "PORTABLE TERMO TESTE"
        persist_vehicle = "VEICULO TESTE"
        persist_subject = "ASSUNTO TESTE"
        if persist_term not in main.controller.news_db.listTerms():
            main.controller.add_term(persist_term)
        if not any(
            d.vehicle == persist_vehicle and d.subject == persist_subject
            for d in main.controller.news_db.listDemands()
        ):
            main.controller.add_demand(persist_vehicle, persist_subject)
        main.controller.selected_news_source_ids = {"fonte-teste"}
        main.controller.selected_video_source_ids = {"video-cnn-brasil"}

        # PDF aberto PELO MONITOR: usa o modelo real da página integrada.
        pdf_page = main.pages[Section.PDF_EDITOR]
        pdf_model = pdf_page.model
        pdf_model.clear_all()
        pdf_model.create_blank_page()
        synthetic_image = root / "temp" / "portable-pdf-image.png"
        Image.new("RGB", (240, 160), (30, 80, 120)).save(synthetic_image, format="PNG")
        pdf_errors = pdf_model.import_files([synthetic_image])
        if pdf_errors:
            raise RuntimeError(f"Editor PDF empacotado falhou no import artificial: {pdf_errors}")
        if len(pdf_model.pages) != 2:
            raise RuntimeError("Editor PDF empacotado não criou/importou as páginas esperadas.")
        pdf_model.set_zoom(1.25)
        pdf_model.selected_index = 1
        if not pdf_model.apply_crop(PdfCrop(0.10, 0.10, 0.80, 0.80)):
            raise RuntimeError("Editor PDF empacotado não aplicou crop artificial.")
        if not pdf_model.reorder(1, 0):
            raise RuntimeError("Editor PDF empacotado não reordenou páginas.")
        if not pdf_model.undo() or not pdf_model.redo():
            raise RuntimeError("Undo/redo do Editor PDF empacotado falhou.")
        pdf_output = root / "temp" / "portable-smoke.pdf"
        pdf_model.export_pdf(pdf_output, include_cover=False)
        if not pdf_output.is_file() or len(PdfReader(str(pdf_output)).pages) != 2:
            raise RuntimeError("Editor PDF empacotado não gerou PDF artificial válido.")

        ffmpeg = root / "bin" / "ffmpeg.exe"
        ffprobe = root / "bin" / "ffprobe.exe"
        if not ffmpeg.is_file() or not ffprobe.is_file():
            raise RuntimeError("FFmpeg/FFprobe próprios ausentes.")

        media_dir = root / "temp" / "portable-media-smoke"
        media_dir.mkdir(parents=True, exist_ok=True)
        source = media_dir / "fonte teste edição.mp4"
        exported = media_dir / "saida corte.mp4"

        def run(command: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
            cp = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
            if cp.returncode != 0:
                raise RuntimeError(
                    f"Comando falhou ({cp.returncode}): {command}\n{cp.stdout}\n{cp.stderr}"
                )
            return cp

        run([
            str(ffmpeg), "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
            "-t", "2.0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(source),
        ])

        info = probe_video(source, ffprobe)
        if not (1800 <= info.duration_ms <= 2200 and info.width == 320 and info.height == 240):
            raise RuntimeError(f"FFprobe empacotado retornou mídia inesperada: {info}")

        # Editor de Vídeo aberto A PARTIR do workspace do Monitor real empacotado.
        video_page = main.pages[Section.VIDEO_EDITOR]
        video_page.open_editor()
        app.processEvents()
        if not video_page._windows:
            raise RuntimeError("Workspace do Monitor não abriu o Editor de Vídeo real.")
        editor = video_page._windows[-1]
        editor.clips.append(Clip(path=source, info=info))
        editor.refresh_media()
        editor.select_clip(0)
        editor.seek_global(0)
        app.processEvents()

        editor.player.play()
        deadline = time.monotonic() + 8.0
        max_position = 0
        while time.monotonic() < deadline:
            app.processEvents()
            max_position = max(max_position, editor.player.position())
            if editor.player.error() != QMediaPlayer.Error.NoError:
                raise RuntimeError("QMediaPlayer empacotado: " + editor.player.errorString())
            if max_position >= 300:
                break
            time.sleep(0.02)
        if max_position < 300:
            raise RuntimeError(f"Preview empacotado não avançou: {max_position} ms")

        editor.player.pause()
        app.processEvents()
        if editor.player.playbackState() != QMediaPlayer.PlaybackState.PausedState:
            raise RuntimeError("Pause do player empacotado falhou.")

        seek_positions: list[int] = []
        for target in (500, 1000, 1500):
            editor.seek_global(target)
            seek_deadline = time.monotonic() + 3.0
            while time.monotonic() < seek_deadline:
                app.processEvents()
                if abs(editor.player.position() - target) <= 250:
                    break
                time.sleep(0.02)
            current = editor.player.position()
            seek_positions.append(current)
            if abs(current - target) > 250:
                raise RuntimeError(f"Seek empacotado fora da tolerância: alvo={target}, atual={current}")
        if abs(editor.audio.volume() - 0.85) >= 0.01:
            raise RuntimeError("Volume inicial empacotado divergiu de 0.85.")

        # Corte do motor ativo: Clip possui start/end; UI manual IN/OUT permanece ausente
        # conforme a baseline e NÃO é inventada pelo smoke.
        clip = editor.clips[0]
        clip.start_ms = 250
        clip.end_ms = 1500
        command = build_export_command(ffmpeg, clip, exported)
        run(command, timeout=120)
        if not exported.is_file() or exported.stat().st_size <= 1024:
            raise RuntimeError("Exportação FFmpeg empacotada não gerou arquivo.")
        exported_info = probe_video(exported, ffprobe)
        if exported_info.video_codec != "h264" or exported_info.audio_codec != "aac":
            raise RuntimeError(f"Exportação empacotada divergente: {exported_info}")
        export_probe = json.loads(run([
            str(ffprobe), "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(exported),
        ]).stdout)
        export_audio = next(s for s in export_probe["streams"] if s.get("codec_type") == "audio")
        export_duration = float(export_probe["format"]["duration"])
        if not (1.0 <= export_duration <= 1.6):
            raise RuntimeError(f"Duração inesperada no corte exportado: {export_duration}")

        # Extrator aberto PELO MONITOR: fluxo controlado completo por HTTP localhost.
        extractor = main.pages[Section.EXTRACTOR]
        binaries = {
            "yt_dlp": extractor.engine.yt_dlp.is_file(),
            "yt_dlp_stable": extractor.engine.yt_dlp_stable.is_file(),
            "deno": extractor.engine.deno.is_file(),
            "ffmpeg": extractor.engine.ffmpeg.is_file(),
            "ffprobe": extractor.engine.ffprobe.is_file(),
        }
        if not all(binaries.values()):
            raise RuntimeError(f"Binários do Extrator incompletos: {binaries}")
        helper_resource = root / "resources" / "globoplay-login-helper" / "GloboplayLoginHelper.exe"
        if not helper_resource.is_file() or helper_resource.stat().st_size <= 20_000_000:
            raise RuntimeError("Helper Globoplay empacotado ausente/incompleto.")

        # A mídia geral mantém espaço/acentos para o gate de paths; a fixture HTTP
        # do yt-dlp usa nome ASCII para não misturar dois contratos no mesmo teste.
        extractor_source = media_dir / "extractor_fixture.mp4"
        extractor_source.write_bytes(source.read_bytes())

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, _format, *args):
                return

        handler = partial(QuietHandler, directory=str(media_dir))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server_thread = threading.Thread(target=server.serve_forever, name="portable-http-fixture", daemon=True)
        server_thread.start()

        # O runner/host pode possuir proxy por variável de ambiente. Para uma fixture
        # estritamente loopback, isola-se apenas 127.0.0.1; o motor de produção não é alterado.
        proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "NO_PROXY", "no_proxy")
        saved_proxy_env = {key: os.environ.get(key) for key in proxy_keys}
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        os.environ["no_proxy"] = "127.0.0.1,localhost"
        try:
            local_url = f"http://127.0.0.1:{server.server_port}/{quote(extractor_source.name)}"
            # Prova que a fixture local responde antes de entregar a URL ao motor.
            import requests
            response = requests.get(local_url, timeout=5)
            response.raise_for_status()
            if len(response.content) != extractor_source.stat().st_size:
                raise RuntimeError("Fixture HTTP local retornou tamanho divergente.")

            extractor.url.setText(local_url)
            extractor.quality_buttons[-1].setChecked(True)
            extractor.start_download()
            if not wait_until(
                lambda: extractor._download_thread is None and not extractor.cancel_button.isEnabled(),
                timeout=90.0,
                interval=0.05,
            ):
                status_before_cancel = extractor.status.text()
                extractor.cancel_download()
                wait_until(lambda: extractor._download_thread is None, timeout=5.0)
                raise RuntimeError(
                    "Extrator empacotado excedeu o tempo do fluxo controlado. "
                    f"Status antes do cancelamento: {status_before_cancel}"
                )
            if "Download concluído:" not in extractor.status.text():
                raise RuntimeError(f"Extrator empacotado falhou: {extractor.status.text()}")
            extractor_outputs = list(extractor.engine.videos_dir.glob("*"))
            if not extractor_outputs or not any(p.is_file() and p.stat().st_size > 1024 for p in extractor_outputs):
                raise RuntimeError("Extrator empacotado não produziu arquivo no fluxo localhost.")
            if extractor.history.count() < 1:
                raise RuntimeError("Extrator empacotado não registrou histórico do download controlado.")
        finally:
            for key, value in saved_proxy_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=3.0)

        # DPAPI CurrentUser real dentro do runtime congelado, somente dado fictício.
        fake_secret = "SEGREDO-FICTICIO-PASSO18"
        dpapi_file = root / "temp" / "portable-dpapi-test.txt"
        dpapi = DpapiTextStore(dpapi_file)
        dpapi.save(fake_secret)
        if dpapi.load() != fake_secret:
            raise RuntimeError("DPAPI CurrentUser empacotada não recuperou o texto fictício.")
        if fake_secret in dpapi_file.read_text(encoding="utf-8"):
            raise RuntimeError("DPAPI empacotada deixou segredo fictício em texto puro.")
        dpapi.delete()

        # Proxy: preferências + senha DPAPI reais do portable; não faz chamada externa.
        proxy_root = root / "temp" / "proxy-smoke"
        proxy_prefs_file = proxy_root / "prefs" / "monitor_prefs.properties"
        proxy_prefs = SharedPreferences(proxy_prefs_file)
        proxy = ProxySettings(proxy_prefs, data_dir=proxy_root)
        proxy_cfg = proxy.save(
            enabled=True,
            host="proxy.test.local",
            port=6060,
            username="usuario-teste",
            password=fake_secret,
        )
        loaded_proxy = proxy.load()
        if not proxy_cfg.ready or loaded_proxy.password != fake_secret or loaded_proxy.host != "proxy.test.local":
            raise RuntimeError("Configuração/proteção do proxy empacotado divergiu.")
        if proxy_prefs_file.exists() and fake_secret in proxy_prefs_file.read_text(encoding="utf-8"):
            raise RuntimeError("Senha fictícia do proxy apareceu em SharedPreferences plaintext.")
        proxy.secret_store.delete()

        # Startup: usa o EXE portable real; restaura qualquer valor anterior do runner.
        previous_exists = False
        previous_value = None
        previous_type = None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
                previous_value, previous_type = winreg.QueryValueEx(key, VALUE_NAME)
                previous_exists = True
        except FileNotFoundError:
            pass
        startup = StartupManager.default()
        try:
            if not startup.configure(True, executable=Path(sys.executable)):
                raise RuntimeError("StartupManager empacotado recusou ativação.")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
                current_value, current_type = winreg.QueryValueEx(key, VALUE_NAME)
            if current_type != winreg.REG_SZ or current_value != startup_command(Path(sys.executable)):
                raise RuntimeError(f"Startup empacotado gravou valor inesperado: {current_value!r}")
            if not startup.configure(False):
                raise RuntimeError("StartupManager empacotado recusou remoção.")
        finally:
            if previous_exists:
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, VALUE_NAME, 0, previous_type, previous_value)
            else:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass

        # Pipelines controlados reais (UI controller -> runner -> repository -> SQLite -> UI state).
        pipeline_root = root / "temp" / "pipeline-smoke"
        pipeline_paths = AppPaths(pipeline_root)
        pipeline_paths.ensure_runtime_dirs()
        pipeline_prefs = SharedPreferences(pipeline_paths.data / "prefs" / "monitor_prefs.properties")

        class FakeGoogle:
            def collect(self, query):
                published_at = int(time.time() * 1000) - 1000
                return [News(
                    title=portable_news_title,
                    source="Fonte Teste",
                    date=published_at,
                    link=portable_news_link,
                    snippet="Operação da Marinha",
                    capturedAt=published_at,
                )]

        class FakeLatest:
            pass

        class NoopVideoRunner:
            def search_videos(self, **kwargs):
                raise AssertionError("vídeo não deve executar no pipeline de notícias")

        notification_events: list[tuple[str, str]] = []

        def portable_notify(title: str, body: str) -> None:
            notification_events.append((title, body))
            main.notifier(title, body)

        news_db = NewsDb(pipeline_paths.news_db)
        video_db = VideoDb(pipeline_paths.videos_db)
        for term in news_db.listTerms():
            news_db.removeTerm(term)
        news_db.addTerm("MARINHA")
        news_repo = NewsRepository(
            news_db,
            google=FakeGoogle(),
            latest=FakeLatest(),
            national_sources=(),
        )
        news_runner = RuntimeNewsRunner(news_repo, pipeline_prefs, ())
        news_service = AutomationService(
            AutomationSettings(pipeline_prefs),
            news_runner,
            NoopVideoRunner(),
            notify=portable_notify,
        )
        news_terms = VideoTermStore(pipeline_prefs)
        news_controller = RuntimeUiController(
            paths=pipeline_paths,
            prefs=pipeline_prefs,
            news_db=news_db,
            video_db=video_db,
            proxy=FakeProxy(),
            startup=FakeStartup(),
            automation=news_service,
            news_sources=(),
            video_sources=(),
            specialized_sources=(),
            default_video_source_ids=set(),
            video_term_store=news_terms,
        )
        news_controller.add_term("TERMO PORTABLE PERSISTENTE")
        news_controller.add_demand("VEICULO TESTE", "MARINHA")
        news_controller.selected_news_source_ids = {"fonte-teste"}
        if not news_controller.search_news():
            raise RuntimeError("Controller portable recusou pipeline de notícias controlado.")
        wait_automation_idle(news_service, "newsBusy")
        news_controller.sync_automation_state()
        stored_news = news_db.listNews(10)
        if not stored_news or stored_news[0].matchedTerm != "MARINHA":
            raise RuntimeError("Pipeline de notícias não persistiu matching no SQLite.")
        if not news_controller.state.news or news_controller.state.news[0].link != portable_news_link:
            raise RuntimeError("Pipeline de notícias não retornou resultado ao estado da UI.")
        if not notification_events:
            raise RuntimeError("Evento de notícia nova não acionou callback de notificação.")
        news_controller.close()

        reopened_news_db = NewsDb(pipeline_paths.news_db)
        reopened_news_prefs = SharedPreferences(pipeline_paths.data / "prefs" / "monitor_prefs.properties")
        if "TERMO PORTABLE PERSISTENTE" not in reopened_news_db.listTerms():
            raise RuntimeError("Termo de teste não persistiu após reabrir.")
        if not any(d.vehicle == "VEICULO TESTE" and d.subject == "MARINHA" for d in reopened_news_db.listDemands()):
            raise RuntimeError("Demanda de teste não persistiu após reabrir.")
        if reopened_news_prefs.get_string_set("desktop_news_source_ids", set()) != {"fonte-teste"}:
            raise RuntimeError("Seleção de fonte de notícias não persistiu após reabrir.")
        if not reopened_news_db.listNews(10):
            raise RuntimeError("Histórico de notícias não persistiu após reabrir.")
        reopened_news_db.close()

        class FakeWebsite:
            def fetch_search_website(self, source, query, captured_at):
                return [VideoItem(
                    title="Marinha realiza exercício naval",
                    sourceId=source.id,
                    sourceName=source.name,
                    publishedAt=captured_at,
                    link="https://www.cnnbrasil.com.br/videos/marinha-exercicio",
                    summary="Operação da Marinha",
                    capturedAt=captured_at,
                )]
            def fetch_website(self, source, captured_at):
                return []

        class FakeDirect:
            def resolve(self, source, item, captured_at):
                return item

        class NeverUsed:
            def __getattr__(self, name):
                raise AssertionError(f"collector inesperado: {name}")

        class NoopNewsRunner:
            def search_news(self, **kwargs):
                raise AssertionError("notícias não devem executar no pipeline de vídeos")
            def search_demand(self, *args, **kwargs):
                raise AssertionError
            def search_all_demands(self, **kwargs):
                raise AssertionError

        video_news_db = NewsDb(pipeline_paths.news_db)
        video_db2 = VideoDb(pipeline_paths.videos_db)
        video_terms = VideoTermStore(pipeline_prefs)
        video_terms.save(["MARINHA"])
        pipeline_prefs.update(
            desktop_video_source_ids={"video-cnn-brasil"},
            desktop_video_sources_v6_migrated=True,
        )
        video_repo = VideoRepository(
            video_news_db,
            video_db2,
            video_terms,
            youtube=NeverUsed(),
            website=FakeWebsite(),
            direct=FakeDirect(),
            editions=NeverUsed(),
            trechos=NeverUsed(),
            jarvis=NeverUsed(),
        )
        video_runner = RuntimeVideoRunner(video_repo, pipeline_prefs)
        video_service = AutomationService(
            AutomationSettings(pipeline_prefs),
            NoopNewsRunner(),
            video_runner,
            notify=portable_notify,
        )
        video_controller = RuntimeUiController(
            paths=pipeline_paths,
            prefs=pipeline_prefs,
            news_db=video_news_db,
            video_db=video_db2,
            proxy=FakeProxy(),
            startup=FakeStartup(),
            automation=video_service,
            news_sources=(),
            video_sources=(),
            specialized_sources=(),
            default_video_source_ids={"video-cnn-brasil"},
            video_term_store=video_terms,
        )
        if not video_controller.search_videos():
            raise RuntimeError("Controller portable recusou pipeline de vídeos controlado.")
        wait_automation_idle(video_service, "videoBusy")
        video_controller.sync_automation_state()
        stored_videos = video_db2.listAll(10)
        if not stored_videos or stored_videos[0].matchedTerm != "MARINHA":
            raise RuntimeError("Pipeline de vídeos não persistiu matching no SQLite.")
        if not video_controller.state.videos or not video_controller.state.videos[0].link.endswith("/videos/marinha-exercicio"):
            raise RuntimeError("Pipeline de vídeos não retornou resultado ao estado da UI.")
        video_controller.close()

        reopened_video_db = VideoDb(pipeline_paths.videos_db)
        if not reopened_video_db.listAll(10):
            raise RuntimeError("Histórico de vídeos não persistiu após reabrir.")
        reopened_video_db.close()
        reopened_video_terms = VideoTermStore(
            SharedPreferences(pipeline_paths.data / "prefs" / "monitor_prefs.properties")
        ).load(["OUTRO"])
        if "MARINHA" not in reopened_video_terms or "OUTRO" in reopened_video_terms:
            raise RuntimeError("Termo independente de vídeo não persistiu após reabrir.")
        if SharedPreferences(pipeline_paths.data / "prefs" / "monitor_prefs.properties").get_string_set(
            "desktop_video_source_ids", set()
        ) != {"video-cnn-brasil"}:
            raise RuntimeError("Seleção de fonte de vídeo não persistiu após reabrir.")

        # Disparo automático controlado pelo mesmo AutomationService.
        auto_root = root / "temp" / "automation-smoke"
        auto_paths = AppPaths(auto_root)
        auto_paths.ensure_runtime_dirs()
        auto_prefs = SharedPreferences(auto_paths.data / "prefs" / "monitor_prefs.properties")
        auto_db = NewsDb(auto_paths.news_db)
        for term in auto_db.listTerms():
            auto_db.removeTerm(term)
        auto_db.addTerm("MARINHA")
        now_ms = int(time.time() * 1000)
        auto_prefs.update(
            desktop_automatic_monitoring=True,
            desktop_news_automatic=True,
            desktop_demand_automatic=False,
            desktop_video_automatic=False,
            desktop_auto_news_at=0,
        )

        class FakeClock:
            def __init__(self, value):
                self.value = value
            def now_ms(self):
                return self.value
            def local_datetime(self):
                return datetime.fromtimestamp(self.value / 1000)

        class AutoGoogle:
            def collect(self, query):
                return [News(
                    title="Marinha em operação automática",
                    source="Fonte Auto",
                    date=now_ms,
                    link="https://example.test/portable-auto",
                    snippet="Marinha",
                    capturedAt=now_ms,
                )]

        auto_repo = NewsRepository(
            auto_db,
            google=AutoGoogle(),
            latest=FakeLatest(),
            national_sources=(),
        )
        auto_runner = RuntimeNewsRunner(auto_repo, auto_prefs, ())
        auto_service = AutomationService(
            AutomationSettings(auto_prefs),
            auto_runner,
            NoopVideoRunner(),
            clock=FakeClock(now_ms),
            notify=portable_notify,
        )
        auto_service.tick()
        wait_automation_idle(auto_service, "newsBusy")
        if not auto_db.listNews(10) or auto_db.listNews(10)[0].link != "https://example.test/portable-auto":
            raise RuntimeError("AutomationService automático não percorreu pipeline real controlado.")
        if auto_service.settings.last_news_auto_at != now_ms:
            raise RuntimeError("AutomationService não persistiu timestamp do disparo automático.")
        auto_service.close()
        auto_db.close()

        # Teardown real das ferramentas integradas, inclusive liberação do handle.
        if not video_page.shutdown():
            raise RuntimeError("Shutdown do Editor de Vídeo empacotado falhou.")
        if not extractor.shutdown():
            raise RuntimeError("Shutdown do Extrator empacotado falhou.")
        editor.player.setSource(QUrl())
        for _ in range(5):
            app.processEvents()
            time.sleep(0.02)
        source.unlink()
        if source.exists():
            raise RuntimeError("QMediaPlayer empacotado manteve handle da mídia.")

        main._allow_close = True
        main._timer.stop()
        main.controller.close()
        main.tray.hide()
        main.close()
        app.processEvents()

        # Reabre dados da raiz principal e comprova persistência de preferências/banco.
        main_db_check = NewsDb(paths.news_db)
        if persist_term not in main_db_check.listTerms():
            raise RuntimeError("Termo da raiz portable não persistiu após fechar o MainWindow.")
        if not any(
            d.vehicle == persist_vehicle and d.subject == persist_subject
            for d in main_db_check.listDemands()
        ):
            raise RuntimeError("Demanda da raiz portable não persistiu após fechar o MainWindow.")
        main_db_check.close()
        main_prefs_check = SharedPreferences(paths.data / "prefs" / "monitor_prefs.properties")
        if main_prefs_check.get_string_set("desktop_news_source_ids", set()) != {"fonte-teste"}:
            raise RuntimeError("Fonte de notícias da raiz portable não persistiu.")
        if main_prefs_check.get_string_set("desktop_video_source_ids", set()) != {"video-cnn-brasil"}:
            raise RuntimeError("Fonte de vídeos da raiz portable não persistiu.")

        payload.update({
            "ok": True,
            "navigated": navigated,
            "pdf": str(pdf_output),
            "pdf_pages": 2,
            "player_position_ms": max_position,
            "seek_positions_ms": seek_positions,
            "video_codec": exported_info.video_codec,
            "audio_codec": exported_info.audio_codec,
            "resolution": f"{exported_info.width}x{exported_info.height}",
            "fps": exported_info.fps,
            "export_duration": export_duration,
            "audio_sample_rate": int(export_audio.get("sample_rate", "0")),
            "audio_channels": int(export_audio.get("channels", 0)),
            "binaries": binaries,
            "extractor_controlled": True,
            "news_pipeline": True,
            "video_pipeline": True,
            "automation_pipeline": True,
            "persistence": True,
            "history": True,
            "dpapi": True,
            "proxy_dpapi": True,
            "startup_registry": True,
            "notification_event": bool(notification_events),
            "notification_wiring": True,
            "notification_fixture_link": portable_news_link,
            "notification_fixture_title": portable_news_title,
            "manual_video_in_out_ui": "NAO_APLICAVEL_BASELINE",
            "video_delete_reorder_ui": "NAO_APLICAVEL_BASELINE",
        })
        result_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os._exit(0)
    except BaseException as exc:
        payload.update({"ok": False, "error": str(exc), "traceback": traceback.format_exc()})
        try:
            result_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        finally:
            os._exit(91)
