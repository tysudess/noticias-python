let cspellModulePromise = null;

function carregarCSpell() {
  if (!cspellModulePromise) cspellModulePromise = import('cspell-lib');
  return cspellModulePromise;
}

function caminhoDicionarioPtBr() {
  return require.resolve('cspell-dict-pt-br/cspell-ext.json');
}

// Modo rígido: além do dicionário, sinaliza formas sem acento que podem ser
// aceitas como outra classe verbal pelo corretor comum. Em revisão jornalística
// preferimos sensibilidade maior; o usuário decide se aceita ou ignora a sugestão.
const ACENTOS_RIGIDOS = Object.freeze({
  materia: ['matéria'],
  noticia: ['notícia'],
  analise: ['análise'],
  numero: ['número'],
  periodo: ['período'],
  tambem: ['também'],
  possivel: ['possível'],
  area: ['área'],
  ultimo: ['último'],
  historia: ['história'],
  tecnica: ['técnica'],
  pratica: ['prática'],
  pagina: ['página'],
  veiculo: ['veículo'],
  titulo: ['título'],
  subtitulo: ['subtítulo'],
  conteudo: ['conteúdo'],
  portugues: ['português'],
  informacao: ['informação'],
  comunicacao: ['comunicação'],
  situacao: ['situação'],
  operacao: ['operação'],
  organizacao: ['organização'],
  administracao: ['administração'],
  decisao: ['decisão'],
  questao: ['questão'],
  versao: ['versão'],
  revisao: ['revisão'],
  correcao: ['correção'],
  populacao: ['população'],
  regiao: ['região'],
  reuniao: ['reunião'],
  relacao: ['relação'],
  funcao: ['função'],
  acao: ['ação'],
  servico: ['serviço'],
  exercito: ['exército'],
  aeronáutica: ['aeronáutica']
});

const ERROS_RIGIDOS = Object.freeze({
  marinhe: ['marinha', 'marinheiro']
});

function normalizarSugestoes(issue) {
  const sugestoes = Array.isArray(issue?.suggestions) ? issue.suggestions : [];
  return [...new Set(sugestoes.map(s => String(s || '').trim()).filter(Boolean))].slice(0, 8);
}

function ignorarIssue(issue) {
  const palavra = String(issue?.text || '').trim();
  if (!palavra) return true;
  if (palavra.length <= 1) return true;
  if (/^https?:\/\//i.test(palavra)) return true;
  if (/^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$/i.test(palavra)) return true;
  if (/^[A-ZÀ-Ý0-9][A-ZÀ-Ý0-9._/-]{1,}$/.test(palavra)) return true;
  return false;
}

function preservarCaixa(original, sugestao) {
  const o = String(original || '');
  const s = String(sugestao || '');
  if (!o || !s) return s;
  if (o === o.toUpperCase()) return s.toUpperCase();
  if (o[0] === o[0].toUpperCase()) return s[0].toUpperCase() + s.slice(1);
  return s;
}

function localizarRegrasRigidas(texto) {
  const conteudo = String(texto || '');
  const encontrados = [];
  const regex = /[A-Za-zÀ-ÖØ-öø-ÿ]+/g;
  let m;

  while ((m = regex.exec(conteudo))) {
    const palavra = m[0];
    const chave = palavra.toLocaleLowerCase('pt-BR');
    const baseSugestoes = ERROS_RIGIDOS[chave] || ACENTOS_RIGIDOS[chave];
    if (!baseSugestoes) continue;

    encontrados.push({
      palavra,
      offset: m.index,
      length: palavra.length,
      sugestoes: baseSugestoes.map(s => preservarCaixa(palavra, s)),
      origem: ERROS_RIGIDOS[chave] ? 'grafia-rigida' : 'acento-rigido'
    });
  }

  return encontrados;
}

function chaveIssue(issue) {
  return `${Number(issue?.offset) || 0}:${Number(issue?.length) || String(issue?.palavra || '').length}`;
}

function combinarIssues(cspellIssues, rigidos) {
  const mapa = new Map();

  for (const issue of cspellIssues || []) {
    mapa.set(chaveIssue(issue), issue);
  }

  // Regras rígidas têm prioridade porque fornecem a sugestão acentuada esperada.
  for (const issue of rigidos || []) {
    mapa.set(chaveIssue(issue), issue);
  }

  return [...mapa.values()].sort((a, b) => (a.offset || 0) - (b.offset || 0));
}

async function revisarTexto(texto = '') {
  const conteudo = String(texto || '');
  if (!conteudo.trim()) return [];

  const { spellCheckDocument } = await carregarCSpell();

  const resultado = await spellCheckDocument(
    {
      uri: 'file:///texto-materia.txt',
      text: conteudo,
      languageId: 'plaintext',
      locale: 'pt_BR'
    },
    {
      generateSuggestions: true,
      noConfigSearch: true,
      numSuggestions: 8,
      unknownWords: 'report-all'
    },
    {
      import: [caminhoDicionarioPtBr()],
      language: 'pt,pt_BR',
      locale: 'pt_BR',
      dictionaries: ['pt-br'],
      caseSensitive: true,
      allowCompoundWords: false,
      unknownWords: 'report-all',
      suggestionsTimeout: 2500,
      flagWords: [
        'marinhe->marinha, marinheiro'
      ]
    }
  );

  const cspellIssues = (resultado?.issues || [])
    .filter(issue => !ignorarIssue(issue))
    .map(issue => {
      const palavra = String(issue?.text || '');
      const offset = Number.isFinite(issue?.offset) ? issue.offset : 0;
      const length = Number.isFinite(issue?.length) ? issue.length : palavra.length;
      return {
        palavra,
        offset,
        length,
        sugestoes: normalizarSugestoes(issue),
        origem: 'dicionario'
      };
    });

  return combinarIssues(cspellIssues, localizarRegrasRigidas(conteudo));
}

module.exports = {
  revisarTexto,
  caminhoDicionarioPtBr,
  ignorarIssue,
  localizarRegrasRigidas,
  combinarIssues,
  ACENTOS_RIGIDOS,
  ERROS_RIGIDOS
};
