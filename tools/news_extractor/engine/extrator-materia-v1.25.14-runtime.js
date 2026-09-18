const { JSDOM } = require('jsdom');
const base = require('./extrator-materia-v1.25.13-runtime.js');

const VERSAO = '1.25.14-VALOR-CORPO-CURTO-COMPARA-ROTAS';
const LIMITE_CORPO_CURTO = 1200;

function norm(v = '') {
  return String(v || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .trim();
}

function ehValor(url = '') {
  try {
    const h = new URL(url).hostname.toLowerCase();
    return h === 'valor.globo.com' || h.endsWith('.valor.globo.com');
  } catch (_) {
    return false;
  }
}

function blocosTexto(texto = '') {
  return String(texto || '').split(/\n\n+/).map(norm).filter(Boolean);
}

function corpoCurto(texto = '') {
  const blocos = blocosTexto(texto);
  return norm(texto).length < LIMITE_CORPO_CURTO || blocos.length < 3;
}

function tamanhoCorpo(materia) {
  return norm(materia?.texto || '').length;
}

function elementoOcultoOuRestrito(el) {
  for (let no = el; no && no.nodeType === 1; no = no.parentElement) {
    if (no.hasAttribute('hidden')) return true;
    if (String(no.getAttribute('aria-hidden') || '').toLowerCase() === 'true') return true;
    const style = String(no.getAttribute('style') || '').toLowerCase().replace(/\s+/g, '');
    if (/display:none|visibility:hidden/.test(style)) return true;

    const marca = `${no.id || ''} ${no.className || ''}`.toLowerCase();
    // Não lê blocos identificados como restritos/assinatura. A recuperação usa
    // somente conteúdo entregue como parte visível da página pública.
    if (/(?:^|[\s_-])(paywall|signwall|subscription|subscriber|subscribe|premium-wall|login-wall|content-blocked|assinatura|assine)(?:[\s_-]|$)/i.test(marca)) {
      return true;
    }
  }
  return false;
}

function densidadeLinks(el) {
  const total = norm(el.textContent).length;
  if (!total) return 0;
  let links = 0;
  for (const a of el.querySelectorAll('a')) links += norm(a.textContent).length;
  return links / total;
}

function ehLixoValor(t = '') {
  const x = norm(t);
  if (!x) return true;
  return /^(?:publicidade|anúncio|anuncio|compartilhar|salvar|ouvir|mais lidas|mais lidos)$/i.test(x) ||
    /^(?:leia|veja|confira)\s+(?:tamb[eé]m|mais)\b/i.test(x) ||
    /^(?:assine|já é assinante|ja e assinante|faça login|faca login)\b/i.test(x);
}

function pontuarContainer(el) {
  let pontos = 0;
  for (const p of el.querySelectorAll('p, blockquote')) {
    if (elementoOcultoOuRestrito(p)) continue;
    const t = norm(p.textContent);
    if (t.length >= 60) pontos += Math.min(t.length, 1500);
  }
  return pontos;
}

function extrairCorpoVisivelValorHtml(html, url, materia = {}) {
  const dom = new JSDOM(String(html || ''), { url });
  const doc = dom.window.document;

  const seletores = [
    '[itemprop="articleBody"]',
    '.mc-article-body',
    '.content-text',
    '[class*="article-body" i]',
    '[class*="article-content" i]',
    'article',
    'main'
  ];

  const candidatos = [];
  const vistos = new Set();
  for (const seletor of seletores) {
    for (const el of doc.querySelectorAll(seletor)) {
      if (vistos.has(el) || elementoOcultoOuRestrito(el)) continue;
      vistos.add(el);
      candidatos.push(el);
    }
  }

  candidatos.sort((a, b) => pontuarContainer(b) - pontuarContainer(a));
  const container = candidatos[0];
  if (!container) return '';

  const excluir = new Set([
    materia.titulo,
    materia.subtitulo,
    materia.autor,
    materia.data
  ].filter(Boolean).map(x => norm(x).toLowerCase()));

  const saida = [];
  for (const el of container.querySelectorAll('p, h2, h3, blockquote')) {
    if (elementoOcultoOuRestrito(el)) continue;
    const t = norm(el.textContent);
    if (!t || excluir.has(t.toLowerCase()) || ehLixoValor(t)) continue;
    if (densidadeLinks(el) > 0.70 && t.length < 340) continue;

    const tag = String(el.tagName || '').toLowerCase();
    if ((tag === 'p' || tag === 'blockquote') && t.length < 45) continue;
    if ((tag === 'h2' || tag === 'h3') && t.length < 10) continue;

    if (saida[saida.length - 1] !== t) saida.push(t);
  }

  return saida.join('\n\n').trim();
}

async function baixarHtmlValor(url) {
  const cfg = base.carregarConfigProxy();
  const resposta = await base.fetchComRetry(url, {
    redirect: 'follow',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
      'Accept': 'text/html,application/xhtml+xml',
      'Connection': 'close'
    }
  }, {
    timeoutMs: Math.max(5000, Number(cfg.TIMEOUT_MS) || 45000),
    tentativas: 2
  });

  if (!resposta.ok) throw new Error(`HTTP ${resposta.status} ao acessar o Valor.`);
  return await resposta.text();
}

function escolherMelhorMateria(atual, candidata) {
  if (!atual) return candidata || null;
  if (!candidata) return atual;
  return tamanhoCorpo(candidata) > tamanhoCorpo(atual) ? candidata : atual;
}

function aplicarCorpoSeMaior(materia, texto) {
  if (!materia || !texto) return materia;
  const atual = tamanhoCorpo(materia);
  const novo = norm(texto).length;
  if (novo >= 600 && novo > atual + 120) materia.texto = String(texto).trim();
  return materia;
}

async function extrairMateria(url) {
  const original = String(url || '').trim();
  if (!ehValor(original)) return base.extrairMateria(original);

  const rotas = [original];
  const alternativa = typeof base.montarAlternativaValor === 'function'
    ? base.montarAlternativaValor(original)
    : '';
  if (alternativa && alternativa !== original) rotas.push(alternativa);

  let melhor = null;
  let ultimoErro = null;

  for (let i = 0; i < rotas.length; i++) {
    const rota = rotas[i];
    if (i > 0 && melhor && !corpoCurto(melhor.texto)) break;

    let extraida = null;
    try {
      extraida = await base.extrairMateria(rota);
      extraida.url = original;
      melhor = escolherMelhorMateria(melhor, extraida);
    } catch (erro) {
      ultimoErro = erro;
    }

    if (!melhor || corpoCurto(melhor.texto)) {
      try {
        const html = await baixarHtmlValor(rota);
        const referencia = extraida || melhor || {};
        const corpoVisivel = extrairCorpoVisivelValorHtml(html, rota, referencia);
        if (extraida) {
          aplicarCorpoSeMaior(extraida, corpoVisivel);
          extraida.url = original;
          melhor = escolherMelhorMateria(melhor, extraida);
        } else if (melhor) {
          aplicarCorpoSeMaior(melhor, corpoVisivel);
        }
      } catch (erroHtml) {
        ultimoErro = ultimoErro || erroHtml;
      }
    }
  }

  if (!melhor) throw ultimoErro || new Error('Não foi possível extrair a matéria do Valor.');
  melhor.url = original;
  return typeof base.corrigirMateria === 'function' ? base.corrigirMateria(melhor) : melhor;
}

module.exports = {
  ...base,
  VERSAO,
  LIMITE_CORPO_CURTO,
  extrairMateria,
  ehValor,
  corpoCurto,
  extrairCorpoVisivelValorHtml,
  escolherMelhorMateria,
  aplicarCorpoSeMaior
};
