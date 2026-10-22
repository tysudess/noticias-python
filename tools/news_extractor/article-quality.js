'use strict';

function stripPhotoCaptionElements(document) {
  if (!document || typeof document.querySelectorAll !== 'function') return 0;

  const selector = [
    'figcaption',
    '[itemprop~="caption"]',
    '.wp-caption-text',
    '[class*="caption" i]',
    '[class*="legenda" i]',
    '[class*="photo-credit" i]',
    '[class*="photo_credit" i]',
    '[class*="image-credit" i]',
    '[class*="image_credit" i]',
    '[class*="photo-credit-line" i]',
    '[class*="credito-foto" i]',
    '[class*="credito-imagem" i]',
    '[id*="caption" i]',
    '[id*="legenda" i]',
    '[data-testid*="caption" i]',
    '[data-testid*="legenda" i]',
    '[aria-label*="caption" i]',
    '[aria-label*="legenda" i]'
  ].join(',');

  let removed = 0;
  try {
    const elements = Array.from(document.querySelectorAll(selector));
    for (const element of elements) {
      if (!element || element.isConnected === false) continue;
      const tag = String(element.tagName || '').toUpperCase();
      if (['HTML', 'BODY', 'MAIN', 'ARTICLE'].includes(tag)) continue;

      const hint = [
        element.id,
        typeof element.className === 'string' ? element.className : '',
        element.getAttribute && element.getAttribute('itemprop'),
        element.getAttribute && element.getAttribute('data-testid'),
        element.getAttribute && element.getAttribute('aria-label'),
        element.getAttribute && element.getAttribute('title')
      ].filter(Boolean).join(' ');
      if (/(?:closed[-_ ]?caption|video[-_ ]?caption|subtitles?|subtitulo|transcript)/i.test(hint)) continue;

      const text = String(element.textContent || '').replace(/\s+/g, ' ').trim();
      if (text.length > 1200) continue;
      const explicitCaption = tag === 'FIGCAPTION'
        || /(?:wp[-_ ]?caption|caption|legenda|photo|image|foto|imagem)/i.test(hint)
        || /(?:photo|image|foto|imagem)[-_ ]?(?:credit|cr[eé]dito|description|legenda)/i.test(hint);
      if (!explicitCaption) continue;
      if (text.length > 720 && tag !== 'FIGCAPTION' && !/wp[-_ ]?caption[-_ ]?text/i.test(hint)) continue;

      try {
        element.remove();
        removed += 1;
      } catch (_) {}
    }

    // Alguns portais colocam a legenda num <p> sem classe, dentro do figure.
    // Só removemos parágrafos curtos em figuras com imagem; texto longo é mantido.
    for (const paragraph of Array.from(document.querySelectorAll('figure > p, figure > div > p'))) {
      if (!paragraph || paragraph.isConnected === false) continue;
      const figure = paragraph.closest && paragraph.closest('figure');
      if (!figure || !figure.querySelector('img, picture')) continue;
      const text = String(paragraph.textContent || '').replace(/\s+/g, ' ').trim();
      if (text && text.length <= 420) {
        try {
          paragraph.remove();
          removed += 1;
        } catch (_) {}
      }
    }
  } catch (error) {
    console.warn('NEWS QUALITY: não foi possível remover todas as legendas estruturais:', error.message);
  }
  return removed;
}

function installCaptionSanitizer() {
  try {
    const jsdom = require('jsdom');
    const OriginalJSDOM = jsdom.JSDOM;
    if (!OriginalJSDOM || OriginalJSDOM._centralPhotoCaptionSanitizer) return;

    class CaptionSafeJSDOM extends OriginalJSDOM {
      constructor(...args) {
        super(...args);
        try {
          stripPhotoCaptionElements(this.window && this.window.document);
        } catch (_) {}
      }
    }
    Object.defineProperty(CaptionSafeJSDOM, '_centralPhotoCaptionSanitizer', { value: true });
    Object.defineProperty(jsdom, 'JSDOM', {
      value: CaptionSafeJSDOM,
      configurable: true,
      enumerable: true,
      writable: true
    });
    console.log('NEWS QUALITY: remoção estrutural de legendas de fotos ativada.');
  } catch (error) {
    console.warn('NEWS QUALITY: filtro estrutural de legendas indisponível:', error.message);
  }
}

function normalizeParagraph(value) {
  return String(value || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function isPhotoCaptionParagraph(paragraph) {
  const value = normalizeParagraph(paragraph);
  if (!value || value.length > 520) return false;
  return (
    /^(?:legenda(?:\s+da\s+(?:foto|imagem))?|foto|fotos|imagem|imagens|cr[eé]dito(?:s)?(?:\s+da\s+(?:foto|imagem))?|descri[cç][aã]o\s+da\s+imagem)\s*[:：]/i.test(value)
    || /(?:^|[|—–])\s*(?:foto|imagem|cr[eé]dito|legenda)\s*[:：]\s*/i.test(value)
    // Algumas legendas aparecem como descrição curta seguida de crédito entre
    // parênteses, sem começar por \"Foto:\". Nesse formato removemos o bloco
    // inteiro apenas quando ele termina claramente com o crédito.
    || /^.{18,360}\s*\(\s*(?:foto|imagem|cr[eé]dito|legenda)\s*[:：]\s*[^)]{2,160}\)\s*[.!?]?\s*$/i.test(value)
    || /^(?:foto|imagem)\s+(?:de|por)\s+.{1,150}$/i.test(value)
    || /^(?:reprodu[cç][aã]o|divulga[cç][aã]o|arquivo pessoal|arquivo da fam[ií]lia|getty images|afp|reuters|ag[eê]ncia brasil)(?:\s*[/|—–-].*)?$/i.test(value)
  );
}

function isStandaloneNoise(paragraph) {
  const value = normalizeParagraph(paragraph);
  if (!value || value.length > 520) return false;
  return (
    /^(?:publicidade|anúncio|anuncio|compartilhe|continue lendo)$/i.test(value)
    || /^(?:leia|veja|confira)\s+(?:também|tambem|mais)\b/i.test(value)
    || /^(?:conteúdos?|matérias?|notícias?)\s+relacionad[oa]s?\b/i.test(value)
    || /^(?:assine|inscreva-se|receba)\s+(?:o|a|os|as|nossa|nosso|nossas|nossos|as notícias|as noticias|a newsletter|nossa newsletter)\b/i.test(value)
    || /^(?:foto|fotos|imagem|imagens|crédito|créditos|credito|creditos|legenda)\s*[:：]/i.test(value)
    || isPhotoCaptionParagraph(value)
  );
}

function cleanArticleBody(text) {
  const original = String(text || '').trim();
  const paragraphs = original
    .split(/\n\s*\n+/)
    .map(normalizeParagraph)
    .filter(Boolean);
  const seen = new Set();
  const clean = [];

  for (const paragraph of paragraphs) {
    if (isStandaloneNoise(paragraph)) continue;
    const key = paragraph.toLocaleLowerCase('pt-BR');
    // Deduplica parágrafos longos repetidos pelo DOM, sem remover nomes,
    // subtítulos curtos ou referências breves que podem aparecer de novo.
    if (paragraph.length >= 70 && seen.has(key)) continue;
    if (paragraph.length >= 70) seen.add(key);
    clean.push(paragraph);
  }
  return clean.join('\n\n').trim();
}

module.exports = {
  normalizeParagraph,
  isPhotoCaptionParagraph,
  isStandaloneNoise,
  cleanArticleBody,
  stripPhotoCaptionElements,
  installCaptionSanitizer
};
