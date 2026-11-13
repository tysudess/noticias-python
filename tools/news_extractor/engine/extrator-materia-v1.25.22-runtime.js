'use strict';

const { JSDOM } = require('jsdom');
const base = require('./extrator-materia-v1.25.21-runtime.js');

const VERSAO = '1.25.22-PODER-NAVAL-RECUPERACAO';
const PODER_NAVAL_HOST = 'naval.com.br';

function hostOf(url = '') {
  try {
    return new URL(String(url)).hostname.toLowerCase().replace(/^www\./, '');
  } catch (_) {
    return '';
  }
}

function isPoderNaval(url = '') {
  const host = hostOf(url);
  return host === PODER_NAVAL_HOST || host.endsWith(`.${PODER_NAVAL_HOST}`);
}

function norm(value = '') {
  return String(value || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function cleanPoderNavalText(value = '', url = '', metadata = {}) {
  const generic = base.cleanGenericText(value, url, metadata);
  const blocks = String(generic || '')
    .replace(/\r/g, '')
    .split(/\n\s*\n+/)
    .map(norm)
    .filter(Boolean);
  const output = [];
  const seen = new Set();
  const noise = [
    /^(?:publicidade|advertisement|an[uú]ncio)$/i,
    /^(?:leia mais|leia tamb[eé]m|veja tamb[eé]m|not[ií]cias relacionadas|mat[eé]rias relacionadas)\b/i,
    /^(?:deixe (?:seu )?coment[aá]rio|escreva (?:seu )?coment[aá]rio|coment[aá]rios?\s*(?:\(\d+\))?)$/i,
    /^(?:tags?|categorias?)\s*:/i,
    /^(?:fonte|fuente|foto|fotos|imagem|imagens|cr[eé]ditos?|reprodu[cç][aã]o|divulga[cç][aã]o)\s*:/i,
    /^(?:compartilhe|compartilhar|siga-nos|inscreva-se|assine nossa newsletter)\b/i,
    /^(?:post anterior|pr[oó]ximo post|not[ií]cia anterior|pr[oó]xima not[ií]cia)$/i,
    /^\d+\s+coment[aá]rios?$/i,
    /^\u00a9?\s*\d{4}\s+.+todos os direitos reservados\.?$/i,
  ];

  for (let block of blocks) {
    block = block
      .replace(/\s*(?:👉\s*)?(?:leia mais|leia tamb[eé]m|veja tamb[eé]m)\s*:?\s*(?:https?:\/\/\S+)?\s*$/iu, '')
      .replace(/\s+(?:compartilhe esta (?:mat[eé]ria|not[ií]cia)|siga-nos nas redes sociais)\s*$/iu, '')
      .trim();
    if (!block) continue;
    if (noise.some(pattern => pattern.test(block))) continue;
    if (/^https?:\/\//i.test(block) || /^www\./i.test(block)) continue;
    const key = block.toLocaleLowerCase('pt-BR');
    if (seen.has(key)) continue;
    seen.add(key);
    output.push(block);
  }
  return output.join('\n\n').trim();
}

function formatDate(value = '') {
  const text = norm(value);
  if (!text) return '';
  const iso = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]}`;
  const br = text.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/);
  if (br) return `${br[1].padStart(2, '0')}/${br[2].padStart(2, '0')}/${br[3]}`;
  return text;
}

function _meta(document, selectors) {
  for (const selector of selectors) {
    try {
      const node = document.querySelector(selector);
      const value = node?.getAttribute('content')
        || node?.getAttribute('datetime')
        || node?.textContent
        || '';
      if (norm(value)) return norm(value);
    } catch (_) {}
  }
  return '';
}

function _fallbackPoderNavalBody(html, url, current = {}) {
  const dom = new JSDOM(String(html || ''), { url });
  const document = dom.window.document;
  const selectors = [
    '[itemprop="articleBody"]',
    'article .entry-content',
    'article .post-content',
    'article .td-post-content',
    '.entry-content',
    '.post-content',
    '.td-post-content',
    '.post-body',
    '.article-body',
    '#content article',
    '#main article',
    'article',
    'main',
  ];
  const remove = [
    'script', 'style', 'noscript', 'template', 'nav', 'footer', 'aside',
    'form', 'button', 'input', 'textarea', 'select', 'iframe', 'figure',
    'figcaption', 'picture', 'img', 'video', 'audio', 'svg', 'canvas',
    '[role="navigation"]', '[role="complementary"]',
    '[class*="sidebar" i]', '[id*="sidebar" i]',
    '[class*="related" i]', '[id*="related" i]',
    '[class*="comment" i]', '[id*="comment" i]',
    '[class*="share" i]', '[class*="social" i]',
    '[class*="author-box" i]', '[class*="post-tags" i]',
    '[class*="tag-list" i]', '[class*="newsletter" i]',
    '[class*="advert" i]', '[class*="publicidade" i]',
  ];
  const meta = {
    titulo: current.titulo || _meta(document, [
      'meta[property="og:title"]', 'meta[name="twitter:title"]', 'h1', 'title',
    ]),
    subtitulo: current.subtitulo || _meta(document, [
      'meta[property="og:description"]', 'meta[name="description"]',
    ]),
    autor: current.autor || _meta(document, [
      'meta[name="author"]', 'meta[property="article:author"]', '[rel="author"]',
    ]),
    data: current.data || _meta(document, [
      'meta[property="article:published_time"]', 'meta[name="date"]', 'time[datetime]',
    ]),
  };

  let best = null;
  const visited = new Set();
  for (const selector of selectors) {
    let elements = [];
    try { elements = [...document.querySelectorAll(selector)]; } catch (_) {}
    for (const element of elements) {
      if (visited.has(element)) continue;
      visited.add(element);
      const clone = element.cloneNode(true);
      for (const unwanted of remove) {
        try { clone.querySelectorAll(unwanted).forEach(node => node.remove()); } catch (_) {}
      }
      const nodes = [...clone.querySelectorAll('h2,h3,p,blockquote,li')];
      const paragraphs = [];
      const seen = new Set();
      let related = false;
      for (const node of nodes) {
        const tag = String(node.tagName || '').toLowerCase();
        const text = norm(node.textContent);
        if (!text) continue;
        if (/^(?:leia mais|leia tamb[eé]m|veja tamb[eé]m|not[ií]cias relacionadas|mat[eé]rias relacionadas|coment[aá]rios|deixe seu coment[aá]rio)$/i.test(text)) {
          related = true;
          continue;
        }
        if (related && (tag === 'li' || text.length < 90)) continue;
        const cleaned = cleanPoderNavalText(text, url, meta);
        if (!cleaned) continue;
        if ((tag === 'p' && cleaned.length < 35)
          || (tag === 'blockquote' && cleaned.length < 35)
          || (tag === 'li' && cleaned.length < 28)
          || ((tag === 'h2' || tag === 'h3') && cleaned.length < 18)) continue;
        const key = cleaned.toLocaleLowerCase('pt-BR');
        if (seen.has(key)) continue;
        seen.add(key);
        paragraphs.push(cleaned);
      }
      const text = paragraphs.join('\n\n').trim();
      if (text.length < 180 || paragraphs.length < 2) continue;
      const score = text.length + Math.min(paragraphs.length, 24) * 38;
      if (!best || score > best.score) best = { text, score };
    }
  }

  if (!best) return null;
  return {
    url,
    veiculo: 'Poder Naval',
    titulo: meta.titulo || current.titulo || '',
    subtitulo: meta.subtitulo || current.subtitulo || '',
    autor: meta.autor || current.autor || '',
    data: formatDate(meta.data || current.data || ''),
    texto: best.text,
    score: best.score,
  };
}

function extractPoderNavalBody(html, url, current = {}) {
  if (!isPoderNaval(url)) return null;
  let candidate = null;
  try {
    candidate = base.extractPortalBody(html, url, current || {});
  } catch (_) {}

  const fallback = _fallbackPoderNavalBody(html, url, current || {});
  if (!candidate) candidate = fallback;
  else if (fallback && fallback.score > candidate.score + 30) candidate = fallback;
  if (!candidate) return null;

  candidate.url = url;
  candidate.veiculo = 'Poder Naval';
  candidate.texto = cleanPoderNavalText(candidate.texto, url, candidate);
  candidate.score = candidate.texto.length
    + Math.min(candidate.texto.split(/\n\s*\n+/).filter(Boolean).length, 24) * 38;
  return candidate.texto.length >= 180 ? candidate : null;
}

async function fetchPoderNavalHtml(url) {
  const config = typeof base.carregarConfigProxy === 'function'
    ? base.carregarConfigProxy()
    : {};
  const timeoutMs = Math.max(8000, Math.min(30000, Number(config?.TIMEOUT_MS) || 22000));
  const response = await base.fetchComRetry(url, {
    redirect: 'follow',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
      'Accept': 'text/html,application/xhtml+xml',
      'Connection': 'close',
    },
  }, { timeoutMs, tentativas: 2 });

  if (!response.ok) throw new Error(`HTTP ${response.status} ao acessar o artigo do Poder Naval.`);
  const contentType = response.headers?.get?.('content-type') || '';
  if (contentType && !/html|xhtml/i.test(contentType)) {
    throw new Error(`O Poder Naval retornou ${contentType}, não uma página HTML.`);
  }
  return response.text();
}

function formatArticle(article) {
  const parts = [
    article.url || '',
    '',
    'Poder Naval',
    '',
    `*${article.titulo || 'Título não identificado'}*`,
  ];
  if (article.subtitulo) parts.push('', `_${article.subtitulo}_`);
  parts.push('');
  if (article.autor) parts.push(article.autor);
  parts.push(article.data || 'Data não identificada', '', article.texto || '');
  article.resultado = parts.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
  return article;
}

async function extrairMateria(url) {
  const originalUrl = String(url || '').trim();
  if (!isPoderNaval(originalUrl)) return base.extrairMateria(originalUrl);

  let materia = null;
  let erroPrincipal = null;
  try {
    materia = await base.extrairMateria(originalUrl);
  } catch (error) {
    erroPrincipal = error;
  }

  let portal = null;
  let erroPortal = null;
  try {
    const html = await fetchPoderNavalHtml(originalUrl);
    portal = extractPoderNavalBody(html, originalUrl, materia || {});
  } catch (error) {
    erroPortal = error;
  }

  if (!materia && !portal) {
    const primary = erroPrincipal?.message || 'o extrator principal não identificou o corpo do artigo';
    const fallback = erroPortal?.message || 'a leitura específica não encontrou blocos editoriais suficientes';
    throw new Error(`Poder Naval: não foi possível localizar o corpo da matéria. Leitura principal: ${primary}. Leitura do portal: ${fallback}`);
  }

  if (!materia) {
    materia = {
      url: originalUrl,
      veiculo: 'Poder Naval',
      titulo: portal.titulo,
      subtitulo: portal.subtitulo,
      autor: portal.autor,
      data: portal.data,
      texto: portal.texto,
      origemCorpo: 'seletor-poder-naval-v12522',
    };
  } else if (portal) {
    const actual = cleanPoderNavalText(materia.texto, originalUrl, materia);
    const actualScore = actual.length
      + Math.min(actual.split(/\n\s*\n+/).filter(Boolean).length, 24) * 38;
    if (!actual || actual.length < 260 || portal.score > actualScore + 30) {
      materia.texto = portal.texto;
      materia.origemCorpo = 'seletor-poder-naval-v12522';
      materia.titulo = materia.titulo || portal.titulo;
      materia.subtitulo = materia.subtitulo || portal.subtitulo;
      materia.autor = materia.autor || portal.autor;
      materia.data = materia.data || portal.data;
    }
  }

  materia.url = originalUrl;
  materia.veiculo = 'Poder Naval';
  materia.texto = cleanPoderNavalText(materia.texto, originalUrl, materia);
  if (!materia.texto || materia.texto.length < 100) {
    throw new Error('Poder Naval: o texto localizado ficou curto demais após a limpeza. Confira se o link é de uma matéria e se o portal liberou o conteúdo.');
  }
  return formatArticle(materia);
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  isPoderNaval,
  extractPoderNavalBody,
  cleanPoderNavalText,
};
