from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def run_node(source: str) -> None:
    completed = subprocess.run(
        ["node", "-e", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr


def test_v108_removes_photo_legend_and_credit_paragraphs_but_keeps_story_body():
    run_node(r"""
const assert = require('node:assert/strict');
const quality = require('./tools/news_extractor/article-quality.js');
const body = [
  'A reportagem informa que a operação começou nesta manhã e terá continuidade durante a semana.',
  'Foto: Agência Brasil',
  'Legenda da foto: militares acompanham a operação na região.',
  'Militares acompanham a cerimônia no cais (Foto: Agência Brasil).',
  'Crédito: Divulgação',
  'Segundo a assessoria, os trabalhos seguem dentro do cronograma previsto e novas informações serão divulgadas.',
].join('\n\n');
const clean = quality.cleanArticleBody(body);
assert.match(clean, /A reportagem informa/);
assert.match(clean, /Segundo a assessoria/);
assert.doesNotMatch(clean, /Foto: Agência Brasil/i);
assert.doesNotMatch(clean, /Legenda da foto/i);
assert.doesNotMatch(clean, /Militares acompanham a cerimônia no cais/i);
assert.doesNotMatch(clean, /Crédito: Divulgação/i);
""")


def test_v108_structural_filter_removes_photo_caption_nodes_not_video_subtitles():
    run_node(r"""
const assert = require('node:assert/strict');
const { stripPhotoCaptionElements } = require('./tools/news_extractor/article-quality.js');
function element({tag='DIV', cls='', text='', attrs={}} = {}) {
  return {
    tagName: tag,
    id: '',
    className: cls,
    textContent: text,
    isConnected: true,
    removed: false,
    getAttribute(name) { return attrs[name] || ''; },
    remove() { this.removed = true; this.isConnected = false; },
  };
}
const photo = element({cls:'media-photo-caption', text:'Marinheiros durante exercício no litoral.'});
const subtitle = element({cls:'video-caption', text:'Legenda automática do vídeo.'});
const doc = {
  querySelectorAll(selector) {
    if (selector === 'figure > p, figure > div > p') return [];
    return [photo, subtitle];
  }
};
assert.equal(stripPhotoCaptionElements(doc), 1);
assert.equal(photo.removed, true);
assert.equal(subtitle.removed, false);
""")


def test_v108_structural_filter_is_bundled_and_installed_before_extractor_modules_load():
    import json

    package = json.loads(read("tools/news_extractor/package.json"))
    assert "article-quality.js" in package["build"]["files"]
    source = read("tools/news_extractor/monitor-bootstrap.js")
    assert source.index("installCaptionSanitizer();") < source.index("installNetworkOptimizations();")
    assert source.index("installNetworkOptimizations();") < source.index(
        "const motor = require('./engine/extrator-materia-v1.25.10-runtime.js')"
    )
    assert "require('./article-quality.js')" in source



def test_v108_caption_sanitizer_is_installed_on_jsdom_before_parsing():
    run_node(r"""
const assert = require('node:assert/strict');
const Module = require('node:module');
const originalLoad = Module._load;
const photo = {
  tagName: 'FIGCAPTION', id: '', className: '', textContent: 'Foto: Agência Brasil',
  isConnected: true, getAttribute() { return ''; },
  remove() { this.isConnected = false; this.removed = true; }
};
const videoCaption = {
  tagName: 'DIV', id: '', className: 'video-caption', textContent: 'Subtítulo do vídeo',
  isConnected: true, getAttribute() { return ''; },
  remove() { this.isConnected = false; this.removed = true; }
};
const document = { querySelectorAll(selector) {
  return selector === 'figure > p, figure > div > p' ? [] : [photo, videoCaption];
} };
class OriginalJSDOM { constructor() { this.window = {document}; } }
const mockJsdom = {JSDOM: OriginalJSDOM};
Module._load = function(request, parent, isMain) {
  if (request === 'jsdom') return mockJsdom;
  return originalLoad.call(this, request, parent, isMain);
};
try {
  const quality = require('./tools/news_extractor/article-quality.js');
  quality.installCaptionSanitizer();
  assert.notEqual(mockJsdom.JSDOM, OriginalJSDOM);
  new mockJsdom.JSDOM('<html></html>');
  assert.equal(photo.removed, true);
  assert.equal(videoCaption.removed, undefined);
} finally {
  Module._load = originalLoad;
}
""")

def test_v108_fast_mode_enforces_two_http_attempts_in_the_fetch_hook():
    source = read("tools/news_extractor/monitor-bootstrap.js")
    assert "const FAST_NETWORK_MAX_ATTEMPTS = 2" in source
    assert "fastRequestAttempts.get(requestKey)" in source
    assert "throw fastRetryLimitError()" in source
    assert "response.status" in source and "[502, 503, 504]" in source
    assert "NEWS PERF V108" in source
    assert "cache HTML temporário restrito ao G1" in source


def test_v108_html_cache_only_buffers_the_known_duplicate_g1_read():
    source = read("tools/news_extractor/monitor-bootstrap.js")
    assert "await response.clone().text()" not in source
    assert "parsedUrl.hostname.toLowerCase() !== 'g1.globo.com'" in source
    assert "declaredLengthHeader" in source
    assert "response.headers.has('set-cookie')" in source
    assert "htmlCache.set(key, buffered)" in source


def test_v108_caption_noise_rules_are_conservative_about_video_subtitles():
    source = read("tools/news_extractor/article-quality.js")
    assert "figcaption" in source
    assert '[class*="caption" i]' in source
    assert "closed[-_ ]?caption|video[-_ ]?caption" in source
    assert "isPhotoCaptionParagraph(value)" in source
