from __future__ import annotations

import json

from PySide6.QtCore import QTimer, QUrl

from .web_resolver import (
    FrontPageResolver,
    CURRENT_WEBP_JS,
    _cleanup,
)


META_COVER_JS = r"""
(function(expected){
  function clean(u){
    try{
      if(!u)return '';
      return new URL(
        String(u)
          .replace(/\\\//g,'/')
          .replace(/&amp;/g,'&'),
        document.baseURI
      ).href;
    }catch(e){
      return String(u||'');
    }
  }

  function valid(u){
    var low=String(u||'').toLowerCase();

    if(!/^https?:/i.test(u)) return false;
    if(low.indexOf('sports')>=0) return false;
    if(low.indexOf('logo')>=0) return false;
    if(low.indexOf('icon')>=0) return false;
    if(low.indexOf('avatar')>=0) return false;

    return (
      low.indexOf('.webp')>=0 ||
      low.indexOf('.jpg')>=0 ||
      low.indexOf('.jpeg')>=0 ||
      low.indexOf('.png')>=0
    );
  }

  var candidates=[];

  function push(u,score,where){
    u=clean(u);
    if(!valid(u)) return;

    var low=u.toLowerCase();

    if(
      expected.indexOf('WASHINGTON POST')>=0 &&
      (
        low.indexOf('washington-post')>=0 ||
        low.indexOf('washington_post')>=0 ||
        low.indexOf('washingtonpost')>=0
      )
    ){
      score+=1000;
    }

    candidates.push({
      url:u,
      score:score,
      where:where
    });
  }

  try{
    var selectors=[
      'meta[property="og:image"]',
      'meta[property="og:image:url"]',
      'meta[name="twitter:image"]',
      'meta[name="twitter:image:src"]',
      'link[rel="image_src"]'
    ];

    for(var s=0;s<selectors.length;s++){
      var nodes=document.querySelectorAll(selectors[s]);

      for(var i=0;i<nodes.length;i++){
        var n=nodes[i];

        push(
          n.getAttribute('content') ||
          n.getAttribute('href'),
          900,
          'meta'
        );
      }
    }
  }catch(e){}

  try{
    var imgs=document.images||[];

    for(var j=0;j<imgs.length;j++){
      var im=imgs[j];

      var info=(
        (im.alt||'')+' '+
        (im.title||'')+' '+
        (im.getAttribute('data-title')||'')+' '+
        (im.getAttribute('data-caption')||'')
      ).toUpperCase();

      var score=100;

      if(
        expected.indexOf('WASHINGTON POST')>=0 &&
        info.indexOf('WASHINGTON POST')>=0
      ){
        score+=800;
      }

      if((im.naturalWidth||0)>=300) score+=100;
      if((im.naturalHeight||0)>=450) score+=100;

      push(
        im.currentSrc || im.src,
        score,
        'img'
      );

      var attrs=[
        'data-src',
        'data-lazy-src',
        'data-original',
        'data-image',
        'data-url',
        'data-full'
      ];

      for(var a=0;a<attrs.length;a++){
        push(
          im.getAttribute(attrs[a]),
          score-10,
          attrs[a]
        );
      }

      var srcset=(
        im.getAttribute('srcset') ||
        im.getAttribute('data-srcset') ||
        ''
      ).split(',');

      for(var k=0;k<srcset.length;k++){
        var u=srcset[k].trim().split(/\s+/)[0];
        push(u,score-5,'srcset');
      }
    }
  }catch(e){}

  try{
    var scripts=document.querySelectorAll(
      'script[type="application/ld+json"]'
    );

    for(var q=0;q<scripts.length;q++){
      var text=scripts[q].textContent||'';

      var urls=text.match(
        /https?:\\\/?\\\/?[^"'\\s<>]+\\.(?:webp|jpe?g|png)[^"'\\s<>]*/ig
      ) || [];

      for(var z=0;z<urls.length;z++){
        push(
          urls[z].replace(/\\\//g,'/'),
          700,
          'jsonld'
        );
      }
    }
  }catch(e){}

  candidates.sort(function(a,b){
    return b.score-a.score;
  });

  return candidates.length
    ? JSON.stringify(candidates[0])
    : '';
})(%EXPECTED%)
"""


class RobustFrontPageResolver(FrontPageResolver):
    """Resolver reforçado para Washington Post e Valor.

    Além do detector ampliado, dá tempo suficiente para FrontPages concluir
    lazy-load, scripts e anúncios antes de considerar a capa indisponível.
    """

    SOURCE_TIMEOUT_MS = 45000
    MAX_SCAN_ATTEMPTS = 10

    def _start_next_source(self):
        self.browser.destroy_page()
        self._source_index += 1

        if self._source_index >= len(self._sources):
            cb = self.done_cb
            self.done_cb = None
            self._finished = True

            if cb:
                cb(
                    None,
                    "capa correta não confirmada "
                    "(timeout/capa não localizada)",
                )
            return

        self._generation += 1
        generation = self._generation
        self._finished = False
        self._scan_count = 0

        source = self._sources[
            self._source_index
        ]

        self.last_referer = source
        self.last_cookie_header = ""

        self.progress.emit(
            "Abrindo FrontPages…"
            if "frontpages.com" in source
            else "Tentando PressReader…"
        )

        self.page = self.browser.new_page(
            lambda _u, _g=generation: None
        )
        self.page.loadFinished.connect(
            lambda ok, gen=generation:
            self._after_load(ok, gen)
        )
        self.page.load(QUrl(source))

        # FrontPages pode manter a página em loading por publicidade/lazy-load.
        # Fazemos uma inspeção antecipada sem cancelar a navegação.
        QTimer.singleShot(
            10000,
            lambda gen=generation:
            self._scan(gen)
            if self._active(gen)
            else None,
        )

        QTimer.singleShot(
            self.SOURCE_TIMEOUT_MS,
            lambda gen=generation:
            self._source_failed(
                "timeout do navegador interno",
                gen,
            ),
        )

    def _scan(self, generation: int):
        if not self._active(generation) or not self.page:
            return

        self._scan_count += 1
        source = self._sources[self._source_index]

        if "frontpages.com" not in source:
            self._scan_standard(generation)
            return

        expected = (
            "WASHINGTON POST"
            if self._name == "THE WASHINGTON POST"
            else "VALOR ECONOMICO"
        )

        js = META_COVER_JS.replace(
            "%EXPECTED%",
            json.dumps(expected),
        )

        self.page.runJavaScript(
            js,
            lambda r, gen=generation: self._meta_result(
                r,
                gen,
            ),
        )

    def _direct_result(self, result, generation: int) -> None:
        if not self._active(generation):
            return

        url = _cleanup(str(result or ""))
        low = url.lower()

        expected = (
            url.startswith("https://www.frontpages.com/g/")
            and f"/{self._slug}-" in low
            and ".webp" in low
            and not (
                self._slug == "the-washington-post"
                and "sports" in low
            )
        )

        if expected:
            self._success(
                url,
                generation,
            )
            return

        if self._scan_count < self.MAX_SCAN_ATTEMPTS:
            QTimer.singleShot(
                900,
                lambda gen=generation:
                self._scan(gen),
            )
            return

        self._scan_standard(
            generation
        )

    def _meta_result(self, result, generation: int) -> None:
        if not self._active(generation):
            return

        raw = str(result or "").strip()

        if raw:
            try:
                data = json.loads(raw)
                url = _cleanup(
                    str(data.get("url") or "")
                )
                low = url.lower()

                if (
                    url.startswith(("http://", "https://"))
                    and not (
                        self._name == "THE WASHINGTON POST"
                        and "sports" in low
                    )
                ):
                    self._success(url, generation)
                    return
            except Exception:
                pass

        # Fallback para o detector legado /g/...webp.
        js = CURRENT_WEBP_JS.replace(
            "%SLUG%",
            json.dumps(self._slug),
        )

        self.page.runJavaScript(
            js,
            lambda r, gen=generation: self._direct_result(
                r,
                gen,
            ),
        )
