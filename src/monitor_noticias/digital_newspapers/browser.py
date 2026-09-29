from __future__ import annotations

import base64
from datetime import date
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse

import requests

from PySide6.QtCore import (
    QDateTime,
    QByteArray,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.capas_tool.app import network as covers_network
from monitor_noticias.digital_newspapers.providers import DigitalNewspaperProvider
from monitor_noticias.digital_newspapers.pressreader_hd import (
    PressReaderHdPdfThread,
    pressreader_image_candidate_score,
)
from monitor_noticias.digital_newspapers.storage import (
    SecureCredentialStore,
    SecureSessionStore,
)
from monitor_noticias.digital_newspapers.validation import (
    normalized_text as _normalized_text,
    validate_full_edition_pdf,
)
from monitor_noticias.networking.proxy import (
    ProxySettings,
    corporate_tls_compatibility,
)


class DigitalNewspaperPage(QWebEnginePage):
    """Mantém popups/login dentro do mesmo navegador da Central."""

    def createWindow(self, _window_type):  # noqa: N802
        return self


class DigitalNewspaperRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Observa recursos do viewer sem modificar as requisições."""

    resource_seen = Signal(str)

    def interceptRequest(self, info) -> None:  # noqa: N802
        try:
            url = info.requestUrl().toString()
        except Exception:
            return
        low = url.lower()
        if "prcdn.co" in low or "pressreader" in low or "newspaperdirect" in low:
            self.resource_seen.emit(url)


DOWNLOAD_PROBE_JS = r"""
(function(){
  function norm(v){
    return String(v || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim();
  }

  function cleanUrl(v){
    try{
      var u = new URL(String(v || ''), document.baseURI);
      if(u.protocol !== 'http:' && u.protocol !== 'https:') return '';
      return u.href;
    }catch(e){
      return '';
    }
  }

  var here = norm(location.href || '');
  var password = document.querySelector('input[type="password"]');
  if(password || /(?:^|[\/?#&=_-])(login|signin|sign-in|auth)(?:$|[\/?#&=_-])/.test(here)){
    return JSON.stringify({ok:false, reason:'login_required'});
  }

  var phrases = [
    'baixar pdf', 'download pdf', 'baixar edicao', 'baixar edição',
    'download edition', 'download edicao', 'download edição',
    'edicao pdf', 'edição pdf', 'jornal em pdf', 'full edition pdf',
    'edition pdf', 'edicao completa', 'edição completa', 'full edition',
    'replica edition', 'print edition', 'jornal digital', 'edicao digital',
    'edição digital', 'ler edicao', 'ler edição', 'read edition', 'epaper'
  ];
  var urlHints = [
    'edition', 'edicao', 'edicao-digital', 'digital', 'epaper', 'e-paper',
    'viewer', 'flip', 'replica', 'jornal-digital', 'gazeta-revista',
    'newspaper', 'pressreader', 'acervo', 'zero-hora', 'o-estado-de-s-paulo'
  ];
  var rejectHints = [
    'politica', 'policy', 'privacy', 'privacidade', 'termos', 'terms',
    'anticorrup', 'compliance', 'boleto', 'invoice', 'receipt', 'comprovante',
    'contrato', 'regulamento', 'faq', 'media-kit', 'midiakit'
  ];

  var ranked = [];
  var nodes = Array.prototype.slice.call(document.querySelectorAll(
    'a[href], button, [role="button"], [download], input[type="button"], input[type="submit"]'
  ));

  for(var i=0;i<nodes.length;i++){
    var n = nodes[i];
    var label = norm(
      (n.innerText || '') + ' ' + (n.textContent || '') + ' ' +
      (n.value || '') + ' ' + (n.getAttribute('aria-label') || '') + ' ' +
      (n.getAttribute('title') || '')
    );
    var href = cleanUrl(n.href || n.getAttribute('href') || '');
    var lowHref = norm(href);
    var combined = label + ' ' + lowHref;
    var score = 0;

    // Um .pdf genérico NÃO é mais suficiente para ser considerado edição.
    if(href && /\.pdf(?:$|[?#])/i.test(href)) score += 350;
    if(n.hasAttribute && n.hasAttribute('download')) score += 250;

    for(var p=0;p<phrases.length;p++){
      if(label.indexOf(phrases[p]) >= 0) score += 1650 - (p * 18);
    }
    for(var h=0;h<urlHints.length;h++){
      if(lowHref.indexOf(urlHints[h]) >= 0) score += 650 - (h * 10);
    }
    for(var r=0;r<rejectHints.length;r++){
      if(combined.indexOf(rejectHints[r]) >= 0) score -= 7000;
    }

    if(label.indexOf('assine') >= 0 || label.indexOf('subscribe') >= 0) score -= 1200;
    if(label.indexOf('pagina') >= 0 || label.indexOf('página') >= 0 || label.indexOf('single page') >= 0) score -= 4200;
    if(/(?:page|pagina|pag)[=_\/-]?\d+/i.test(href)) score -= 4200;

    if(score > 0){
      ranked.push({kind:'node', index:i, score:score, href:href, text:label.slice(0,240)});
    }
  }

  var frames = Array.prototype.slice.call(
    document.querySelectorAll('iframe[src], frame[src], embed[src], object[data]')
  );
  for(var j=0;j<frames.length;j++){
    var f = frames[j];
    var src = cleanUrl(f.src || f.data || f.getAttribute('src') || f.getAttribute('data') || '');
    if(!src) continue;
    var low = norm(src);
    var s = 0;
    for(var q=0;q<urlHints.length;q++){
      if(low.indexOf(urlHints[q]) >= 0) s += 900 - (q * 12);
    }
    for(var rr=0;rr<rejectHints.length;rr++){
      if(low.indexOf(rejectHints[rr]) >= 0) s -= 7000;
    }
    if(s > 0){
      ranked.push({kind:'resource', index:j, score:s, href:src, text:'viewer/frame'});
    }
  }

  ranked.sort(function(a,b){return b.score-a.score;});
  if(!ranked.length || ranked[0].score < 900){
    return JSON.stringify({ok:false, reason:'not_found', title:document.title || ''});
  }

  var best = ranked[0];
  if(best.href && /\.pdf(?:$|[?#])/i.test(best.href)){
    return JSON.stringify({ok:true, mode:'direct_pdf', href:best.href, text:best.text, score:best.score});
  }

  if(best.kind === 'resource' && best.href){
    return JSON.stringify({ok:true, mode:'navigate', href:best.href, text:best.text, score:best.score});
  }

  var node = nodes[best.index];
  if(best.href && best.score >= 1100){
    return JSON.stringify({ok:true, mode:'navigate', href:best.href, text:best.text, score:best.score});
  }

  // Não clica ainda: Python valida o candidato e só então autoriza o clique.
  try{
    node.setAttribute('data-central-edition-candidate','1');
  }catch(e){}
  return JSON.stringify({ok:true, mode:'click_candidate', href:best.href || '', text:best.text, score:best.score});
})()
"""


PRESSREADER_RESOURCES_JS = r"""
(function(){
  try{
    var resources=[],seen={};
    function add(v){try{var u=String(v||'').trim();if(!u||seen[u])return;seen[u]=1;resources.push(u);}catch(e){}}
    (performance.getEntriesByType('resource')||[]).forEach(function(e){add(e.name);});
    Array.from(document.images||[]).forEach(function(img){
      add(img.currentSrc);add(img.src);
      String(img.srcset||'').split(',').forEach(function(part){add(part.trim().split(/\s+/)[0]);});
    });
    Array.from(document.querySelectorAll('source[src],source[srcset]')).forEach(function(n){
      add(n.src);String(n.srcset||'').split(',').forEach(function(part){add(part.trim().split(/\s+/)[0]);});
    });
    return JSON.stringify({href:location.href||'',title:document.title||'',hasPassword:!!document.querySelector('input[type="password"]'),resources:resources});
  }catch(e){return JSON.stringify({href:location.href||'',title:document.title||'',hasPassword:false,resources:[]});}
})()
"""



def _output_target(
    paths: AppPaths,
    provider: DigitalNewspaperProvider,
    target_date: date,
) -> Path:
    output_dir = (
        Path(paths.state_root)
        / "JornaisDigitais"
        / provider.id
        / target_date.isoformat()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / provider.output_filename(target_date)


class DirectPdfDownloadThread(QThread):
    """Baixa um PDF oficial conhecido sem abrir janela/navegador visível."""

    status_changed = Signal(str)
    completed = Signal(str, int, str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        paths: AppPaths,
        provider: DigitalNewspaperProvider,
        target_date: date,
        url: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.provider = provider
        self.target_date = target_date
        self.url = str(url)

    def _proxy_settings(self) -> tuple[ProxySettings, object]:
        prefs = SharedPreferences(
            self.paths.data
            / "prefs"
            / "monitor_prefs.properties"
        )
        settings = ProxySettings(
            prefs,
            data_dir=self.paths.data,
        )
        return settings, settings.load()

    def _restore_requests_cookies(
        self,
        session: requests.Session,
    ) -> None:
        vault = SecureSessionStore(
            self.paths,
            self.provider.id,
        )
        rows = vault.load_json(default=[])
        if not isinstance(rows, list):
            return

        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                name = str(item.get("name") or "")
                domain = str(item.get("domain") or "").lstrip(".")
                path = str(item.get("path") or "/")
                if not name or not self.provider.domain_allowed(domain):
                    continue
                value = base64.b64decode(
                    str(item.get("value") or ""),
                    validate=False,
                ).decode("utf-8", "ignore")
                session.cookies.set(
                    name,
                    value,
                    domain=domain,
                    path=path,
                )
            except Exception:
                continue

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/151 Safari/537.36"
            ),
            "Accept": "application/pdf,*/*;q=0.8",
            "Referer": self.provider.edition_url,
        }

    def _http_get(
        self,
        session: requests.Session,
        url: str,
        *,
        proxies,
        verify,
        stream: bool = True,
    ) -> requests.Response:
        return session.get(
            url,
            headers=self._headers(),
            stream=stream,
            allow_redirects=True,
            timeout=(15, 180),
            proxies=proxies,
            verify=verify,
        )

    def _download_response_to_file(
        self,
        response: requests.Response,
        target: Path,
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.unlink()
        except FileNotFoundError:
            pass

        received = 0
        with response:
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if self.isInterruptionRequested():
                        raise RuntimeError("Download cancelado.")
                    if not chunk:
                        continue
                    handle.write(chunk)
                    received += len(chunk)
                    if received and received % (5 * 1024 * 1024) < len(chunk):
                        self.status_changed.emit(
                            f"{self.provider.name}: {received / (1024 * 1024):.1f} MB recebidos…"
                        )

    def _validate_pdf(
        self,
        path: Path,
        *,
        full_edition: bool = True,
    ) -> int:
        if full_edition:
            return validate_full_edition_pdf(path, self.provider)

        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise RuntimeError("PDF de página inválido.")
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(path)).pages)
        except Exception as exc:
            raise RuntimeError("PDF de página inválido.") from exc
        if pages <= 0:
            raise RuntimeError("PDF de página vazio.")
        return pages

    def _emit_pagewise_fallback(
        self,
        message: str,
    ) -> None:
        self.status_changed.emit(
            f"{self.provider.name}: {message} Tentando o PDF integral oficial…"
        )

    def _try_pagewise_pdf_build(
        self,
        session: requests.Session,
        *,
        proxies,
        verify,
        target: Path,
    ) -> tuple[int, str] | None:
        if not self.provider.supports_pagewise_pdf:
            return None

        from pypdf import PdfReader, PdfWriter

        temp_dir = target.parent / "_tmp_paginas"
        shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        page_files: list[tuple[int, Path]] = []
        misses = 0

        try:
            self.status_changed.emit(
                f"{self.provider.name}: tentando remontar a edição página a página…"
            )

            for page_number in range(1, self.provider.pagewise_max_pages + 1):
                if self.isInterruptionRequested():
                    raise RuntimeError("Download cancelado.")

                downloaded_file: Path | None = None

                for url in self.provider.page_pdf_urls(self.target_date, page_number):
                    response = self._http_get(
                        session,
                        url,
                        proxies=proxies,
                        verify=verify,
                        stream=True,
                    )

                    if response.status_code in {401, 403}:
                        response.close()
                        self._emit_pagewise_fallback(
                            "as páginas individuais exigem autenticação"
                        )
                        return None

                    if response.status_code == 404:
                        response.close()
                        continue

                    if response.status_code < 200 or response.status_code >= 300:
                        response.close()
                        continue

                    candidate = temp_dir / f"{page_number:03d}.pdf"
                    try:
                        self._download_response_to_file(response, candidate)
                        page_count = self._validate_pdf(candidate, full_edition=False)
                        if page_count <= 0:
                            raise RuntimeError("Página vazia.")
                        downloaded_file = candidate
                        break
                    except Exception:
                        try:
                            candidate.unlink()
                        except Exception:
                            pass
                        continue

                if downloaded_file is not None:
                    page_files.append((page_number, downloaded_file))
                    misses = 0
                    self.status_changed.emit(
                        f"{self.provider.name}: página {page_number:02d} localizada…"
                    )
                    continue

                misses += 1
                if page_files and misses >= self.provider.pagewise_stop_after_misses:
                    break

            if len(page_files) < max(1, self.provider.pagewise_min_pages):
                if page_files:
                    self._emit_pagewise_fallback(
                        "a quantidade de páginas individuais válidas foi insuficiente"
                    )
                return None

            discovered = [page for page, _ in page_files]
            existing = set(discovered)
            gaps = [
                number
                for number in range(discovered[0], discovered[-1] + 1)
                if number not in existing
            ]
            if gaps:
                shown = ", ".join(str(x) for x in gaps[:8])
                if len(gaps) > 8:
                    shown += ", …"
                self._emit_pagewise_fallback(
                    f"faltaram páginas na sequência ({shown})"
                )
                return None

            writer = PdfWriter()
            total_pages = 0
            for _page_number, pdf_path in page_files:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1

            part = target.with_suffix(target.suffix + ".part")
            try:
                part.unlink()
            except FileNotFoundError:
                pass

            with part.open("wb") as handle:
                writer.write(handle)

            total_pages = self._validate_pdf(part)

            try:
                target.unlink()
            except FileNotFoundError:
                pass

            part.replace(target)
            return total_pages, "PDF oficial remontado página a página"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _download_integral_pdf(
        self,
        session: requests.Session,
        *,
        proxies,
        verify,
        target: Path,
    ) -> tuple[int, str]:
        part = target.with_suffix(target.suffix + ".part")

        response = self._http_get(
            session,
            self.url,
            proxies=proxies,
            verify=verify,
            stream=True,
        )

        if response.status_code in {401, 403}:
            response.close()
            raise RuntimeError(
                "Autenticação necessária. Use “Entrar / renovar sessão” uma vez e tente novamente."
            )

        if response.status_code == 404:
            response.close()
            raise RuntimeError(
                "A edição desta data ainda não está disponível no servidor oficial."
            )

        if response.status_code < 200 or response.status_code >= 300:
            response.close()
            raise RuntimeError(
                f"O servidor do jornal respondeu HTTP {response.status_code}."
            )

        self.status_changed.emit(
            f"{self.provider.name}: baixando o PDF integral oficial…"
        )
        self._download_response_to_file(response, part)
        pages = self._validate_pdf(part)

        try:
            target.unlink()
        except FileNotFoundError:
            pass

        part.replace(target)
        return pages, "PDF oficial direto"

    def run(self) -> None:
        target = _output_target(
            self.paths,
            self.provider,
            self.target_date,
        )
        part = target.with_suffix(target.suffix + ".part")

        try:
            settings, config = self._proxy_settings()
            proxies = settings.requests_proxies(config)
            verify = settings.requests_verify(config)

            with requests.Session() as session:
                session.trust_env = False
                self._restore_requests_cookies(session)

                self.status_changed.emit(
                    f"{self.provider.name}: baixando a edição de "
                    f"{self.target_date.strftime('%d/%m/%Y')} em segundo plano…"
                )

                pagewise = self._try_pagewise_pdf_build(
                    session,
                    proxies=proxies,
                    verify=verify,
                    target=target,
                )
                if pagewise is not None:
                    pages, method = pagewise
                    self.completed.emit(
                        str(target),
                        pages,
                        method,
                    )
                    return

                pages, method = self._download_integral_pdf(
                    session,
                    proxies=proxies,
                    verify=verify,
                    target=target,
                )

            self.completed.emit(
                str(target),
                pages,
                method,
            )

        except Exception as exc:
            try:
                part.unlink()
            except Exception:
                pass
            self.failed.emit(str(exc) or exc.__class__.__name__)


class DigitalNewspaperBrowserDialog(QDialog):
    """Sessão WebEngine dos jornais.

    Na V78 o diálogo NÃO é exibido no fluxo normal. O clique no jornal tenta o
    PDF automaticamente em segundo plano. Esta janela só é mostrada quando o
    usuário escolhe explicitamente “Entrar / renovar sessão”.
    """

    status_changed = Signal(str)
    session_changed = Signal(bool)
    pdf_completed = Signal(str, int, str)

    def __init__(
        self,
        *,
        paths: AppPaths,
        provider: DigitalNewspaperProvider,
        target_date: date,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.provider = provider
        self.target_date = target_date
        self.session_store = SecureSessionStore(
            paths,
            provider.id,
        )
        self.credential_store = SecureCredentialStore(
            paths,
            provider.id,
        )
        self._cookies: dict[str, dict] = {}
        self._cookie_save_timer = QTimer(self)
        self._cookie_save_timer.setSingleShot(True)
        self._cookie_save_timer.setInterval(900)
        self._cookie_save_timer.timeout.connect(
            self._save_cookie_vault
        )
        self._download_in_progress = False
        self._pending_method = "Download autorizado"
        self._auto_download_requested = False
        self._auto_download_active = False
        self._auto_entry_urls: tuple[str, ...] = ()
        self._auto_entry_index = -1
        self._auto_seen_urls: set[str] = set()
        self._auto_probe_attempts = 0
        self._auto_navigation_depth = 0
        self._auto_login_seen = False
        self._edition_download_armed = False
        self._download_origin_auto = False
        self._direct_thread: DirectPdfDownloadThread | None = None
        self._pressreader_thread: PressReaderHdPdfThread | None = None
        self._valor_hd_active = False
        self._valor_page_number = 0
        self._valor_image_urls: dict[int, str] = {}
        self._valor_probe_attempts = 0
        self._valor_reload_attempts = 0
        self._valor_intercepted_best_url = ""
        self._valor_intercepted_best_score = -1

        self.setWindowTitle(
            f"Entrar / renovar sessão • {provider.name}"
        )
        self.resize(1320, 860)
        self.setMinimumSize(980, 650)

        self._build_browser()
        self._build_ui()
        self._restore_cookie_vault()

    def _build_browser(self) -> None:
        try:
            covers_network.refresh_central_proxy()
        except Exception:
            pass

        self.profile = QWebEngineProfile(self)
        self._request_interceptor = DigitalNewspaperRequestInterceptor(self)
        self._request_interceptor.resource_seen.connect(self._request_resource_seen)
        try:
            self.profile.setUrlRequestInterceptor(self._request_interceptor)
        except Exception:
            pass
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 CentralInteligenteDeMidia/4.0.2"
        )

        try:
            self.profile.setHttpCacheType(
                QWebEngineProfile.HttpCacheType.MemoryHttpCache
            )
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
            )
        except Exception:
            pass

        self.cookie_store = self.profile.cookieStore()
        self.cookie_store.cookieAdded.connect(
            self._cookie_added
        )
        self.cookie_store.cookieRemoved.connect(
            self._cookie_removed
        )

        self.profile.downloadRequested.connect(
            self._download_requested
        )

        self.page = DigitalNewspaperPage(
            self.profile,
            self,
        )

        try:
            self.page.proxyAuthenticationRequired.connect(
                self._proxy_authentication_required
            )
        except Exception:
            pass

        try:
            self.page.certificateError.connect(
                self._certificate_error
            )
        except Exception:
            pass

        settings = self.page.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            True,
        )

        self.view = QWebEngineView(self)
        self.view.setPage(self.page)
        self.view.urlChanged.connect(
            lambda url: self.address.setText(url.toString())
            if hasattr(self, "address")
            else None
        )
        self.view.loadStarted.connect(
            lambda: self._emit_status("Abrindo serviço do jornal…")
        )
        self.view.loadFinished.connect(
            self._load_finished
        )

    def _request_resource_seen(self, raw_url: str) -> None:
        if not self._valor_hd_active:
            return
        score = pressreader_image_candidate_score(
            raw_url, expected_page=self._valor_page_number
        )
        if score is None or score <= self._valor_intercepted_best_score:
            return
        self._valor_intercepted_best_score = score
        self._valor_intercepted_best_url = str(raw_url or "")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        back = QPushButton("←")
        back.setFixedWidth(42)
        back.clicked.connect(self.view.back)
        toolbar.addWidget(back)

        forward = QPushButton("→")
        forward.setFixedWidth(42)
        forward.clicked.connect(self.view.forward)
        toolbar.addWidget(forward)

        reload_button = QPushButton("↻")
        reload_button.setFixedWidth(42)
        reload_button.clicked.connect(self.view.reload)
        toolbar.addWidget(reload_button)

        self.address = QLineEdit()
        self.address.setReadOnly(True)
        toolbar.addWidget(self.address, 1)

        self.download_button = QPushButton(
            "Baixar edição completa"
        )
        self.download_button.clicked.connect(
            self.start_automatic_download
        )
        self.download_button.setEnabled(
            self.provider.can_try_download
        )
        toolbar.addWidget(self.download_button)

        root.addLayout(toolbar)

        self.info = QLabel(
            "Esta tela existe somente para autenticação quando a sessão expirar. "
            "No uso normal, selecione o jornal na aba Jornais Digitais e clique em "
            "“Iniciar busca / baixar edição”. Se você optar por salvar o acesso, "
            "a senha fica criptografada somente neste computador."
        )
        self.info.setWordWrap(True)
        self.info.setObjectName("digitalBrowserInfo")
        root.addWidget(self.info)

        root.addWidget(self.view, 1)

        self.status = QLabel("Pronto")
        self.status.setWordWrap(True)
        self.status.setObjectName("digitalBrowserStatus")
        root.addWidget(self.status)

        self.setStyleSheet(
            """
            QDialog { background:#F4F9FF; }
            QLineEdit {
                background:white;
                color:#08245F;
                border:1px solid #C9DDF5;
                border-radius:8px;
                padding:8px 10px;
            }
            QPushButton {
                background:#087AF7;
                color:white;
                border:0;
                border-radius:8px;
                padding:8px 12px;
                font-weight:800;
            }
            QPushButton:disabled {
                background:#C8D6E8;
                color:#F5F7FA;
            }
            QLabel#digitalBrowserInfo {
                color:#526E9B;
                background:#EDF6FF;
                border:1px solid #D1E5F8;
                border-radius:8px;
                padding:8px 10px;
            }
            QLabel#digitalBrowserStatus {
                color:#087A59;
                background:#EAF9F2;
                border:1px solid #BFE8D5;
                border-radius:8px;
                padding:7px 10px;
                font-weight:700;
            }
            """
        )

    def _certificate_error(self, error) -> None:
        """V69 preservada também no Chromium dos Jornais Digitais."""
        try:
            config = covers_network.central_proxy_config()
            if corporate_tls_compatibility(config):
                error.acceptCertificate()
                self._emit_status(
                    "Compatibilidade SSL corporativa ativa somente para "
                    f"{config.host}:{config.port}."
                )
                return
        except Exception:
            pass

        try:
            error.rejectCertificate()
        except Exception:
            pass

    def _proxy_authentication_required(
        self,
        _request_url,
        authenticator,
        _proxy_host,
    ) -> None:
        try:
            config = covers_network.central_proxy_config()
            if config.enabled and config.ready:
                authenticator.setUser(config.username)
                authenticator.setPassword(config.password)
        except Exception:
            pass

    def _cookie_key(self, item: dict) -> str:
        return "|".join(
            (
                str(item.get("domain") or ""),
                str(item.get("path") or "/"),
                str(item.get("name") or ""),
            )
        )

    def _cookie_to_dict(self, cookie: QNetworkCookie) -> dict | None:
        try:
            domain = str(cookie.domain() or "").strip()
            if not domain or not self.provider.domain_allowed(domain):
                return None

            expiration = cookie.expirationDate()
            expires = (
                int(expiration.toSecsSinceEpoch())
                if expiration.isValid()
                else 0
            )

            return {
                "name": bytes(cookie.name()).decode("utf-8", "ignore"),
                "value": base64.b64encode(bytes(cookie.value())).decode("ascii"),
                "domain": domain,
                "path": str(cookie.path() or "/"),
                "secure": bool(cookie.isSecure()),
                "http_only": bool(cookie.isHttpOnly()),
                "expires": expires,
            }
        except Exception:
            return None

    def _dict_to_cookie(self, item: dict) -> QNetworkCookie | None:
        try:
            name = str(item.get("name") or "")
            if not name:
                return None
            domain = str(item.get("domain") or "")
            if not self.provider.domain_allowed(domain):
                return None

            value = base64.b64decode(
                str(item.get("value") or ""),
                validate=False,
            )
            cookie = QNetworkCookie(
                QByteArray(name.encode("utf-8")),
                QByteArray(value),
            )
            cookie.setDomain(domain)
            cookie.setPath(str(item.get("path") or "/"))
            cookie.setSecure(bool(item.get("secure")))
            cookie.setHttpOnly(bool(item.get("http_only")))

            expires = int(item.get("expires") or 0)
            if expires > 0:
                cookie.setExpirationDate(
                    QDateTime.fromSecsSinceEpoch(expires)
                )
            return cookie
        except Exception:
            return None

    def _cookie_added(self, cookie: QNetworkCookie) -> None:
        item = self._cookie_to_dict(cookie)
        if item is None:
            return
        self._cookies[self._cookie_key(item)] = item
        self._cookie_save_timer.start()
        self.session_changed.emit(True)

    def _cookie_removed(self, cookie: QNetworkCookie) -> None:
        item = self._cookie_to_dict(cookie)
        if item is None:
            return
        self._cookies.pop(self._cookie_key(item), None)
        self._cookie_save_timer.start()

    def _restore_cookie_vault(self) -> None:
        rows = self.session_store.load_json(default=[])
        if not isinstance(rows, list):
            return

        restored = 0
        for item in rows:
            if not isinstance(item, dict):
                continue
            cookie = self._dict_to_cookie(item)
            if cookie is None:
                continue

            key = self._cookie_key(item)
            self._cookies[key] = item

            domain = str(item.get("domain") or "").lstrip(".")
            origin = QUrl(f"https://{domain}/")
            try:
                self.cookie_store.setCookie(cookie, origin)
                restored += 1
            except Exception:
                pass

        if restored:
            self.session_changed.emit(True)

    def _save_cookie_vault(self) -> None:
        if not self._cookies:
            self.session_store.clear()
            self.session_changed.emit(False)
            return

        try:
            self.session_store.save_json(
                list(self._cookies.values())
            )
            self.session_changed.emit(True)
        except Exception:
            self._emit_status(
                "Sessão mantida somente em memória: o cofre seguro não está disponível."
            )

    def clear_session(self) -> None:
        self._cookies.clear()
        try:
            self.cookie_store.deleteAllCookies()
        except Exception:
            pass
        self.session_store.clear()
        self.session_changed.emit(False)
        self._emit_status("Sessão local removida.")

    def has_saved_session(self) -> bool:
        return bool(
            self._cookies
            or self.session_store.exists()
        )

    def set_target_date(self, target_date: date) -> None:
        self.target_date = target_date

    def open_edition(self) -> None:
        urls = self.provider.edition_urls(self.target_date)
        target = urls[0] if urls else self.provider.edition_url
        self.view.load(QUrl(target))

    def prepare_manual_login(self) -> None:
        self._valor_hd_active = False
        self._auto_download_requested = False
        self._auto_download_active = False
        self._auto_entry_urls = ()
        self._auto_entry_index = -1
        self.download_button.setEnabled(self.provider.can_try_download)
        self.open_edition()

    def _navigation_allowed(self, raw_url: str) -> bool:
        try:
            parsed = urlparse(str(raw_url or "").strip())
        except Exception:
            return False
        if parsed.scheme.lower() not in {"http", "https"}:
            return False
        host = str(parsed.hostname or "").strip().lower()
        return bool(host and self.provider.domain_allowed(host))

    def _candidate_looks_like_edition(
        self,
        href: str,
        label: str,
    ) -> bool:
        # Não usa o hostname para validar palavras da marca: caso contrário
        # qualquer PDF em estadao.com.br/gzh/etc. pareceria uma edição.
        try:
            parsed = urlparse(str(href or ""))
            href_signal = f"{parsed.path} {parsed.query} {parsed.fragment}"
        except Exception:
            href_signal = str(href or "")

        combined = _normalized_text(f"{label} {href_signal}")
        if not combined:
            return False

        reject = (
            "politica", "policy", "privacy", "privacidade", "anticorrup",
            "compliance", "boleto", "invoice", "receipt", "comprovante",
            "contrato", "regulamento", "faq", "midiakit", "media-kit",
        )
        if any(item in combined for item in reject):
            return False

        strong = (
            "baixar pdf", "download pdf", "baixar edicao", "baixar edição",
            "download edition", "download edicao", "download edição",
            "edicao completa", "edição completa", "full edition",
            "jornal digital", "replica edition", "print edition",
        )
        if any(_normalized_text(item) in combined for item in strong):
            return True

        for keyword in self.provider.edition_link_keywords:
            if _normalized_text(keyword) in combined:
                return True

        return False

    def _autofill_saved_credentials(
        self,
        *,
        auto_submit: bool,
    ) -> None:
        credentials = self.credential_store.load()
        if credentials is None:
            return

        current = self.page.url().toString().strip()
        if not self._navigation_allowed(current):
            return

        username, password = credentials
        script = r"""
        (function(user, pass, autoSubmit){
          function visible(el){
            if(!el) return false;
            var s=window.getComputedStyle(el);
            return s.display!=='none' && s.visibility!=='hidden' && !el.disabled;
          }
          function setValue(el, value){
            if(!el || !value) return false;
            try{
              var proto = Object.getPrototypeOf(el);
              var desc = Object.getOwnPropertyDescriptor(proto, 'value');
              if(desc && desc.set){ desc.set.call(el, value); }
              else { el.value=value; }
              el.dispatchEvent(new Event('input',{bubbles:true}));
              el.dispatchEvent(new Event('change',{bubbles:true}));
              return true;
            }catch(e){ return false; }
          }
          var hay=(location.href+' '+document.title).toLowerCase();
          var pw=Array.from(document.querySelectorAll('input[type="password"]')).find(visible) || null;
          var loginHint=!!pw || /(login|signin|sign-in|auth|entrar|conta|account)/.test(hay);
          if(!loginHint) return JSON.stringify({ok:false,reason:'not_login'});

          var users=Array.from(document.querySelectorAll(
            'input[type="email"],input[name*="email" i],input[name*="user" i],input[id*="email" i],input[id*="user" i],input[autocomplete="username"]'
          )).filter(visible);
          var u=users.length ? users[0] : null;
          var filledUser=setValue(u,user);
          var filledPass=setValue(pw,pass);
          var submitted=false;

          if(autoSubmit){
            var buttons=Array.from(document.querySelectorAll('button,input[type="submit"],[role="button"]')).filter(visible);
            var wanted=null;
            for(var i=0;i<buttons.length;i++){
              var t=String(buttons[i].innerText || buttons[i].value || buttons[i].getAttribute('aria-label') || '').toLowerCase();
              if(/(entrar|acessar|login|sign in|continuar|continue|proximo|próximo|next)/.test(t)){
                wanted=buttons[i]; break;
              }
            }
            if(wanted && ((pw && filledPass) || (!pw && filledUser))){
              wanted.click(); submitted=true;
            }
          }
          return JSON.stringify({ok:true,user:filledUser,password:filledPass,submitted:submitted});
        })(%s,%s,%s)
        """ % (
            json.dumps(username),
            json.dumps(password),
            "true" if auto_submit else "false",
        )
        try:
            self.page.runJavaScript(script)
        except Exception:
            pass

    def _finish_auto_not_found(self) -> None:
        self._auto_download_active = False
        self._auto_download_requested = False
        self._edition_download_armed = False
        self.download_button.setEnabled(self.provider.can_try_download)

        if self._auto_login_seen:
            self._emit_status(
                f"{self.provider.name}: autenticação necessária ou sessão expirada. "
                "Use “Entrar / renovar sessão” uma vez e depois clique em “Iniciar busca / baixar edição”."
            )
            return

        self._emit_status(
            f"{self.provider.name}: nenhum PDF completo ou exportação autorizada foi "
            "localizado automaticamente nos leitores oficiais testados. Se o serviço "
            "oferecer download somente após login, use “Entrar / renovar sessão”."
        )

    def _advance_auto_entry(self) -> None:
        if not self._auto_download_active:
            return

        self._edition_download_armed = False

        while True:
            self._auto_entry_index += 1
            if self._auto_entry_index >= len(self._auto_entry_urls):
                self._finish_auto_not_found()
                return

            raw = self._auto_entry_urls[self._auto_entry_index]
            url = str(raw or "").strip()
            if not url or url in self._auto_seen_urls:
                continue
            if not self._navigation_allowed(url):
                continue

            self._auto_seen_urls.add(url)
            self._auto_probe_attempts = 0
            self._auto_navigation_depth = 0
            self._auto_download_requested = True
            self._emit_status(
                f"{self.provider.name}: verificando leitor oficial "
                f"{self._auto_entry_index + 1}/{len(self._auto_entry_urls)}…"
            )
            self.view.load(QUrl(url))
            return

    def start_automatic_download(self) -> None:
        self._edition_download_armed = False
        if not self.provider.can_try_download:
            self._emit_status(
                "Este provedor não oferece um fluxo web confirmado para baixar a edição."
            )
            return

        if self.provider.download_strategy == "pressreader_hd_images":
            self._start_pressreader_hd_download()
            return

        direct_url = self.provider.direct_pdf_url(self.target_date)
        if direct_url:
            self._start_direct_pdf_download(direct_url)
            return

        self._pending_method = (
            "PDF oficial"
            if self.provider.official_pdf_documented
            else "Exportação/download autorizado"
        )
        self._auto_download_active = True
        self._auto_download_requested = True
        self._auto_entry_urls = self.provider.edition_urls(self.target_date)
        self._auto_entry_index = -1
        self._auto_seen_urls.clear()
        self._auto_probe_attempts = 0
        self._auto_navigation_depth = 0
        self._auto_login_seen = False
        self.download_button.setEnabled(False)

        self._emit_status(
            f"{self.provider.name}: procurando a edição de "
            f"{self.target_date.strftime('%d/%m/%Y')} nos leitores oficiais…"
        )
        self._advance_auto_entry()

    def _start_pressreader_hd_download(self) -> None:
        if self._pressreader_thread is not None and self._pressreader_thread.isRunning():
            self._emit_status("O PDF HD do Valor já está sendo montado.")
            return

        first_url = self.provider.pressreader_page_url(self.target_date, 1)
        if not first_url:
            self._emit_status("O provedor não possui URL de páginas PressReader configurada.")
            return

        self._auto_download_active = False
        self._auto_download_requested = True
        self._valor_hd_active = True
        self._valor_page_number = 1
        self._valor_image_urls.clear()
        self._valor_probe_attempts = 0
        self._valor_reload_attempts = 0
        self._valor_intercepted_best_url = ""
        self._valor_intercepted_best_score = -1
        self.download_button.setEnabled(False)
        try:
            self.page.setVisible(True)
        except Exception:
            pass
        try:
            self.page.setLifecycleState(QWebEnginePage.LifecycleState.Active)
        except Exception:
            pass
        try:
            self.view.resize(1440, 2400)
        except Exception:
            pass
        self._emit_status(
            f"{self.provider.name}: abrindo página 01 da edição de "
            f"{self.target_date.strftime('%d/%m/%Y')} no PressReader…"
        )
        self.view.load(QUrl(first_url))

    def _pressreader_page_expected_path(self, page_number: int) -> str:
        return (
            f"/{self.target_date.strftime('%Y%m%d')}/page/{int(page_number)}"
        )

    def _pressreader_load_finished(self, ok: bool) -> None:
        if not self._valor_hd_active:
            return

        if not ok:
            if self._valor_reload_attempts < 1:
                self._valor_reload_attempts += 1
                QTimer.singleShot(800, self.view.reload)
                return
            self._finish_pressreader_hd_error(
                "A página do PressReader não concluiu o carregamento. "
                "Verifique internet, Proxy Geral ou autenticação."
            )
            return

        self._autofill_saved_credentials(auto_submit=True)
        self._valor_probe_attempts = 0
        try:
            self.page.runJavaScript(
                "(function(){try{document.querySelectorAll('img').forEach(function(i){i.loading='eager';});window.scrollTo(0,1);window.scrollTo(0,0);window.dispatchEvent(new Event('resize'));}catch(e){}return true;})()"
            )
        except Exception:
            pass
        QTimer.singleShot(3200, self._probe_pressreader_resources)

    def _probe_pressreader_resources(self) -> None:
        if not self._valor_hd_active:
            return

        try:
            self.page.runJavaScript(
                PRESSREADER_RESOURCES_JS,
                self._pressreader_probe_result,
            )
        except Exception as exc:
            self._finish_pressreader_hd_error(
                f"Não foi possível ler os recursos HD do PressReader: {exc}"
            )

    def _pressreader_probe_result(self, raw) -> None:
        if not self._valor_hd_active:
            return

        try:
            data = json.loads(str(raw or ""))
        except Exception:
            data = {}

        current = str(data.get("href") or self.page.url().toString() or "")
        has_password = bool(data.get("hasPassword"))
        expected = self._pressreader_page_expected_path(self._valor_page_number)

        if has_password or any(
            marker in current.lower()
            for marker in ("/login", "/signin", "sign-in", "/auth")
        ):
            self._autofill_saved_credentials(auto_submit=True)
            if self._valor_probe_attempts < 2:
                self._valor_probe_attempts += 1
                QTimer.singleShot(1700, self._probe_pressreader_resources)
                return
            self._finish_pressreader_hd_error(
                "A sessão do PressReader precisa ser renovada. Use “Entrar / renovar sessão” "
                "uma vez e tente novamente."
            )
            return

        resources = data.get("resources")
        if not isinstance(resources, list):
            resources = []

        best_url = self._valor_intercepted_best_url
        best_score = self._valor_intercepted_best_score
        for item in resources:
            url = str(item or "").strip()
            score = pressreader_image_candidate_score(
                url,
                expected_page=self._valor_page_number,
            )
            if score is not None and score > best_score:
                best_url = url
                best_score = score

        if best_url:
            page_number = self._valor_page_number
            self._valor_image_urls[page_number] = best_url
            self._emit_status(
                f"{self.provider.name}: página {page_number:02d} localizada no CDN HD."
            )
            self._valor_page_number += 1
            self._valor_probe_attempts = 0
            self._valor_reload_attempts = 0
            self._valor_intercepted_best_url = ""
            self._valor_intercepted_best_score = -1

            if self._valor_page_number > int(self.provider.pressreader_max_pages):
                self._finish_pressreader_collection()
                return

            next_url = self.provider.pressreader_page_url(
                self.target_date,
                self._valor_page_number,
            )
            QTimer.singleShot(350, lambda: self.view.load(QUrl(next_url)))
            return

        if self._valor_probe_attempts < 3:
            self._valor_probe_attempts += 1
            try:
                self.page.runJavaScript(
                    "(function(){try{window.scrollTo(0,0);window.dispatchEvent(new Event('resize'));}catch(e){} return true;})()"
                )
            except Exception:
                pass
            QTimer.singleShot(1800, self._probe_pressreader_resources)
            return

        # Uma recarga reduz o risco de considerar como fim da edição uma página
        # que apenas demorou a renderizar no Chromium oculto.
        if self._valor_reload_attempts < 1 and expected in current:
            self._valor_reload_attempts += 1
            self._valor_probe_attempts = 0
            self._emit_status(
                f"{self.provider.name}: página {self._valor_page_number:02d} demorou a carregar; tentando novamente…"
            )
            self.view.reload()
            return

        collected = len(self._valor_image_urls)
        if collected >= int(self.provider.min_edition_pages):
            self._finish_pressreader_collection()
            return

        if expected not in current:
            detail = "a edição/data não foi aberta pelo PressReader"
        else:
            detail = "não apareceu uma imagem de página válida no CDN"
        self._finish_pressreader_hd_error(
            f"{detail}. Foram localizadas somente {collected} páginas; "
            f"o mínimo esperado é {self.provider.min_edition_pages}."
        )

    def _finish_pressreader_collection(self) -> None:
        if not self._valor_hd_active:
            return

        self._valor_hd_active = False
        self._auto_download_requested = False
        self._save_cookie_vault()

        pages = sorted(self._valor_image_urls)
        if not pages or pages != list(range(1, pages[-1] + 1)):
            self._finish_pressreader_hd_error(
                "A sequência das páginas do Valor veio incompleta. Nenhum PDF foi gerado."
            )
            return

        target = _output_target(self.paths, self.provider, self.target_date)
        thread = PressReaderHdPdfThread(
            paths=self.paths,
            provider=self.provider,
            target_date=self.target_date,
            page_urls=dict(self._valor_image_urls),
            output_path=target,
            parent=self,
        )
        thread.status_changed.connect(self._emit_status)
        thread.failed.connect(self._pressreader_thread_failed)
        thread.completed.connect(self._pressreader_thread_completed)
        thread.finished.connect(self._pressreader_thread_finished)
        self._pressreader_thread = thread
        self._emit_status(
            f"{self.provider.name}: {len(pages)} páginas localizadas; baixando as imagens HD…"
        )
        thread.start()

    def _finish_pressreader_hd_error(self, message: str) -> None:
        self._valor_hd_active = False
        self._auto_download_requested = False
        self.download_button.setEnabled(self.provider.can_try_download)
        self._emit_status(f"{self.provider.name}: {message}")

    def _pressreader_thread_failed(self, message: str) -> None:
        self.download_button.setEnabled(self.provider.can_try_download)
        self._emit_status(f"{self.provider.name}: {message}")

    def _pressreader_thread_completed(
        self,
        path: str,
        pages: int,
        method: str,
    ) -> None:
        self.download_button.setEnabled(self.provider.can_try_download)
        self._emit_status(
            f"{self.provider.name}: PDF HD concluído com {pages} páginas: {path}"
        )
        self.pdf_completed.emit(path, pages, method)

    def _pressreader_thread_finished(self) -> None:
        thread = self._pressreader_thread
        self._pressreader_thread = None
        if thread is not None:
            thread.deleteLater()

    def _start_direct_pdf_download(self, url: str) -> None:
        if self._direct_thread is not None and self._direct_thread.isRunning():
            self._emit_status("O download desta edição já está em andamento.")
            return

        thread = DirectPdfDownloadThread(
            paths=self.paths,
            provider=self.provider,
            target_date=self.target_date,
            url=url,
            parent=self,
        )
        thread.status_changed.connect(self._emit_status)
        thread.failed.connect(self._direct_failed)
        thread.completed.connect(self._direct_completed)
        thread.finished.connect(self._direct_thread_finished)
        self._direct_thread = thread
        thread.start()

    def _direct_failed(self, message: str) -> None:
        self._emit_status(
            f"{self.provider.name}: {message}"
        )

    def _direct_completed(
        self,
        path: str,
        pages: int,
        method: str,
    ) -> None:
        self._emit_status(
            f"PDF concluído sem recompressão: {path}"
        )
        self.pdf_completed.emit(
            path,
            pages,
            method,
        )

    def _direct_thread_finished(self) -> None:
        thread = self._direct_thread
        self._direct_thread = None
        if thread is not None:
            thread.deleteLater()

    def _load_finished(self, ok: bool) -> None:
        if self._valor_hd_active:
            self._pressreader_load_finished(ok)
            return

        if not ok:
            if self._auto_download_active:
                self._advance_auto_entry()
                return
            self._emit_status(
                "A página não concluiu o carregamento. Verifique internet, Proxy Geral "
                "ou autenticação do site."
            )
            return

        self._autofill_saved_credentials(
            auto_submit=self._auto_download_active,
        )

        if self._auto_download_active:
            current = self.page.url().toString().strip()
            if current:
                self._auto_seen_urls.add(current)
            self._auto_probe_attempts = 0
            QTimer.singleShot(
                1800,
                self.try_download_edition,
            )
            return

        self._emit_status(
            "Página de autenticação carregada. Se houver acesso salvo localmente, "
            "os campos são preenchidos sem expor a senha no código ou no GitHub."
        )

    def try_download_edition(self) -> None:
        if not self.provider.can_try_download:
            self._emit_status(
                "Este provedor não oferece um fluxo web confirmado para baixar a edição."
            )
            return

        if self._download_in_progress:
            return

        self._pending_method = (
            "PDF oficial"
            if self.provider.official_pdf_documented
            else "Exportação/download autorizado"
        )
        self.download_button.setEnabled(False)
        self._emit_status(
            f"{self.provider.name}: analisando PDF, edição, viewer e exportação autorizada…"
        )
        self.page.runJavaScript(
            DOWNLOAD_PROBE_JS,
            self._download_probe_result,
        )

    def _reprobe_after_click(self) -> None:
        if not self._auto_download_active or self._download_in_progress:
            return
        self._edition_download_armed = False
        if self._auto_probe_attempts >= 3:
            self._advance_auto_entry()
            return
        self.try_download_edition()

    def _download_probe_result(self, raw) -> None:
        try:
            data = json.loads(str(raw or ""))
        except Exception:
            data = {}

        if not data.get("ok"):
            reason = str(data.get("reason") or "")
            if reason == "login_required":
                self._auto_login_seen = True
                # Em fluxo oculto, uma credencial local pode completar o login.
                self._autofill_saved_credentials(auto_submit=True)

            if (
                self._auto_download_active
                and reason in {"not_found", "login_required"}
                and self._auto_probe_attempts < 2
            ):
                self._auto_probe_attempts += 1
                QTimer.singleShot(1800, self.try_download_edition)
                return

            if self._auto_download_active:
                self._advance_auto_entry()
            else:
                self.download_button.setEnabled(self.provider.can_try_download)
            return

        mode = str(data.get("mode") or "")
        href = str(data.get("href") or "").strip()
        label = str(data.get("text") or "")

        if mode == "direct_pdf" and href:
            if not self._candidate_looks_like_edition(href, label):
                self._emit_status(
                    f"{self.provider.name}: PDF ignorado porque não parece ser a edição completa."
                )
                if self._auto_download_active:
                    self._advance_auto_entry()
                return

            self._edition_download_armed = True
            self._emit_status(
                "PDF da edição localizado. Iniciando o download original…"
            )
            try:
                self.page.download(
                    QUrl(href),
                    self.provider.output_filename(self.target_date),
                )
                return
            except Exception:
                pass

            script = (
                "(function(u){var a=document.createElement('a');"
                "a.href=u;a.download='';a.rel='noopener';"
                "document.body.appendChild(a);a.click();a.remove();})(%s)"
                % json.dumps(href)
            )
            self.page.runJavaScript(script)
            return

        if mode == "navigate" and href:
            if (
                self._auto_download_active
                and self._navigation_allowed(href)
                and href not in self._auto_seen_urls
                and self._auto_navigation_depth < 5
            ):
                self._auto_navigation_depth += 1
                self._auto_seen_urls.add(href)
                self._edition_download_armed = False
                self._emit_status(
                    f"{self.provider.name}: seguindo o leitor oficial da edição…"
                )
                self.view.load(QUrl(href))
                return

            if self._auto_download_active:
                self._advance_auto_entry()
            return

        if mode == "click_candidate":
            if not self._candidate_looks_like_edition(href, label):
                if self._auto_download_active:
                    self._advance_auto_entry()
                return

            self._edition_download_armed = True
            self._auto_probe_attempts += 1
            self._emit_status(
                "Comando específico de edição/download autorizado. Aguardando o arquivo…"
            )
            script = r"""
            (function(){
              var n=document.querySelector('[data-central-edition-candidate="1"]');
              if(!n) return false;
              n.removeAttribute('data-central-edition-candidate');
              try{n.scrollIntoView({block:'center',inline:'center'});}catch(e){}
              n.click();
              return true;
            })()
            """
            self.page.runJavaScript(script)
            QTimer.singleShot(1900, self._reprobe_after_click)
            return

        if self._auto_download_active:
            self._advance_auto_entry()
        else:
            self.download_button.setEnabled(self.provider.can_try_download)

    def _download_requested(
        self,
        download: QWebEngineDownloadRequest,
    ) -> None:
        try:
            suggested = str(download.suggestedFileName() or "")
        except Exception:
            suggested = ""

        try:
            mime = str(download.mimeType() or "").lower()
        except Exception:
            mime = ""

        is_pdf = (
            suggested.lower().endswith(".pdf")
            or "application/pdf" in mime
            or str(download.url().toString()).lower().split("?", 1)[0].endswith(".pdf")
        )

        if not is_pdf:
            try:
                download.cancel()
            except Exception:
                pass
            self._emit_status(
                "O site tentou baixar um arquivo que não é PDF. Ele não foi tratado "
                "como edição completa."
            )
            if self._auto_download_active:
                QTimer.singleShot(500, self._advance_auto_entry)
            return

        if not self._edition_download_armed:
            try:
                download.cancel()
            except Exception:
                pass
            self._emit_status(
                "PDF ignorado: o download não foi identificado como edição completa do jornal."
            )
            if self._auto_download_active:
                QTimer.singleShot(400, self._advance_auto_entry)
            return

        self._edition_download_armed = False
        self._download_origin_auto = self._auto_download_active
        self._auto_download_active = False
        self._auto_download_requested = False

        target = _output_target(
            self.paths,
            self.provider,
            self.target_date,
        )
        output_dir = target.parent

        try:
            target.unlink()
        except FileNotFoundError:
            pass

        try:
            download.setDownloadDirectory(str(output_dir))
            download.setDownloadFileName(target.name)
        except Exception:
            pass

        self._download_in_progress = True
        self._emit_status(
            f"Baixando PDF original: {target.name}"
        )

        download.stateChanged.connect(
            lambda _state, d=download, p=target:
                self._download_state_changed(d, p)
        )
        download.accept()

    def _download_state_changed(
        self,
        download: QWebEngineDownloadRequest,
        target: Path,
    ) -> None:
        state = download.state()

        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self._download_in_progress = False
            self.download_button.setEnabled(self.provider.can_try_download)

            try:
                pages = validate_full_edition_pdf(
                    target,
                    self.provider,
                )
            except Exception as exc:
                try:
                    target.unlink()
                except Exception:
                    pass
                self._emit_status(
                    f"{self.provider.name}: {exc} O arquivo foi descartado."
                )
                if self._download_origin_auto:
                    self._download_origin_auto = False
                    self._auto_download_active = True
                    QTimer.singleShot(500, self._advance_auto_entry)
                return

            self._download_origin_auto = False
            self._emit_status(
                f"PDF concluído sem recompressão: {target}"
            )
            self.pdf_completed.emit(
                str(target),
                pages,
                self._pending_method,
            )
            return

        if state in {
            QWebEngineDownloadRequest.DownloadState.DownloadCancelled,
            QWebEngineDownloadRequest.DownloadState.DownloadInterrupted,
        }:
            self._download_in_progress = False
            was_auto = self._download_origin_auto
            self._download_origin_auto = False
            self.download_button.setEnabled(self.provider.can_try_download)
            self._emit_status(
                "O download foi cancelado ou interrompido pelo site/navegador."
            )
            if was_auto:
                self._auto_download_active = True
                QTimer.singleShot(500, self._advance_auto_entry)

    def _emit_status(self, text: str) -> None:
        self.status.setText(text)
        self.status_changed.emit(text)

    def shutdown(self) -> None:
        self._valor_hd_active = False
        if self._direct_thread is not None and self._direct_thread.isRunning():
            self._direct_thread.requestInterruption()
            self._direct_thread.wait(1500)

        if self._pressreader_thread is not None and self._pressreader_thread.isRunning():
            self._pressreader_thread.requestInterruption()
            self._pressreader_thread.wait(1800)

        if self._cookie_save_timer.isActive():
            self._cookie_save_timer.stop()
            self._save_cookie_vault()

        try:
            self.page.triggerAction(QWebEnginePage.WebAction.Stop)
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)
