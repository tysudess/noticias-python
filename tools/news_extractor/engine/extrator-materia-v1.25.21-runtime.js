'use strict';

const { JSDOM } = require('jsdom');
const base = require('./extrator-materia-v1.25.20-runtime.js');

const VERSAO = '1.25.21-ZONA-MILITAR-DAN-LIMPEZA-GERAL';
const PORTAIS_ESPECIAIS = new Set([
  'zona-militar.com',
  'defesaaereanaval.com.br'
]);

const SELETORES_CORPO = [
  '[itemprop="articleBody"]',
  'article .td-post-content',
  'article .entry-content',
  'article .post-content',
  'article .article-content',
  'article .post-body',
  '.td-post-content',
  '.entry-content',
  '.post-content',
  '.article-content',
  '.post-body',
  '.content-single',
  '.single-content',
  '.single-post-content',
  '.post-body-content',
  '.elementor-widget-theme-post-content .elementor-widget-container',
  'article',
  'main'
];

const SELETORES_DESCARTAVEIS = [
  'script', 'style', 'noscript', 'template', 'nav', 'footer', 'aside',
  'form', 'button', 'input', 'textarea', 'select', 'iframe', 'figure',
  'figcaption', 'picture', 'img', 'video', 'audio', 'svg', 'canvas',
  '[role="navigation"]', '[role="complementary"]', '[role="contentinfo"]',
  '[class*="advert" i]', '[id*="advert" i]',
  '[class*="publicidade" i]', '[id*="publicidade" i]',
  '[class*="banner" i]', '[class*="newsletter" i]',
  '[class*="social-share" i]', '[class*="share-buttons" i]',
  '[class*="social" i]', '[class*="related" i]', '[id*="related" i]',
  '[class*="recommend" i]', '[class*="recomend" i]',
  '[class*="mais-lid" i]', '[class*="most-read" i]',
  '[class*="breadcrumb" i]', '[class*="comments" i]', '[id*="comments" i]',
  '[class*="comment-form" i]', '[class*="author-box" i]',
  '[class*="post-tags" i]', '[class*="tag-list" i]',
  '[class*="category-list" i]', '.sharedaddy', '.jp-relatedposts',
  '.wp-block-gallery', '.post-share', '.post-navigation'
];

function hostOf(url = '') {
  try {
    return new URL(url).hostname.toLowerCase().replace(/^www\./, '');
  } catch (_) {
    return '';
  }
}

function isPortalEspecial(url = '') {
  const host = hostOf(url);
  return [...PORTAIS_ESPECIAIS].some(domain => host === domain || host.endsWith(`.${domain}`));
}

function norm(value = '') {
  return String(value || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function comparison(value = '') {
  return norm(value)
    .toLocaleLowerCase('pt-BR')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[“”"'‘’]/g, '')
    .replace(/[.:;!?]+$/g, '')
    .trim();
}

function textContentMeta(document, selectors) {
  for (const selector of selectors) {
    try {
      const element = document.querySelector(selector);
      const value = element?.getAttribute('content')
        || element?.getAttribute('datetime')
        || element?.textContent
        || '';
      if (norm(value)) return norm(value);
    } catch (_) {}
  }
  return '';
}

function collectJsonLd(document) {
  const found = [];
  const visit = value => {
    if (!value) return;
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (typeof value !== 'object') return;
    found.push(value);
    if (value['@graph']) visit(value['@graph']);
    if (value.mainEntity) visit(value.mainEntity);
    if (value.subjectOf) visit(value.subjectOf);
    if (value.itemListElement) visit(value.itemListElement);
  };

  for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      visit(JSON.parse(script.textContent || ''));
    } catch (_) {}
  }
  return found;
}

function articleJsonLd(objects) {
  const articleTypes = new Set([
    'article', 'newsarticle', 'reportagenewsarticle', 'blogposting',
    'analysisnewsarticle', 'opinionnewsarticle'
  ]);
  return objects.find(item => {
    const types = Array.isArray(item['@type']) ? item['@type'] : [item['@type']];
    return types.some(type => articleTypes.has(String(type || '').toLowerCase()));
  }) || objects.find(item => item.articleBody || item.headline) || {};
}

function authorName(author) {
  if (!author) return '';
  if (typeof author === 'string') return norm(author).replace(/^por\s+/i, '');
  if (Array.isArray(author)) return author.map(authorName).filter(Boolean).join(', ');
  if (typeof author === 'object') return norm(author.name || author.alternateName || '');
  return '';
}

function isNoiseBlock(value, url = '') {
  const text = norm(value);
  if (!text) return true;
  const plain = comparison(text);
  const short = text.length <= 320;

  const exact = new Set([
    'publicidade', 'publicidad', 'anuncio', 'anuncio publicitario', 'advertisement',
    'ad', 'leia mais', 'leia tambem', 'veja tambem', 'confira tambem',
    'voce tambem pode se interessar', 'voce tambem pode gostar',
    'artigos relacionados', 'noticias relacionadas', 'materias relacionadas',
    'mais noticias', 'ultimas noticias', 'mais lidas', 'comentarios',
    'deixe seu comentario', 'deixe um comentario', 'tags', 'categorias',
    'image', 'imagem', 'foto', 'picture', 'noticia anterior', 'proxima noticia',
    'compartilhe', 'compartilhar', 'share', 'share this', 'siga-nos',
    'inscreva-se', 'assine', 'fechar', 'carregar mais', 'ver mais'
  ]);
  if (exact.has(plain)) return true;

  if (short && /^(?:foto|fotos|imagem|imagens|credito|creditos|fonte|fuente|reproducao|divulgacao)\s*:/i.test(plain)) return true;
  if (short && /^(?:creditos?|credits?)\b/i.test(plain)) return true;
  if (short && /^(?:por favor,?\s*)?(?:digite|escreva) (?:seu )?comentario\b/i.test(plain)) return true;
  if (short && /^(?:noticia anterior|proxima noticia)\b/i.test(plain)) return true;
  if (short && /noticia anterior/.test(plain) && /proxima noticia/.test(plain)) return true;
  if (short && /^(?:publicidade|publicidad|anuncio|advertisement)\b/i.test(plain)) return true;
  if (short && /^(?:tags?|categorias?|compartilhe|compartilhar|share this|siga-nos|inscreva-se|assine nossa newsletter|receba nossas noticias)\b/i.test(plain)) return true;
  if (/^(?:👉\s*)?(?:leia mais|leia tambem|veja tambem|confira tambem|read more|you may also like)\s*:/i.test(text)) return true;
  if (/^(?:👉\s*)?(?:voce tambem pode se interessar por|voce tambem pode gostar|you may also like)\b/i.test(plain)) return true;
  if (/^(?:clique aqui|acesse aqui|continue lendo|ver noticia completa)\b/i.test(plain)) return true;
  if (/^(?:deixe (?:seu )?comentario|escreva (?:seu )?comentario|digite (?:seu )?comentario)\b/i.test(plain)) return true;
  if (/^\d{4}\s+.+todos os direitos reservados\.?$/i.test(text)) return true;
  if (/^(?:http|www\.)\S+$/i.test(text)) return true;
  if (/^\d+\s+(?:comentarios?|respostas?)$/i.test(plain)) return true;

  // Créditos isolados são ruído visual, mas frases jornalísticas sobre fontes
  // permanecem no texto quando não são apenas uma linha de atribuição.
  if (isPortalEspecial(url) && short && /^(?:fonte|fuente|foto|credito)\s*:/i.test(text)) return true;
  return false;
}

function stripInlineNoise(value = '') {
  let text = norm(value);
  if (!text) return '';
  text = text
    .replace(/\s*(?:👉\s*)?(?:leia mais|leia tamb[eé]m|veja tamb[eé]m|confira tamb[eé]m|read more)\s*:\s*(?:https?:\/\/\S+|[^.!?]{0,180})\s*$/iu, '')
    .replace(/\s+(?:compartilhe esta (?:mat[eé]ria|not[ií]cia)|siga-nos nas redes sociais)\s*$/iu, '')
    .trim();
  return text;
}

function linkDensity(element) {
  const total = norm(element?.textContent).length;
  if (!total) return 0;
  let linked = 0;
  for (const anchor of element.querySelectorAll('a')) linked += norm(anchor.textContent).length;
  return linked / total;
}

function removeNoiseElements(root) {
  for (const selector of SELETORES_DESCARTAVEIS) {
    try {
      root.querySelectorAll(selector).forEach(element => element.remove());
    } catch (_) {}
  }
}

function extractBlocks(container, url = '', metadata = {}) {
  const clone = container.cloneNode(true);
  removeNoiseElements(clone);
  const nodes = [...clone.querySelectorAll('h2, h3, p, blockquote, li')];
  const meta = new Set([
    metadata.title, metadata.subtitle, metadata.author, metadata.date
  ].filter(Boolean).map(comparison));
  const blocks = [];
  const seen = new Set();

  for (const node of nodes) {
    const tag = String(node.tagName || '').toLowerCase();
    let text = stripInlineNoise(node.textContent || '');
    if (!text || isNoiseBlock(text, url)) continue;
    if (meta.has(comparison(text))) continue;
    // Listas curtas podem conter especificações ou dados jornalísticos;
    // removemos apenas itens muito curtos ou dominados por links.
    if (tag === 'li' && text.length < 28) continue;
    if ((tag === 'h2' || tag === 'h3') && text.length < 18) continue;
    if (tag === 'p' && text.length < 45) continue;
    if (tag === 'blockquote' && text.length < 35) continue;
    if (linkDensity(node) > 0.50 && text.length < 360) continue;

    const key = comparison(text);
    if (seen.has(key)) continue;
    seen.add(key);
    blocks.push(text);
  }

  const text = blocks.join('\n\n').trim();
  if (text.length < 180 || blocks.length < 2) return null;
  return {
    text,
    blocks: blocks.length,
    score: text.length + Math.min(blocks.length, 24) * 38
  };
}

function extractPortalBody(html, url, current = {}) {
  const dom = new JSDOM(String(html || ''), { url });
  const document = dom.window.document;
  const jsonLd = articleJsonLd(collectJsonLd(document));
  const metadata = {
    title: current.titulo || norm(jsonLd.headline || '') || textContentMeta(document, [
      'meta[property="og:title"]', 'meta[name="twitter:title"]', 'h1'
    ]),
    subtitle: current.subtitulo || norm(jsonLd.description || '') || textContentMeta(document, [
      'meta[property="og:description"]', 'meta[name="description"]'
    ]),
    author: current.autor || authorName(jsonLd.author) || textContentMeta(document, [
      'meta[name="author"]', 'meta[property="article:author"]', '[rel="author"]',
      '.author-name', '.post-author', '.byline'
    ]),
    date: current.data || norm(jsonLd.datePublished || '') || textContentMeta(document, [
      'meta[property="article:published_time"]', 'meta[name="date"]', 'time[datetime]'
    ])
  };

  let best = null;
  const visited = new Set();
  for (const selector of SELETORES_CORPO) {
    let elements = [];
    try { elements = [...document.querySelectorAll(selector)]; } catch (_) {}
    for (const element of elements) {
      if (visited.has(element)) continue;
      visited.add(element);
      const candidate = extractBlocks(element, url, metadata);
      if (candidate && (!best || candidate.score > best.score)) best = candidate;
    }
  }

  if (!best && typeof jsonLd.articleBody === 'string') {
    const text = jsonLd.articleBody
      .replace(/<br\s*\/?\s*>/gi, '\n')
      .replace(/<\/(?:p|div|li|h[1-6])\s*>/gi, '\n\n')
      .replace(/<[^>]*>/g, ' ')
      .split(/\n+|(?<=[.!?])\s+(?=[A-ZÀ-Ý])/u)
      .map(stripInlineNoise)
      .filter(block => block.length >= 45 && !isNoiseBlock(block, url));
    const deduped = [...new Set(text)];
    const joined = deduped.join('\n\n').trim();
    if (joined.length >= 180) best = {
      text: joined,
      blocks: deduped.length,
      score: joined.length + Math.min(deduped.length, 24) * 38
    };
  }

  if (!best) return null;

  const host = hostOf(url);
  const vehicle = host === 'zona-militar.com'
    ? 'Zona Militar'
    : host === 'defesaaereanaval.com.br'
      ? 'Defesa Aérea & Naval'
      : norm(textContentMeta(document, ['meta[property="og:site_name"]'])) || current.veiculo || '';

  return {
    titulo: metadata.title || current.titulo || '',
    subtitulo: metadata.subtitle || current.subtitulo || '',
    autor: metadata.author || current.autor || '',
    data: formatDate(metadata.date || current.data || ''),
    veiculo: vehicle,
    texto: best.text,
    score: best.score
  };
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

function cleanGenericText(value = '', url = '', metadata = {}) {
  const parts = String(value || '')
    .replace(/\r/g, '')
    .split(/\n\s*\n+/)
    .map(stripInlineNoise)
    .filter(Boolean);
  const meta = new Set([
    metadata.titulo, metadata.subtitulo, metadata.autor, metadata.data
  ].filter(Boolean).map(comparison));
  const result = [];
  const seen = new Set();

  for (const part of parts) {
    const text = norm(part);
    if (!text || isNoiseBlock(text, url)) continue;
    if (meta.has(comparison(text))) continue;
    const key = comparison(text);
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(text);
  }
  return result.join('\n\n').trim();
}

function formatArticle(article) {
  const parts = [
    article.url || '',
    '',
    article.veiculo || 'Veículo não identificado',
    '',
    `*${article.titulo || 'Título não identificado'}*`
  ];
  if (article.subtitulo) parts.push('', `_${article.subtitulo}_`);
  parts.push('');
  if (article.autor) parts.push(article.autor);
  parts.push(article.data || 'Data não identificada', '', article.texto || '');
  article.resultado = parts.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
  return article;
}

async function fetchPortalHtml(url) {
  const config = typeof base.carregarConfigProxy === 'function'
    ? base.carregarConfigProxy()
    : {};
  const timeoutMs = Math.max(8000, Math.min(25000, Number(config?.TIMEOUT_MS) || 20000));
  const response = await base.fetchComRetry(url, {
    redirect: 'follow',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
      'Accept-Language': 'pt-BR,pt;q=0.9,es;q=0.8,en;q=0.7',
      'Accept': 'text/html,application/xhtml+xml',
      'Connection': 'close'
    }
  }, {
    timeoutMs,
    tentativas: 1
  });
  if (!response.ok) throw new Error(`HTTP ${response.status} ao acessar a página para localizar o corpo da matéria.`);
  const contentType = response.headers?.get?.('content-type') || '';
  if (contentType && !/html|xhtml/i.test(contentType)) {
    throw new Error(`O site retornou ${contentType}, não uma página HTML.`);
  }
  return response.text();
}

async function extrairMateria(url) {
  const originalUrl = String(url || '').trim();
  const portalEspecial = isPortalEspecial(originalUrl);
  let materia = null;
  let erroBase = null;

  try {
    materia = await base.extrairMateria(originalUrl);
  } catch (error) {
    erroBase = error;
  }

  if (!materia && !portalEspecial) {
    throw erroBase || new Error('Não foi possível extrair o corpo principal da matéria.');
  }

  if (portalEspecial) {
    try {
      const html = await fetchPortalHtml(originalUrl);
      const portal = extractPortalBody(html, originalUrl, materia || {});
      if (portal) {
        const atual = cleanGenericText(materia?.texto || '', originalUrl, materia || {});
        const atualScore = atual.length + Math.min(atual.split(/\n\s*\n+/).filter(Boolean).length, 24) * 38;
        if (!materia) {
          materia = {
            url: originalUrl,
            veiculo: portal.veiculo,
            titulo: portal.titulo,
            subtitulo: portal.subtitulo,
            autor: portal.autor,
            data: portal.data,
            texto: portal.texto,
            origemCorpo: 'seletor-portal-v12521'
          };
        } else if (!atual || atual.length < 260 || portal.score > atualScore + 60) {
          materia.texto = portal.texto;
          materia.origemCorpo = 'seletor-portal-v12521';
          materia.veiculo = materia.veiculo || portal.veiculo;
          materia.titulo = materia.titulo || portal.titulo;
          materia.subtitulo = materia.subtitulo || portal.subtitulo;
          materia.autor = materia.autor || portal.autor;
          materia.data = materia.data || portal.data;
        }
      }
    } catch (portalError) {
      if (!materia) {
        const detalheBase = erroBase?.message || 'o extrator principal não encontrou o artigo';
        throw new Error(
          `Não foi possível extrair a matéria de ${hostOf(originalUrl)}. `
          + `Leitura principal: ${detalheBase}. `
          + `Leitura específica do portal: ${portalError?.message || portalError}`
        );
      }
      materia.avisoPortal = `A leitura específica do portal falhou; foi preservado o resultado principal. ${portalError?.message || portalError}`;
    }
  }

  if (!materia) throw erroBase || new Error('O site não forneceu o conteúdo principal da matéria.');

  materia.url = materia.url || originalUrl;
  materia.texto = cleanGenericText(materia.texto, originalUrl, materia);
  if (!materia.texto || materia.texto.length < 100) {
    throw new Error('O texto encontrado é curto demais após a limpeza. Verifique se o site liberou o conteúdo integral da matéria.');
  }

  return formatArticle(materia);
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  isPortalEspecial,
  extractPortalBody,
  cleanGenericText,
  isNoiseBlock
};
