const base = require('./extrator-materia-v1.25.11-runtime.js');

const VERSAO = '1.25.12-VALOR-AMP-FALLBACK';

function host(url = '') {
  try { return new URL(url).hostname.toLowerCase(); } catch (_) { return ''; }
}

function montarAlternativaValor(url = '') {
  try {
    const u = new URL(url);
    const h = u.hostname.toLowerCase();
    if (h !== 'valor.globo.com' && !h.endsWith('.valor.globo.com')) return '';

    if (u.pathname.startsWith('/google/amp/')) {
      const normal = new URL(u.toString());
      normal.pathname = u.pathname.replace(/^\/google\/amp/, '');
      return normal.toString();
    }

    const amp = new URL(u.toString());
    amp.pathname = `/google/amp${u.pathname.startsWith('/') ? '' : '/'}${u.pathname}`;
    return amp.toString();
  } catch (_) {
    return '';
  }
}

async function extrairMateria(url) {
  const original = String(url || '').trim();
  let erroOriginal = null;

  try {
    return await base.extrairMateria(original);
  } catch (erro) {
    erroOriginal = erro;
  }

  const alternativa = montarAlternativaValor(original);
  if (!alternativa || alternativa === original) throw erroOriginal;

  try {
    const materia = await base.extrairMateria(alternativa);
    materia.url = original;
    return base.corrigirMateria(materia);
  } catch (erroAmp) {
    const msgOriginal = erroOriginal?.message || String(erroOriginal || 'falha na URL original');
    const msgAmp = erroAmp?.message || String(erroAmp || 'falha na rota AMP');
    throw new Error(`Valor: falhou na URL original e na rota AMP. Original: ${msgOriginal} | AMP: ${msgAmp}`);
  }
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  montarAlternativaValor
};
