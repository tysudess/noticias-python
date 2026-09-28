from __future__ import annotations

import base64
from datetime import date
import json
from pathlib import Path

from PySide6.QtCore import QDateTime, QByteArray, QTimer, QUrl, Signal
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
from monitor_noticias.capas_tool.app import network as covers_network
from monitor_noticias.digital_newspapers.providers import DigitalNewspaperProvider
from monitor_noticias.digital_newspapers.storage import SecureSessionStore
from monitor_noticias.networking.proxy import corporate_tls_compatibility


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
    'edition pdf'
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

    var lowHref = norm(href);
    var score = 0;

    if(/\.pdf(?:$|[?#])/i.test(href)) score += 5000;
    if(n.hasAttribute && n.hasAttribute('download')) score += 900;

    for(var p=0;p<phrases.length;p++){
      if(text.indexOf(phrases[p]) >= 0){
        score += 1200 - (p * 40);
      }
    }

    if(text.indexOf('pagina') >= 0 || text.indexOf('page') >= 0){
      score -= 250;
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

  if(!ranked.length){
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


class DigitalNewspaperBrowserDialog(QDialog):
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

        self.setWindowTitle(
            f"Jornais Digitais • {provider.name}"
        )
        self.resize(1320, 860)
        self.setMinimumSize(980, 650)

        self._build_browser()
        self._build_ui()
        self._restore_cookie_vault()
        self.open_edition()

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
            lambda: self._emit_status("Abrindo edição…")
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

        open_button = QPushButton("Abrir edição")
        open_button.clicked.connect(self.open_edition)
        toolbar.addWidget(open_button)

        self.download_button = QPushButton(
            "Baixar edição completa"
        )
        self.download_button.clicked.connect(
            self.try_download_edition
        )
        self.download_button.setEnabled(
            self.provider.can_try_download
        )
        toolbar.addWidget(self.download_button)

        root.addLayout(toolbar)

        self.info = QLabel(
            "Use somente sua própria assinatura. A Central não armazena a senha "
            "do jornal e não contorna paywall, CAPTCHA, DRM ou proteção técnica."
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
            # QNetworkCookie não informa a origem de um cookie host-only.
            # Para não atribuir por engano um cookie de terceiro ao domínio
            # visível da página, cookies sem domínio explícito ficam somente
            # na memória do Chromium e não entram no cofre persistente.
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
            self._emit_status(
                f"Sessão protegida restaurada ({restored} cookies)."
            )

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

    def _load_finished(self, ok: bool) -> None:
        if ok:
            self._emit_status(
                "Página carregada. Faça login normalmente, abra a edição desejada "
                "e use “Baixar edição completa”."
            )
        else:
            self._emit_status(
                "A página não concluiu o carregamento. Verifique internet, Proxy Geral "
                "ou autenticação do site."
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
            "Procurando na página atual um PDF ou botão de exportação autorizado…"
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
                "Nenhum download autorizado foi localizado nesta tela. "
                "Abra a edição correta e tente novamente."
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
                # Alguns builds do Qt não expõem Page.download. O clique direto
                # continua sendo tentado abaixo, sem contornar o site.
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
                "Comando de download/exportação acionado. Aguardando o site iniciar o arquivo…"
            )
            return

        self._emit_status(
            "O visualizador respondeu, mas não iniciou um PDF autorizado."
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
                "O site tentou baixar um arquivo que não é PDF. A V77 não o tratou "
                "como edição completa para evitar perda de qualidade ou arquivo incorreto."
            )
            return

        output_dir = (
            Path(self.paths.state_root)
            / "JornaisDigitais"
            / self.provider.id
            / self.target_date.isoformat()
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = self.provider.output_filename(self.target_date)
        target = output_dir / filename
        base_stem = target.stem
        suffix = target.suffix
        counter = 2
        while target.exists():
            target = output_dir / (
                f"{base_stem}-{counter}{suffix}"
            )
            counter += 1

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
            pages = 0
            try:
                from pypdf import PdfReader

                pages = len(PdfReader(str(target)).pages)
            except Exception:
                pages = 0

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

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._cookie_save_timer.isActive():
            self._cookie_save_timer.stop()
            self._save_cookie_vault()
        super().closeEvent(event)
