const { JSDOM } = require('jsdom');
const base = require('./extrator-materia-v1.25.10-runtime-base.js');

const VERSAO = '1.25.11-FALLBACKS-PORTAIS-G1-AMP-DAN-SUBTITULO';

function norm(v = '') {
  return String(v || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .trim();
}

function host(url = '') {
  try { return new URL(url).hostname.toLowerCase(); } catch (_) { return ''; }
}

function formatar(m) {
  const p = [m.url, '', m.veiculo, '', `*${m.titulo || 'Título não identificado'}*`];
  if (m.subtitulo) p.push('', `_${m.subtitulo}_`);
  p.push('');
  if (m.autor) p.push(m.autor);
  p.push(m.data || 'Data não identificada', '', m.texto || '');
  m.resultado = p.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
  return m;
}

function meta(doc, seletores = []) {
  for (const seletor of seletores) {
    const el = doc.querySelector(seletor);
    if (!el) continue;
    const valor = norm(el.getAttribute('content') || el.getAttribute('datetime') || el.textContent || '');
    if (valor) return valor;
  }
  return '';
}

function jsonLdObjetos(doc) {
  const saida = [];
  const visitar = valor => {
    if (!valor) return;
    if (Array.isArray(valor)) { valor.forEach(visitar); return; }
    if (typeof valor !== 'object') return;
    saida.push(valor);
    if (Array.isArray(valor['@graph'])) valor['@graph'].forEach(visitar);
  };
  for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
    try { visitar(JSON.parse(script.textContent || '')); } catch (_) {}
  }
  return saida;
}

function artigoLd(doc) {
  const objetos = jsonLdObjetos(doc);
  return objetos.find(o => /(?:NewsArticle|Article|ReportageNewsArticle)/i.test(String(o['@type'] || ''))) || {};
}

function nomeAutor(valor) {
  if (!valor) return '';
  if (Array.isArray(valor)) return valor.map(nomeAutor).filter(Boolean).join(' e ');
  if (typeof valor === 'object') return norm(valor.name || '');
  return norm(valor);
}

function veiculoPorHost(h = '') {
  if (h === 'www.zona-militar.com' || h === 'zona-militar.com') return 'Zona Militar';
  if (h === 'www.revistafatorbrasil.com.br' || h === 'revistafatorbrasil.com.br') return 'Fator Brasil';
  if (h === 'www.bnews.com.br' || h === 'bnews.com.br') return 'BNews';
  if (h === 'g1.globo.com') return 'G1';
  if (h === 'www.defesaaereanaval.com.br' || h === 'defesaaereanaval.com.br') return 'Defesa Aérea & Naval';
  return '';
}

function dataDaUrl(url = '') {
  try {
    const m = new URL(url).pathname.match(/\/(20\d{2})\/(0?[1-9]|1[0-2])\/(0?[1-9]|[12]\d|3[01])(?:\/|$)/);
    if (!m) return '';
    return `${String(m[3]).padStart(2, '0')}/${String(m[2]).padStart(2, '0')}/${m[1]}`;
  } catch (_) { return ''; }
}

function dataPt(texto = '') {
  const t = norm(texto).toLowerCase();
  const direta = t.match(/\b(\d{1,2})\/(\d{1,2})\/(20\d{2})\b/);
  if (direta) return `${direta[1].padStart(2, '0')}/${direta[2].padStart(2, '0')}/${direta[3]}`;
  const meses = { janeiro:1, fevereiro:2, marco:3, março:3, abril:4, maio:5, junho:6, julho:7, agosto:8, setembro:9, outubro:10, novembro:11, dezembro:12 };
  const m = t.match(/\b(\d{1,2})(?:\s+de)?\s+(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro),?(?:\s+de)?\s+(20\d{2})\b/i);
  if (!m) return '';
  const chave = m[2].replace('marco', 'março');
  const mes = meses[chave];
  return mes ? `${m[1].padStart(2, '0')}/${String(mes).padStart(2, '0')}/${m[3]}` : '';
}

function dataDocumento(doc, ld, url) {
  const candidatos = [
    ld.datePublished,
    meta(doc, ['meta[property="article:published_time"]', 'meta[name="date"]', 'meta[name="publish-date"]', 'time[datetime]']),
    ...[...doc.querySelectorAll('time, [class*="date" i], [class*="publish" i]')].slice(0, 12).map(el => norm(el.getAttribute('datetime') || el.textContent))
  ].filter(Boolean);
  for (const c of candidatos) {
    const f = dataPt(c) || base.formatarData(c);
    if (f) return f;
  }
  return dataDaUrl(url) || 'Data não identificada';
}

function autorDocumento(doc, ld) {
  const doLd = nomeAutor(ld.author);
  if (doLd) return doLd.replace(/^por\s+/i, '').trim();
  const doMeta = meta(doc, ['meta[name="author"]', 'meta[property="article:author"]']);
  if (doMeta && doMeta.length <= 120) return doMeta.replace(/^por\s+/i, '').trim();
  const seletores = ['[rel="author"]', '[class*="author-name" i]', '[class*="author__name" i]', '.author a', '.autor a', '[class~="author"]'];
  for (const seletor of seletores) {
    for (const el of doc.querySelectorAll(seletor)) {
      const t = norm(el.textContent).replace(/^por\s+/i, '').trim();
      if (t.length >= 3 && t.length <= 100 && !/^(?:por|autor|redação|redacao)$/i.test(t)) return t;
    }
  }
  return '';
}

function tituloDocumento(doc, ld) {
  return norm(doc.querySelector('h1')?.textContent || ld.headline || meta(doc, ['meta[property="og:title"]', 'meta[name="twitter:title"]']) || doc.title || '');
}

function subtituloDocumento(doc, ld, url, titulo) {
  const h = host(url);
  if (h === 'www.zona-militar.com' || h === 'zona-militar.com') return '';
  let s = '';
  const seletores = ['[class*="subtitle" i]', '[class*="subtitulo" i]', '[class*="subheadline" i]', '[class*="article-lead" i]', '[class*="entry-summary" i]', '[class*="excerpt" i]', '[class*="dek" i]'];
  for (const seletor of seletores) {
    const candidatos = [...doc.querySelectorAll(seletor)].map(el => norm(el.textContent)).filter(t => t.length >= 25 && t.length <= 650);
    if (candidatos.length) { s = candidatos[0]; break; }
  }
  if (!s && (h.includes('revistafatorbrasil.com.br') || h.includes('bnews.com.br'))) {
    s = norm(ld.description || meta(doc, ['meta[property="og:description"]', 'meta[name="description"]', 'meta[name="twitter:description"]']));
  }
  if (s && norm(s).toLowerCase() === norm(titulo).toLowerCase()) return '';
  if (/^(?:portal e tv fator brasil|bnews|zona militar)\b/i.test(s) && s.length < 120) return '';
  return s;
}

function densidadeLinks(el) {
  const total = norm(el.textContent).length;
  if (!total) return 0;
  let links = 0;
  for (const a of el.querySelectorAll('a')) links += norm(a.textContent).length;
  return links / total;
}

function ehLixoFallback(t, h, autor = '') {
  const x = norm(t);
  if (!x) return true;
  if (/^(?:publicidade|anúncio|anuncio|compartilhar|ouvir|salvar)$/i.test(x)) return true;
  if (/^(?:👉\s*)?leia\s+mais\s*:/i.test(x)) return true;
  if (/^(?:📌\s*)?você\s+tamb[eé]m\s+pode\s+se\s+interessar/i.test(x)) return true;
  if (/^siga\s+(?:o\s+)?bnews\b/i.test(x)) return true;
  if (/^receba\s+(?:as|nossas)\s+not[ií]cias\b/i.test(x)) return true;
  if (/^classifica[cç][aã]o\s+indicativa\b/i.test(x)) return true;
  if (/^tags?\b/i.test(x)) return true;
  if (/^por\s+favor\s+deje\s+su\s+comentario/i.test(x)) return true;
  if (h.includes('zona-militar.com') && autor && x.startsWith(autor) && /editor|analista|licenciado/i.test(x)) return true;
  return false;
}

function devePararFallback(t, h, autor = '') {
  const x = norm(t);
  if (/^por\s+favor\s+deje\s+su\s+comentario/i.test(x)) return true;
  if (/^classifica[cç][aã]o\s+indicativa\b/i.test(x)) return true;
  if (h.includes('zona-militar.com') && autor && x.startsWith(autor) && /editor|analista|licenciado/i.test(x)) return true;
  return false;
}

function candidatosContainer(doc, h) {
  const seletores = [];
  if (h.includes('zona-militar.com')) seletores.push('.td-post-content', '.entry-content', 'article');
  if (h.includes('revistafatorbrasil.com.br')) seletores.push('article', '.entry-content', '.post-content', '.content-single', 'main');
  if (h.includes('bnews.com.br')) seletores.push('article', '.post-content', '.entry-content', '[class*="article-content" i]', 'main');
  seletores.push('article', '[itemprop="articleBody"]', '.entry-content', '.post-content', 'main');
  const encontrados = [];
  const vistos = new Set();
  for (const seletor of seletores) {
    for (const el of doc.querySelectorAll(seletor)) {
      if (!vistos.has(el)) { vistos.add(el); encontrados.push(el); }
    }
  }
  return encontrados;
}

function pontuarContainer(el) {
  let pontos = 0;
  for (const p of el.querySelectorAll('p, blockquote')) {
    const t = norm(p.textContent);
    if (t.length >= 60) pontos += Math.min(t.length, 1200);
  }
  return pontos;
}

function corpoDocumento(doc, url, metadados) {
  const h = host(url);
  const containers = candidatosContainer(doc, h).sort((a, b) => pontuarContainer(b) - pontuarContainer(a));
  const container = containers[0] || doc.body;
  if (!container) return '';
  const metaSet = new Set([metadados.titulo, metadados.subtitulo, metadados.autor, metadados.data].filter(Boolean).map(x => norm(x).toLowerCase()));
  const saida = [];
  let iniciado = false;
  let pulandoRelacionados = false;
  for (const el of container.querySelectorAll('p, h2, h3, blockquote, li')) {
    const t = norm(el.textContent);
    if (!t || metaSet.has(t.toLowerCase())) continue;
    if (devePararFallback(t, h, metadados.autor)) break;
    if (/^(?:👉\s*)?leia\s+mais\s*:/i.test(t) || /^(?:📌\s*)?você\s+tamb[eé]m\s+pode\s+se\s+interessar/i.test(t)) {
      pulandoRelacionados = true;
      continue;
    }
    const tag = String(el.tagName || '').toLowerCase();
    if (pulandoRelacionados) {
      if (tag === 'li') continue;
      if ((tag === 'p' || tag === 'blockquote') && t.length >= 90) pulandoRelacionados = false;
      else continue;
    }
    if (ehLixoFallback(t, h, metadados.autor)) continue;
    if (densidadeLinks(el) > 0.72 && t.length < 320) continue;
    if (!iniciado) {
      if (!['p', 'blockquote'].includes(tag) || t.length < 70) continue;
      iniciado = true;
    }
    if (tag === 'li' && t.length < 80) continue;
    if (saida[saida.length - 1] !== t) saida.push(t);
  }
  return saida.join('\n\n').trim();
}

function extrairFallbackDoHtml(html, url) {
  const dom = new JSDOM(String(html || ''), { url });
  const doc = dom.window.document;
  const ld = artigoLd(doc);
  const h = host(url);
  const titulo = tituloDocumento(doc, ld).replace(/\s+[|–—-]\s+(?:Zona Militar|Portal e TV Fator Brasil|BNews)\s*$/i, '').trim();
  const subtitulo = subtituloDocumento(doc, ld, url, titulo);
  const autor = autorDocumento(doc, ld);
  const data = dataDocumento(doc, ld, url);
  const veiculo = veiculoPorHost(h) || norm(meta(doc, ['meta[property="og:site_name"]', 'meta[name="application-name"]'])) || h.replace(/^www\./, '');
  const metadados = { titulo, subtitulo, autor, data };
  const texto = corpoDocumento(doc, url, metadados);
  if (!titulo || texto.length < 180) throw new Error('Fallback HTML não encontrou corpo suficiente da matéria.');
  return formatar({ url, veiculo, titulo, subtitulo, autor, data, texto });
}

function ehSubtituloDatelineDAN(subtitulo = '') {
  const s = norm(subtitulo);
  return /^[^.!?]{2,180}:\s*\d{1,2}\s+de\s+[a-zç]+\s+de\s+20\d{2}\s*[–—-]\s+.{30,}$/i.test(s);
}

function corrigirMateria(m) {
  const h = host(m.url);
  m.titulo = norm(m.titulo);
  m.subtitulo = norm(m.subtitulo);
  m.autor = norm(m.autor);
  m.texto = String(m.texto || '').trim();

  if ((h === 'www.defesaaereanaval.com.br' || h === 'defesaaereanaval.com.br') && ehSubtituloDatelineDAN(m.subtitulo)) {
    const lead = m.subtitulo;
    if (!norm(m.texto).toLowerCase().startsWith(norm(lead).toLowerCase().slice(0, 80))) {
      m.texto = `${lead}\n\n${m.texto}`.trim();
    }
    m.subtitulo = '';
  }

  return formatar(m);
}

function montarAlternativas(url = '') {
  const saida = [];
  try {
    const u = new URL(url);
    const h = u.hostname.toLowerCase();
    if (h === 'g1.globo.com') {
      if (u.pathname.startsWith('/google/amp/')) {
        const v = new URL(u.toString());
        v.pathname = u.pathname.replace(/^\/google\/amp/, '');
        saida.push(v.toString());
      } else {
        const v = new URL(u.toString());
        v.pathname = `/google/amp${u.pathname}`;
        saida.push(v.toString());
      }
    }
    if (h === 'www.bnews.com.br' || h === 'bnews.com.br') {
      const v = new URL(u.toString());
      if (u.pathname.startsWith('/amp/')) v.pathname = u.pathname.replace(/^\/amp/, '');
      else v.pathname = `/amp${u.pathname.startsWith('/') ? '' : '/'}${u.pathname}`;
      saida.push(v.toString());
    }
  } catch (_) {}
  return [...new Set(saida)].filter(x => x && x !== url);
}

function alvoFallback(url = '') {
  const h = host(url);
  return h === 'www.zona-militar.com' || h === 'zona-militar.com' ||
    h === 'www.revistafatorbrasil.com.br' || h === 'revistafatorbrasil.com.br' ||
    h === 'www.bnews.com.br' || h === 'bnews.com.br';
}

async function baixarHtml(url) {
  const cfg = base.carregarConfigProxy();
  const r = await base.fetchComRetry(url, {
    redirect: 'follow',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
      'Accept': 'text/html,application/xhtml+xml',
      'Connection': 'close'
    }
  }, { timeoutMs: Math.max(5000, Number(cfg.TIMEOUT_MS) || 45000), tentativas: 3 });
  if (!r.ok) throw new Error(`HTTP ${r.status} ao acessar a página no fallback.`);
  return await r.text();
}

async function extrairMateria(url) {
  const original = String(url || '').trim();
  const tentativas = [original, ...montarAlternativas(original)];
  let ultimoErro = null;

  for (const tentativa of tentativas) {
    try {
      const m = await base.extrairMateria(tentativa);
      m.url = original;
      return corrigirMateria(m);
    } catch (erro) {
      ultimoErro = erro;
    }
  }

  if (alvoFallback(original)) {
    for (const tentativa of tentativas) {
      try {
        const html = await baixarHtml(tentativa);
        const m = extrairFallbackDoHtml(html, tentativa);
        m.url = original;
        return corrigirMateria(m);
      } catch (erro) {
        ultimoErro = erro;
      }
    }
  }

  throw ultimoErro || new Error('Não foi possível extrair a matéria.');
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  corrigirMateria,
  montarAlternativas,
  extrairFallbackDoHtml,
  ehSubtituloDatelineDAN,
  dataDaUrl,
  dataPt
};
