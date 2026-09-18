const { JSDOM } = require('jsdom');

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

function palavras(t = '') {
  return new Set(
    norm(t)
      .toLocaleLowerCase('pt-BR')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .match(/[a-z0-9]{4,}/g) || []
  );
}

function semelhanca(a = '', b = '') {
  const A = palavras(a);
  const B = palavras(b);
  if (A.size < 4 || B.size < 4) return 0;
  let inter = 0;
  for (const p of A) if (B.has(p)) inter++;
  return inter / Math.min(A.size, B.size);
}

function ehRuidoG1(texto = '') {
  const t = norm(texto);
  if (!t) return true;

  if (/^(?:agora\s+no\s+g1|mais\s+do\s+g1|vídeos?\s+em\s+alta\s+no\s+g1|videos?\s+em\s+alta\s+no\s+g1)$/i.test(t)) return true;
  if (/^(?:✅\s*)?clique\s+aqui\s+para\s+seguir\s+o\s+canal\s+do\s+g1\b/i.test(t)) return true;
  if (/^(?:veja|confira|leia)\s+(?:tamb[eé]m|mais)\b/i.test(t) && t.length < 220) return true;
  if (/^(?:foto|cr[eé]dito)\s*:/i.test(t)) return true;
  if (/\s[—–-]\s*foto\s*:/i.test(t)) return true;
  if (/^\d{1,2}:\d{2}(?::\d{2})?$/.test(t)) return true;
  if (/^(?:compartilhe|publicidade)$/i.test(t)) return true;
  return false;
}

function dentroDeModuloNaoJornalistico(el) {
  if (!el || !el.closest) return false;
  const seletores = [
    '[class*="resumo"]',
    '[class*="summary"]',
    '[class*="recommend"]',
    '[class*="related"]',
    '[class*="feed-post"]',
    '[class*="mais-lidas"]',
    '[class*="most-read"]',
    '[data-testid*="summary"]',
    '[data-testid*="recommend"]'
  ];
  return seletores.some(s => {
    try { return !!el.closest(s); } catch (_) { return false; }
  });
}

function escolherRaizArtigoG1(document) {
  const seletores = [
    'main .mc-article-body .mc-column.content-text',
    'main .mc-article-body article',
    'main .mc-article-body',
    'main article',
    'article'
  ];

  let melhor = null;
  let melhorQtd = 0;
  for (const s of seletores) {
    for (const raiz of document.querySelectorAll(s)) {
      const qtd = raiz.querySelectorAll('p.content-text__container').length;
      if (qtd > melhorQtd) {
        melhor = raiz;
        melhorQtd = qtd;
      }
    }
    if (melhorQtd >= 3) break;
  }
  return melhor;
}

function coletarBlocosG1(document, materia = {}) {
  const raiz = escolherRaizArtigoG1(document);
  if (!raiz) return [];

  // IMPORTANTE: somente <p class="content-text__container"> dentro do corpo
  // principal. A versão anterior aceitava qualquer .content-text__container,
  // o que permitia capturar cards/resumos do portal.
  const elementos = [...raiz.querySelectorAll(
    'p.content-text__container, .content-intertitle h2, .content-intertitle h3'
  )];

  const titulo = norm(materia.titulo);
  const subtitulo = norm(materia.subtitulo);
  const meta = new Set(
    [titulo, subtitulo, norm(materia.autor), norm(materia.data)]
      .filter(Boolean)
      .map(x => x.toLocaleLowerCase('pt-BR'))
  );

  const saida = [];
  const vistos = new Set();

  for (const el of elementos) {
    if (dentroDeModuloNaoJornalistico(el)) continue;

    const t = norm(el.textContent);
    if (!t || ehRuidoG1(t)) continue;
    if (meta.has(t.toLocaleLowerCase('pt-BR'))) continue;

    const intertitulo = /^H[23]$/.test(el.tagName || '') || !!el.closest?.('.content-intertitle');
    if (!intertitulo && t.length < 35) continue;
    if (intertitulo && t.length < 4) continue;

    const chave = t.toLocaleLowerCase('pt-BR');
    if (vistos.has(chave)) continue;
    vistos.add(chave);
    saida.push(t);
  }

  return saida;
}

function blocosAtuais(texto = '') {
  return String(texto || '').split(/\n\n+/).map(norm).filter(Boolean);
}

function indiceCorrespondente(alvo, lista = []) {
  const a = norm(alvo);
  if (!a) return -1;
  let melhor = -1;
  let melhorScore = 0;
  for (let i = 0; i < lista.length; i++) {
    const b = norm(lista[i]);
    const score = a === b ? 1 : (a.includes(b) || b.includes(a) ? 0.95 : semelhanca(a, b));
    if (score > melhorScore) {
      melhorScore = score;
      melhor = i;
    }
  }
  return melhorScore >= 0.78 ? melhor : -1;
}

function completarSomenteDepoisDoUltimoParagrafo(atual = '', blocos = []) {
  const atuais = blocosAtuais(atual);
  if (!atuais.length || blocos.length < 2) return atual;

  // A correção nunca mais substitui o corpo inteiro. Ela só pode acrescentar
  // texto que aparece DEPOIS do último parágrafo já extraído, dentro do corpo
  // principal da matéria. Se não houver correspondência literal forte, não mexe.
  const ultimo = atuais[atuais.length - 1];
  const pos = indiceCorrespondente(ultimo, blocos);
  if (pos < 0 || pos >= blocos.length - 1) return atual;

  const extras = [];
  for (const cand of blocos.slice(pos + 1)) {
    const repetido = atuais.some(a =>
      norm(a) === norm(cand) ||
      a.includes(cand) || cand.includes(a) ||
      semelhanca(a, cand) >= 0.78
    );
    if (!repetido) extras.push(cand);
  }

  if (!extras.length) return atual;
  return [...atuais, ...extras].join('\n\n').trim();
}

async function recuperarCorpoCompletoG1(materia, base) {
  const h = host(materia?.url);
  if (h !== 'g1.globo.com') return materia;

  try {
    const cfg = base.carregarConfigProxy();
    const resposta = await base.fetchComRetry(materia.url, {
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml',
        'Connection': 'close'
      }
    }, {
      timeoutMs: Math.max(5000, Number(cfg.TIMEOUT_MS) || 45000),
      tentativas: 2
    });

    if (!resposta.ok) return materia;
    const html = await resposta.text();
    const document = new JSDOM(html, { url: materia.url }).window.document;
    const blocos = coletarBlocosG1(document, materia);

    materia.texto = completarSomenteDepoisDoUltimoParagrafo(materia.texto, blocos);
  } catch (_) {
    // Em qualquer dúvida, preserva o resultado original da camada anterior.
  }

  return materia;
}

module.exports = {
  recuperarCorpoCompletoG1,
  coletarBlocosG1,
  escolherRaizArtigoG1,
  completarSomenteDepoisDoUltimoParagrafo,
  ehRuidoG1,
  semelhanca
};
