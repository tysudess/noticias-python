from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QRect,
    QTimer,
)

from monitor_noticias.capas_tool.app import ui as covers_ui
from monitor_noticias.capas_tool.app.config import (
    cache_dir,
)
from monitor_noticias.capas_tool.app.models import (
    CandidatePage,
)
from monitor_noticias.capas_tool.app.network import (
    safe_slug,
)
from monitor_noticias.capas_tool.app.ocr import (
    score_candidate,
)
from monitor_noticias.capas_tool.app.web_resolver_patch import (
    RobustFrontPageResolver,
)
from monitor_noticias.capas_tool.app.workers import (
    Worker,
)


_INSTALLED = False


# V42:
# O FrontPages já conseguiu carregar a capa dentro do QWebEngineView, mas
# algumas URLs de imagem retornam HTTP 404 quando são baixadas novamente com
# requests fora da sessão Chromium. Em vez de repetir o download, capturamos
# a imagem que o próprio navegador já renderizou.
CAPTURE_FRONT_PAGE_JS = r"""
(function(expected, slug){
  function norm(s){
    try{
      return String(s || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g,'')
        .toUpperCase();
    }catch(e){
      return String(s || '').toUpperCase();
    }
  }

  function cleanUrl(u){
    try{
      if(!u) return '';
      return new URL(
        String(u)
          .replace(/\\\//g,'/')
          .replace(/&amp;/g,'&'),
        document.baseURI
      ).href;
    }catch(e){
      return String(u || '');
    }
  }

  var expectedNorm = norm(expected);
  var slugNorm = String(slug || '').toLowerCase();
  var words = expectedNorm
    .split(/[^A-Z0-9]+/)
    .filter(function(x){
      return x && x !== 'THE' && x !== 'ECONOMICO';
    });

  var candidates = [];
  var imgs = document.images || [];

  for(var i=0;i<imgs.length;i++){
    var img = imgs[i];

    try{
      if(!img.complete) continue;

      var nw = Number(img.naturalWidth || 0);
      var nh = Number(img.naturalHeight || 0);

      if(nw < 180 || nh < 260) continue;

      var ratio = nh / Math.max(1,nw);

      if(ratio < 1.05 || ratio > 2.25) continue;

      var src = cleanUrl(
        img.currentSrc ||
        img.src ||
        img.getAttribute('data-src') ||
        img.getAttribute('data-original') ||
        ''
      );

      var info = norm(
        (img.alt || '') + ' ' +
        (img.title || '') + ' ' +
        (img.getAttribute('data-title') || '') + ' ' +
        (img.getAttribute('data-caption') || '') + ' ' +
        src
      );

      var low = String(src || '').toLowerCase();

      if(
        expectedNorm.indexOf('WASHINGTON POST') >= 0 &&
        (
          info.indexOf('SPORTS') >= 0 ||
          low.indexOf('sports') >= 0
        )
      ){
        continue;
      }

      var score = 0;

      if(nw >= 500) score += 150;
      if(nh >= 700) score += 180;
      if(nw >= 700) score += 180;
      if(nh >= 950) score += 220;

      if(ratio >= 1.25 && ratio <= 1.75){
        score += 250;
      }

      if(low.indexOf('/g/') >= 0){
        score += 450;
      }

      if(
        slugNorm &&
        (
          low.indexOf('/' + slugNorm + '-') >= 0 ||
          low.indexOf(slugNorm) >= 0
        )
      ){
        score += 1200;
      }

      for(var w=0;w<words.length;w++){
        if(info.indexOf(words[w]) >= 0){
          score += 350;
        }
      }

      if(
        expectedNorm.indexOf('VALOR ECONOMICO') >= 0 &&
        (
          info.indexOf('VALOR') >= 0 ||
          low.indexOf('valor-economico') >= 0
        )
      ){
        score += 1800;
      }

      if(
        expectedNorm.indexOf('WASHINGTON POST') >= 0 &&
        (
          info.indexOf('WASHINGTON POST') >= 0 ||
          low.indexOf('washington-post') >= 0
        )
      ){
        score += 1800;
      }

      candidates.push({
        element: img,
        score: score,
        url: src,
        naturalWidth: nw,
        naturalHeight: nh
      });

    }catch(e){}
  }

  candidates.sort(function(a,b){
    return b.score - a.score;
  });

  if(!candidates.length){
    return '';
  }

  var best = candidates[0];

  if(best.score < 700){
    return '';
  }

  try{
    best.element.scrollIntoView({
      block: 'center',
      inline: 'center'
    });
  }catch(e){}

  var dataUrl = '';

  // Preferência: pixels na resolução natural da própria imagem carregada.
  // Como as capas do FrontPages normalmente vêm do próprio domínio, canvas
  // preserva a sessão/cookies e evita novo request pelo Python.
  try{
    var maxWidth = 1800;
    var scale = Math.min(
      1,
      maxWidth / Math.max(1,best.naturalWidth)
    );

    var cw = Math.max(
      1,
      Math.round(
        best.naturalWidth * scale
      )
    );

    var ch = Math.max(
      1,
      Math.round(
        best.naturalHeight * scale
      )
    );

    var canvas = document.createElement('canvas');
    canvas.width = cw;
    canvas.height = ch;

    var ctx = canvas.getContext(
      '2d',
      {
        alpha: false
      }
    );

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(
      0,
      0,
      cw,
      ch
    );

    ctx.drawImage(
      best.element,
      0,
      0,
      cw,
      ch
    );

    dataUrl = canvas.toDataURL(
      'image/png',
      1.0
    );
  }catch(e){
    dataUrl = '';
  }

  var rect = null;

  try{
    var r = best.element.getBoundingClientRect();

    rect = {
      x: Number(r.x || r.left || 0),
      y: Number(r.y || r.top || 0),
      w: Number(r.width || 0),
      h: Number(r.height || 0)
    };
  }catch(e){}

  return JSON.stringify({
    url: best.url || '',
    score: best.score || 0,
    naturalWidth: best.naturalWidth || 0,
    naturalHeight: best.naturalHeight || 0,
    dataUrl: dataUrl || '',
    rect: rect
  });
})(%EXPECTED%, %SLUG%)
"""


def _decode_data_url(
    value: str,
) -> bytes:
    raw = str(
        value or ""
    ).strip()

    if not raw.startswith(
        "data:image/"
    ):
        return b""

    marker = ";base64,"

    if marker not in raw:
        return b""

    try:
        encoded = raw.split(
            marker,
            1,
        )[1]

        return base64.b64decode(
            encoded,
            validate=False,
        )

    except Exception:
        return b""


def _grab_rendered_image(
    resolver: RobustFrontPageResolver,
    rect_data: dict,
) -> bytes:
    """Fallback: recorta a própria QWebEngineView já renderizada."""

    view = getattr(
        resolver.browser,
        "view",
        None,
    )

    if view is None:
        return b""

    try:
        pixmap = view.grab()

        if pixmap.isNull():
            return b""

        dpr = float(
            pixmap.devicePixelRatio()
            or 1.0
        )

        x = max(
            0,
            int(
                float(
                    rect_data.get(
                        "x",
                        0,
                    )
                    or 0
                )
                * dpr
            ),
        )

        y = max(
            0,
            int(
                float(
                    rect_data.get(
                        "y",
                        0,
                    )
                    or 0
                )
                * dpr
            ),
        )

        width = max(
            1,
            int(
                float(
                    rect_data.get(
                        "w",
                        0,
                    )
                    or 0
                )
                * dpr
            ),
        )

        height = max(
            1,
            int(
                float(
                    rect_data.get(
                        "h",
                        0,
                    )
                    or 0
                )
                * dpr
            ),
        )

        width = min(
            width,
            max(
                1,
                pixmap.width()
                - x,
            ),
        )

        height = min(
            height,
            max(
                1,
                pixmap.height()
                - y,
            ),
        )

        if (
            width < 150
            or height < 220
        ):
            return b""

        cropped = pixmap.copy(
            QRect(
                x,
                y,
                width,
                height,
            )
        )

        if cropped.isNull():
            return b""

        byte_array = QByteArray()
        buffer = QBuffer(
            byte_array
        )

        if not buffer.open(
            QIODevice.OpenModeFlag.WriteOnly
        ):
            return b""

        try:
            if not cropped.save(
                buffer,
                "PNG",
            ):
                return b""

            return bytes(
                byte_array
            )
        finally:
            buffer.close()

    except Exception:
        return b""


def _finish_browser_capture(
    resolver: RobustFrontPageResolver,
    data: dict,
    generation: int,
) -> None:
    if not resolver._active(
        generation
    ):
        return

    url = str(
        data.get(
            "url",
            "",
        )
        or ""
    ).strip()

    image_bytes = (
        _decode_data_url(
            str(
                data.get(
                    "dataUrl",
                    "",
                )
                or ""
            )
        )
    )

    if not image_bytes:
        image_bytes = (
            _grab_rendered_image(
                resolver,
                data.get(
                    "rect",
                    {},
                )
                or {},
            )
        )

    if image_bytes:
        resolver.last_browser_capture = (
            image_bytes
        )
        resolver.last_browser_capture_url = (
            url
            or resolver.last_referer
        )

        resolver._success(
            url
            or resolver.last_referer,
            generation,
        )
        return

    if (
        resolver._scan_count
        < resolver.MAX_SCAN_ATTEMPTS
    ):
        QTimer.singleShot(
            1100,
            lambda gen=generation:
                resolver._scan(gen),
        )
        return

    # Para o Valor isso segue automaticamente para PressReader.
    # Para o Post termina com diagnóstico real, sem inventar URL de imagem.
    resolver._source_failed(
        "a capa apareceu na página, "
        "mas o navegador não conseguiu capturar os pixels",
        generation,
    )


def _handle_capture_result(
    resolver: RobustFrontPageResolver,
    result,
    generation: int,
) -> None:
    if not resolver._active(
        generation
    ):
        return

    raw = str(
        result or ""
    ).strip()

    if not raw:
        if (
            resolver._scan_count
            < resolver.MAX_SCAN_ATTEMPTS
        ):
            QTimer.singleShot(
                1100,
                lambda gen=generation:
                    resolver._scan(
                        gen
                    ),
            )
        else:
            resolver._source_failed(
                "capa visual não localizada "
                "no FrontPages",
                generation,
            )
        return

    try:
        data = json.loads(
            raw
        )
    except Exception:
        data = {}

    if not isinstance(
        data,
        dict,
    ):
        data = {}

    # O scrollIntoView ocorre dentro do JavaScript. Pequeno atraso dá tempo ao
    # Chromium para redesenhar antes do fallback por captura da View.
    QTimer.singleShot(
        250,
        lambda d=data, gen=generation:
            _finish_browser_capture(
                resolver,
                d,
                gen,
            ),
    )


def _save_capture_and_score(
    image_bytes: bytes,
    dest: Path,
    source_url: str,
    name: str,
    mastheads,
    target_date,
    page_number: int = 1,
) -> CandidatePage:
    """Salva a captura do Chromium e executa a mesma validação OCR."""

    dest = Path(
        dest
    )
    dest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with Image.open(
        BytesIO(
            image_bytes
        )
    ) as original:
        image = original.convert(
            "RGB"
        )

        width, height = (
            image.size
        )

        if (
            width < 220
            or height < 320
            or height
            / max(
                1,
                width,
            )
            < 1.10
        ):
            raise RuntimeError(
                "A imagem capturada no navegador "
                "não possui formato de capa."
            )

        # A validação histórica do Valor espera pelo menos ~700x950.
        # Uma captura visual pode estar reduzida pelo CSS da página.
        # Redimensionamos somente quando necessário; não alteramos proporção.
        if width < 900:
            new_width = 900
            new_height = max(
                1,
                round(
                    height
                    * (
                        new_width
                        / width
                    )
                ),
            )

            image = image.resize(
                (
                    new_width,
                    new_height,
                ),
                Image.Resampling.LANCZOS,
            )

        image.save(
            dest,
            "PNG",
            optimize=True,
        )

    score, confidence, text = (
        score_candidate(
            dest,
            name,
            mastheads,
            target_date,
        )
    )

    candidate = CandidatePage(
        dest,
        score,
        confidence,
        text,
        source_url,
        page_number,
    )

    candidate.source_filename = (
        "browser-capture"
    )

    return candidate


def install_covers_browser_capture_patch() -> None:
    """V42 — captura Valor/Post diretamente da sessão Qt WebEngine."""

    global _INSTALLED

    if _INSTALLED:
        return

    # --------------------------------------------------------------
    # 1) Resolver: capturar pixels, não apenas URL.
    # --------------------------------------------------------------

    original_scan = (
        RobustFrontPageResolver._scan
    )

    def patched_scan(
        self: RobustFrontPageResolver,
        generation: int,
    ):
        if (
            not self._active(
                generation
            )
            or not self.page
        ):
            return

        source = (
            self._sources[
                self._source_index
            ]
        )

        if (
            "frontpages.com"
            not in source
        ):
            return original_scan(
                self,
                generation,
            )

        self._scan_count += 1

        expected = (
            "WASHINGTON POST"
            if self._name
            == "THE WASHINGTON POST"
            else "VALOR ECONOMICO"
        )

        # Torna a área renderizada ampla o bastante para o jornal aparecer
        # sem depender de viewport minúsculo.
        try:
            view = self.browser.view

            if view is not None:
                view.resize(
                    1400,
                    1900,
                )
        except Exception:
            pass

        js = (
            CAPTURE_FRONT_PAGE_JS
            .replace(
                "%EXPECTED%",
                json.dumps(
                    expected
                ),
            )
            .replace(
                "%SLUG%",
                json.dumps(
                    self._slug
                ),
            )
        )

        self.page.runJavaScript(
            js,
            lambda result, gen=generation:
                _handle_capture_result(
                    self,
                    result,
                    gen,
                ),
        )

    RobustFrontPageResolver._scan = (
        patched_scan
    )

    # --------------------------------------------------------------
    # 2) UI: para Valor/Post não usar mais o parser HTTP intermediário
    #    da V35. Abre diretamente o Qt WebEngine.
    # --------------------------------------------------------------

    main_window_cls = (
        covers_ui.MainWindow
    )

    previous_start = (
        main_window_cls
        ._start_single_web_resolver
    )

    def patched_start_single_web_resolver(
        self,
        entry,
        generation,
        one_done,
        pressreader_only=False,
    ):
        if (
            entry.name
            not in {
                "VALOR ECONÔMICO",
                "THE WASHINGTON POST",
            }
        ):
            return previous_start(
                self,
                entry,
                generation,
                one_done,
                pressreader_only,
            )

        resolver = (
            RobustFrontPageResolver(
                self
            )
        )

        resolver.progress.connect(
            self.set_status
        )

        self.web_resolvers.append(
            resolver
        )

        callback = (
            lambda url, err,
            en=entry,
            r=resolver,
            g=generation:
                self._web_resolved(
                    en,
                    r,
                    url,
                    err,
                    g,
                    one_done,
                )
        )

        if pressreader_only:
            resolver.resolve_pressreader_only(
                callback
            )
        else:
            # IMPORTANTE:
            # Para Valor esta função só é alcançada DEPOIS que o fluxo Gmail
            # tentou a Página 1 e não conseguiu utilizá-la.
            entry.status = (
                f"{entry.name}: abrindo capa "
                "no navegador interno pelo Proxy Geral…"
            )
            self._refresh_list()

            resolver.resolve_frontpages(
                entry.name,
                callback,
            )

    main_window_cls._start_single_web_resolver = (
        patched_start_single_web_resolver
    )

    # --------------------------------------------------------------
    # 3) UI: se o resolver trouxe pixels do browser, não executar requests.
    # --------------------------------------------------------------

    previous_web_resolved = (
        main_window_cls
        ._web_resolved
    )

    def patched_web_resolved(
        self,
        entry,
        resolver,
        url,
        err,
        generation,
        one_done,
    ):
        if (
            generation
            != self.refresh_generation
        ):
            return

        image_bytes = getattr(
            resolver,
            "last_browser_capture",
            b"",
        )

        if not image_bytes:
            return previous_web_resolved(
                self,
                entry,
                resolver,
                url,
                err,
                generation,
                one_done,
            )

        source_url = str(
            getattr(
                resolver,
                "last_browser_capture_url",
                "",
            )
            or url
            or resolver.last_referer
            or ""
        )

        dest = (
            cache_dir()
            / self.target_date()
            .isoformat()
            / (
                safe_slug(
                    entry.name
                )
                + "-browser.png"
            )
        )

        entry.status = (
            f"{entry.name}: capa carregada no navegador "
            "• validando imagem…"
        )
        self._refresh_list()

        worker = Worker(
            _save_capture_and_score,
            image_bytes,
            dest,
            source_url,
            entry.name,
            entry.mastheads,
            self.target_date(),
            1,
        )

        worker.signals.finished.connect(
            lambda candidate,
            en=entry,
            r=resolver,
            g=generation:
                self._web_candidate_ready(
                    en,
                    r,
                    candidate,
                    g,
                    one_done,
                )
        )

        worker.signals.error.connect(
            lambda message,
            en=entry,
            r=resolver,
            g=generation:
                self._web_candidate_error(
                    en,
                    r,
                    message,
                    g,
                    one_done,
                )
        )

        self._start_worker(
            worker
        )

    main_window_cls._web_resolved = (
        patched_web_resolved
    )

    _INSTALLED = True
