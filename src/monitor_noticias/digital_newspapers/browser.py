from __future__ import annotations

import base64
from datetime import date
import json
from pathlib import Path
import shutil

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
from monitor_noticias.digital_newspapers.storage import SecureSessionStore
from monitor_noticias.networking.proxy import (
    ProxySettings,
    corporate_tls_compatibility,
)


class DigitalNewspaperPage(QWebEnginePage):
    """Mantém popups/login dentro do mesmo navegador da Central."""

    def createWindow(self, _window_type):  # noqa: N802
        return self


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

  var nodes = Array.prototype.slice.call(
    document.querySelectorAll(
      'a[href], button, [role="button"], [download], input[type="button"], input[type="submit"]'
    )
  );

  var ranked = [];
  var phrases = [
    'baixar pdf',
    'download pdf',
    'baixar edicao',
    'baixar edição',
    'download edition',
    'edicao pdf',
    'edição pdf',
    'jornal em pdf',
    'full edition pdf',
    'edition pdf',
    'download edição',
    'download edicao'
  ];

  for(var i=0;i<nodes.length;i++){
    var n = nodes[i];
    var text = norm(
      (n.innerText || '') + ' ' +
      (n.textContent || '') + ' ' +
      (n.value || '') + ' ' +
      (n.getAttribute('aria-label') || '') + ' ' +
      (n.getAttribute('title') || '')
    );
    var href = '';
    try{
      href = n.href ? String(n.href) : '';
    }catch(e){}

    var score = 0;

    if(/\.pdf(?:$|[?#])/i.test(href)) score += 5000;
    if(n.hasAttribute && n.hasAttribute('download')) score += 900;

    for(var p=0;p<phrases.length;p++){
      if(text.indexOf(phrases[p]) >= 0){
        score += 1200 - (p * 35);
      }
    }

    // Evita escolher PDF/botão de uma única página quando a intenção é a edição inteira.
    if(
      text.indexOf('pagina') >= 0 ||
      text.indexOf('página') >= 0 ||
      text.indexOf('page ') >= 0
    ){
      score -= 1200;
    }

    if(score > 0){
      ranked.push({
        index: i,
        score: score,
        href: href,
        text: text.slice(0, 220)
      });
    }
  }

  ranked.sort(function(a,b){return b.score-a.score;});

  if(!ranked.length || ranked[0].score < 900){
    return JSON.stringify({ok:false, reason:'not_found'});
  }

  var best = ranked[0];
  var node = nodes[best.index];

  if(best.href && /\.pdf(?:$|[?#])/i.test(best.href)){
    return JSON.stringify({
      ok:true,
      mode:'direct_pdf',
      href:best.href,
      text:best.text
    });
  }

  try{
    node.scrollIntoView({block:'center', inline:'center'});
    node.click();
    return JSON.stringify({
      ok:true,
      mode:'clicked',
      href:best.href || '',
      text:best.text
    });
  }catch(e){
    return JSON.stringify({
      ok:false,
      reason:'click_failed',
      detail:String(e || '')
    });
  }
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
    ) -> int:
        with path.open("rb") as handle:
            signature = handle.read(5)

        if signature != b"%PDF-":
            raise RuntimeError(
                "O endereço oficial não retornou um PDF. A sessão pode ter expirado."
            )

        try:
            from pypdf import PdfReader

            pages = len(PdfReader(str(path)).pages)
        except Exception as exc:
            raise RuntimeError(
                "O arquivo recebido não passou na validação de PDF."
            ) from exc

        if pages <= 0:
            raise RuntimeError(
                "O arquivo PDF foi recebido, mas veio sem páginas válidas."
            )
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
                        page_count = self._validate_pdf(candidate)
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
        self._direct_thread: DirectPdfDownloadThread | None = None

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
            "No uso normal, clique no nome do jornal na aba Jornais Digitais e o "
            "download acontece sem abrir esta janela. A Central não armazena sua senha."
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
        self.view.load(
            QUrl(self.provider.edition_url)
        )

    def prepare_manual_login(self) -> None:
        self._auto_download_requested = False
        self.open_edition()

    def start_automatic_download(self) -> None:
        if not self.provider.can_try_download:
            self._emit_status(
                "Este provedor não oferece um fluxo web confirmado para baixar a edição."
            )
            return

        direct_url = self.provider.direct_pdf_url(self.target_date)
        if direct_url:
            self._start_direct_pdf_download(direct_url)
            return

        self._auto_download_requested = True
        self._pending_method = (
            "PDF oficial"
            if self.provider.official_pdf_documented
            else "Exportação/download autorizado"
        )
        self._emit_status(
            f"{self.provider.name}: procurando a edição de "
            f"{self.target_date.strftime('%d/%m/%Y')} em segundo plano…"
        )
        self.open_edition()

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
        if not ok:
            self._auto_download_requested = False
            self._emit_status(
                "A página não concluiu o carregamento. Verifique internet, Proxy Geral "
                "ou autenticação do site."
            )
            return

        if self._auto_download_requested:
            self._auto_download_requested = False
            QTimer.singleShot(
                900,
                self.try_download_edition,
            )
            return

        self._emit_status(
            "Página de autenticação carregada. Entre normalmente. A senha não é "
            "armazenada; somente a sessão/cookies permitidos podem ser protegidos localmente."
        )

    def try_download_edition(self) -> None:
        if not self.provider.can_try_download:
            self._emit_status(
                "Este provedor não oferece um fluxo web confirmado para baixar a edição."
            )
            return

        self._pending_method = (
            "PDF oficial"
            if self.provider.official_pdf_documented
            else "Exportação/download autorizado"
        )
        self.download_button.setEnabled(False)
        self._emit_status(
            "Procurando automaticamente PDF ou exportação autorizada da edição…"
        )
        self.page.runJavaScript(
            DOWNLOAD_PROBE_JS,
            self._download_probe_result,
        )

    def _download_probe_result(self, raw) -> None:
        self.download_button.setEnabled(
            self.provider.can_try_download
        )

        try:
            data = json.loads(str(raw or ""))
        except Exception:
            data = {}

        if not data.get("ok"):
            self._emit_status(
                "Nenhum PDF completo autorizado foi localizado automaticamente. "
                "A sessão pode precisar ser renovada em “Entrar / renovar sessão”."
            )
            return

        mode = str(data.get("mode") or "")
        href = str(data.get("href") or "").strip()

        if mode == "direct_pdf" and href:
            self._emit_status(
                "PDF autorizado localizado. Iniciando o download original…"
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

        if mode == "clicked":
            self._emit_status(
                "Comando oficial de download/exportação acionado. Aguardando o PDF…"
            )
            return

        self._emit_status(
            "O visualizador respondeu, mas não iniciou um PDF completo autorizado."
        )

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
            return

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

            try:
                with target.open("rb") as handle:
                    if handle.read(5) != b"%PDF-":
                        raise ValueError("assinatura PDF inválida")

                from pypdf import PdfReader

                pages = len(PdfReader(str(target)).pages)
            except Exception:
                try:
                    target.unlink()
                except Exception:
                    pass
                self._emit_status(
                    "O arquivo recebido não era um PDF válido da edição e foi descartado."
                )
                return

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
            self._emit_status(
                "O download foi cancelado ou interrompido pelo site/navegador."
            )

    def _emit_status(self, text: str) -> None:
        self.status.setText(text)
        self.status_changed.emit(text)

    def shutdown(self) -> None:
        if self._direct_thread is not None and self._direct_thread.isRunning():
            self._direct_thread.requestInterruption()
            self._direct_thread.wait(1500)

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
