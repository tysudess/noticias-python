const { JSDOM } = require('jsdom');
const base = require('./extrator-materia-v1.25.19-runtime.js');

const VERSAO = '1.25.20-UOL-COMPLETUDE-E-BLOCOS';

function norm(value = '') {
  return String(value || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .trim();
}

function host(url = '') {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch (_) {
    return '';
  }
}

function pathName(url = '') {
  try {
    return new URL(url).pathname.toLowerCase();
  } catch (_) {
    return '';
  }
}

function ehUol(url = '') {
  const h = host(url);
  return h === 'uol.com.br' || h.endsWith('.uol.com.br');
}

function blocosTexto(texto = '') {
  return String(texto || '')
    .split(/\n\s*\n+/)
    .map(norm)
    .filter(Boolean);
}

function pareceUolIncompleto(materia, url = '') {
  if (!ehUol(url)) return false;

  const texto = String(materia?.texto || '').trim();
  const blocos = blocosTexto(texto);
  const caminho = pathName(url);

  if (!texto) return true;

  // Colunas do UOL costumam ser matérias longas e divididas por blocos
  // publicitários. Dois ou três parágrafos não devem ser tratados
  // automaticamente como "matéria completa".
  if (caminho.includes('/colunas/')) {
    return texto.length < 1800 || blocos.length < 5;
  }

  return texto.length < 1100 || blocos.length < 4;
}

function densidadeLinks(elemento) {
  const total = norm(elemento?.textContent).length;
  if (!total) return 0;

  let links = 0;
  for (const link of elemento.querySelectorAll('a')) {
    links += norm(link.textContent).length;
  }

  return links / total;
}

function ehBlocoTerminalUol(texto = '') {
  const t = norm(texto);

  return (
    /^reportagem$/i.test(t)
    || /^comunicar erro$/i.test(t)
    || /^deixe seu coment[aá]rio$/i.test(t)
    || /^veja tamb[eé]m$/i.test(t)
    || /^as mais lidas agora$/i.test(t)
    || /^receba novos posts\b/i.test(t)
    || /^mais lidas\b/i.test(t)
  );
}

function ehLixoUol(texto = '') {
  const t = norm(texto);

  if (!t) return true;

  return (
    /^publicidade$/i.test(t)
    || /^continua ap[oó]s a publicidade$/i.test(t)
    || /^imagem:\s*/i.test(t)
    || /^foto:\s*/i.test(t)
    || /^ouvir$/i.test(t)
    || /^resumo$/i.test(t)
    || /^s[oó] para assinantes$/i.test(t)
    || /^assine uol$/i.test(t)
    || /^colunista de\b/i.test(t)
    || /^sobre o autor$/i.test(t)
    || /^\d+(?:[,.]\d+)?×$/i.test(t)
  );
}

function elementoEmAreaDescartavel(elemento) {
  if (!elemento || typeof elemento.closest !== 'function') {
    return false;
  }

  const ancestor = elemento.closest(
    [
      'nav',
      'footer',
      'aside',
      '[class*="comment" i]',
      '[id*="comment" i]',
      '[class*="related" i]',
      '[id*="related" i]',
      '[class*="recommend" i]',
      '[id*="recommend" i]',
      '[class*="newsletter" i]',
      '[id*="newsletter" i]',
      '[class*="most-read" i]',
      '[class*="mais-lidas" i]',
      '[class*="share" i]',
      '[class*="social" i]'
    ].join(',')
  );

  return Boolean(ancestor);
}

function encontrarInicio(nodes, materia) {
  const baseBlocks = blocosTexto(materia?.texto || '');
  const primeiro = baseBlocks.find(t => t.length >= 70) || baseBlocks[0] || '';
  const titulo = norm(materia?.titulo || '');

  if (primeiro) {
    const chave = norm(primeiro).toLocaleLowerCase('pt-BR').slice(0, 120);

    const index = nodes.findIndex(node => {
      const t = norm(node.textContent).toLocaleLowerCase('pt-BR');
      if (t.length < 60) return false;

      const curto = chave.slice(0, Math.min(85, chave.length));
      return (
        (curto && t.includes(curto))
        || (t.slice(0, 85) && chave.includes(t.slice(0, 85)))
      );
    });

    if (index >= 0) return index;
  }

  if (titulo) {
    const tituloNorm = titulo.toLocaleLowerCase('pt-BR');

    const hIndex = nodes.findIndex(node => {
      const tag = String(node.tagName || '').toLowerCase();
      if (tag !== 'h1') return false;

      const t = norm(node.textContent).toLocaleLowerCase('pt-BR');
      return t === tituloNorm || t.includes(tituloNorm) || tituloNorm.includes(t);
    });

    if (hIndex >= 0) {
      for (let i = hIndex + 1; i < nodes.length; i += 1) {
        const tag = String(nodes[i].tagName || '').toLowerCase();
        const t = norm(nodes[i].textContent);

        if (
          (tag === 'p' || tag === 'blockquote')
          && t.length >= 70
          && !ehLixoUol(t)
        ) {
          return i;
        }
      }
    }
  }

  return -1;
}

function extrairCorpoUolDoHtml(html, url, materiaBase) {
  const dom = new JSDOM(String(html || ''), { url });
  const document = dom.window.document;

  const nodes = [
    ...document.querySelectorAll('h1, h2, h3, p, blockquote')
  ];

  const start = encontrarInicio(nodes, materiaBase);
  if (start < 0) return '';

  const meta = new Set(
    [
      materiaBase?.titulo,
      materiaBase?.subtitulo,
      materiaBase?.autor,
      materiaBase?.data
    ]
      .filter(Boolean)
      .map(v => norm(v).toLocaleLowerCase('pt-BR'))
  );

  const saida = [];
  const vistos = new Set();

  for (let i = start; i < nodes.length; i += 1) {
    const node = nodes[i];
    const tag = String(node.tagName || '').toLowerCase();
    const texto = norm(node.textContent);

    if (!texto) continue;

    if (i > start && ehBlocoTerminalUol(texto)) {
      break;
    }

    if (ehLixoUol(texto)) continue;
    if (elementoEmAreaDescartavel(node)) continue;

    const chave = texto.toLocaleLowerCase('pt-BR');

    if (meta.has(chave)) continue;
    if (vistos.has(chave)) continue;

    if (
      (tag === 'h2' || tag === 'h3')
      && texto.length <= 180
    ) {
      vistos.add(chave);
      saida.push(texto);
      continue;
    }

    if (tag !== 'p' && tag !== 'blockquote') {
      continue;
    }

    if (texto.length < 25) continue;
    if (densidadeLinks(node) > 0.72 && texto.length < 320) continue;

    vistos.add(chave);
    saida.push(texto);
  }

  return saida.join('\n\n').trim();
}

function paginaMarcaSoAssinantes(html = '') {
  const dom = new JSDOM(String(html || ''));
  const document = dom.window.document;

  for (const element of document.querySelectorAll(
    'body *'
  )) {
    const text = norm(element.textContent);

    if (
      text
      && text.length <= 80
      && /^s[oó] para assinantes\b/i.test(text)
    ) {
      return true;
    }
  }

  return false;
}

function formatarMateria(materia) {
  const partes = [
    materia.url,
    '',
    materia.veiculo,
    '',
    `*${materia.titulo || 'Título não identificado'}*`
  ];

  if (materia.subtitulo) {
    partes.push('', `_${materia.subtitulo}_`);
  }

  partes.push('');

  if (materia.autor) {
    partes.push(materia.autor);
  }

  partes.push(
    materia.data || 'Data não identificada',
    '',
    materia.texto || ''
  );

  materia.resultado =
    partes
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
    + '\n';

  return materia;
}

async function baixarHtmlParaConferencia(url) {
  const resposta = await base.fetchComRetry(
    url,
    {
      redirect: 'follow',
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
          + 'AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml',
        'Connection': 'close'
      }
    },
    {
      // Só é usado quando a primeira extração UOL parece incompleta.
      // Uma tentativa curta é suficiente; não queremos dobrar o tempo.
      timeoutMs: 18000,
      tentativas: 1
    }
  );

  if (!resposta.ok) {
    throw new Error(
      `HTTP ${resposta.status} ao conferir a completude da matéria UOL.`
    );
  }

  const contentType = resposta.headers.get('content-type') || '';
  if (!contentType.includes('text/html')) {
    throw new Error(
      `A conferência UOL não retornou HTML (${contentType || 'tipo desconhecido'}).`
    );
  }

  return await resposta.text();
}

async function extrairMateria(url) {
  const materia = await base.extrairMateria(url);

  if (!pareceUolIncompleto(materia, url)) {
    return materia;
  }

  let html = '';

  try {
    html = await baixarHtmlParaConferencia(url);
  } catch (_) {
    // Preserva o resultado original quando a conferência não consegue
    // acessar a página. A orquestração V91 continua controlando o timeout.
    materia.avisoCompletude =
      'A matéria foi extraída, mas a Central não conseguiu confirmar se o '
      + 'UOL entregou o corpo completo.';
    return materia;
  }

  // Regra importante: não tentar contornar conteúdo reservado a assinantes.
  // Se o acesso atual do extrator recebeu apenas o preview e a própria página
  // sinaliza "Só para assinantes", devolvemos um erro claro em vez de chamar
  // o preview de matéria completa.
  if (
    paginaMarcaSoAssinantes(html)
    && pareceUolIncompleto(materia, url)
  ) {
    throw new Error(
      'O UOL forneceu apenas o trecho inicial desta matéria e marcou o '
      + 'conteúdo como exclusivo para assinantes. Para extrair a versão '
      + 'integral, a Central precisa usar uma sessão UOL autenticada pelo '
      + 'próprio usuário; o extrator não contorna o acesso do site.'
    );
  }

  const completo = extrairCorpoUolDoHtml(
    html,
    url,
    materia
  );

  const atual = String(materia.texto || '').trim();

  if (
    completo.length >= atual.length + 220
    && blocosTexto(completo).length >= blocosTexto(atual).length + 1
  ) {
    materia.texto = completo;
    materia.origemCorpo = 'uol-dom-multiblocos';
    materia.avisoCompletude = '';
    return formatarMateria(materia);
  }

  materia.avisoCompletude =
    'A matéria foi extraída, mas o corpo retornado pelo UOL parece curto. '
    + 'Revise o texto antes de utilizar.';

  return materia;
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  pareceUolIncompleto,
  extrairCorpoUolDoHtml,
  paginaMarcaSoAssinantes
};
