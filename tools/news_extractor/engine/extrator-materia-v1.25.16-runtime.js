const base = require('./extrator-materia-v1.25.15-runtime.js');
const motorDireto = require('./extrator-materia-v1.25.11-runtime.js');
const valorUtils = require('./extrator-materia-v1.25.14-runtime.js');

const VERSAO = '1.25.16-VALOR-ROTAS-INDEPENDENTES-FALLBACK-SEGURO';

function ehValor(url = '') {
  try {
    const h = new URL(url).hostname.toLowerCase();
    return h === 'valor.globo.com' || h.endsWith('.valor.globo.com');
  } catch (_) {
    return false;
  }
}

function rotasValor(url = '') {
  const original = String(url || '').trim();
  if (!ehValor(original)) return [original].filter(Boolean);

  const rotas = [original];
  const alternativa = typeof base.montarAlternativaValor === 'function'
    ? base.montarAlternativaValor(original)
    : '';
  if (alternativa && alternativa !== original) rotas.push(alternativa);
  return [...new Set(rotas)];
}

function textoErro(erro) {
  return erro?.message || String(erro || 'falha sem detalhe');
}

async function baixarHtmlPublicoValor(url) {
  const cfg = motorDireto.carregarConfigProxy();
  const resposta = await motorDireto.fetchComRetry(url, {
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

  if (!resposta.ok) {
    const erro = new Error(`HTTP ${resposta.status} ao acessar a página pública do Valor.`);
    erro.status = resposta.status;
    throw erro;
  }
  return await resposta.text();
}

function materiaDoHtmlValor(html, rota, original, referencia = null) {
  let candidata = null;

  try {
    candidata = motorDireto.extrairFallbackDoHtml(String(html || ''), rota);
    if (candidata) candidata.url = original;
  } catch (_) {}

  let corpoVisivel = '';
  try {
    corpoVisivel = valorUtils.extrairCorpoVisivelValorHtml(
      String(html || ''),
      rota,
      candidata || referencia || {}
    );
  } catch (_) {}

  if (candidata) {
    valorUtils.aplicarCorpoSeMaior(candidata, corpoVisivel);
    candidata.url = original;
    return candidata;
  }

  if (referencia && corpoVisivel) {
    const copia = { ...referencia, url: original };
    valorUtils.aplicarCorpoSeMaior(copia, corpoVisivel);
    return copia;
  }

  return null;
}

async function recuperarValorPublico(url, dependencias = {}) {
  const original = String(url || '').trim();
  const extrairDireto = dependencias.extrairDireto || motorDireto.extrairMateria;
  const baixarHtml = dependencias.baixarHtml || baixarHtmlPublicoValor;

  let melhor = null;
  const erros = [];

  for (const rota of rotasValor(original)) {
    let extraidaNaRota = null;

    // Importante: usa o motor anterior ao fallback específico do Valor.
    // Assim cada rota é testada de forma independente e uma falha na AMP
    // nunca apaga um resultado já obtido pela URL normal (e vice-versa).
    try {
      extraidaNaRota = await extrairDireto(rota);
      if (extraidaNaRota) {
        extraidaNaRota.url = original;
        melhor = valorUtils.escolherMelhorMateria(melhor, extraidaNaRota);
      }
    } catch (erro) {
      erros.push(`${rota}: ${textoErro(erro)}`);
    }

    // Se ainda está curto (ou o parser falhou), tenta apenas o HTML que o
    // próprio site entregou publicamente. Não usa login, cookies ou paywall.
    if (!melhor || valorUtils.corpoCurto(melhor.texto)) {
      try {
        const html = await baixarHtml(rota);
        const candidataHtml = materiaDoHtmlValor(
          html,
          rota,
          original,
          extraidaNaRota || melhor
        );
        melhor = valorUtils.escolherMelhorMateria(melhor, candidataHtml);
      } catch (erroHtml) {
        erros.push(`${rota} [HTML]: ${textoErro(erroHtml)}`);
      }
    }
  }

  // Regressão corrigida: se qualquer rota produziu matéria válida, devolve a
  // melhor disponível mesmo que uma tentativa complementar tenha falhado.
  if (melhor && String(melhor.texto || '').trim()) {
    melhor.url = original;
    return typeof base.corrigirMateria === 'function'
      ? base.corrigirMateria(melhor)
      : melhor;
  }

  const detalhes = erros.join(' | ');
  if (/\b(?:401|403)\b|forbidden|unauthorized/i.test(detalhes)) {
    throw new Error(
      'Valor recusou o acesso automatizado às rotas públicas desta matéria. ' +
      'Nenhum conteúdo já obtido foi descartado. Para conteúdo de assinante, ' +
      'será necessário usar uma sessão autenticada autorizada pelo próprio usuário.'
    );
  }

  throw new Error(
    'Não foi possível extrair esta matéria do Valor pelas rotas públicas disponíveis.' +
    (detalhes ? ` Detalhes: ${detalhes}` : '')
  );
}

async function extrairMateria(url) {
  const original = String(url || '').trim();
  if (!ehValor(original)) return base.extrairMateria(original);
  return recuperarValorPublico(original);
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  ehValor,
  rotasValor,
  baixarHtmlPublicoValor,
  materiaDoHtmlValor,
  recuperarValorPublico
};
