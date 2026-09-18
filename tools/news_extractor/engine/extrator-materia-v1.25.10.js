const { JSDOM } = require('jsdom');
const base = require('./extrator-materia-v1.25.1.js');

const VERSAO = '1.25.10-CORRECOES-FONTES';

function norm(v = '') {
  return String(v || '')
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .trim();
}
function host(url = '') { try { return new URL(url).hostname.toLowerCase(); } catch (_) { return ''; } }
function split(texto = '') { return String(texto || '').split(/\n\n+/).map(norm).filter(Boolean); }
function join(lista = []) { return lista.map(norm).filter(Boolean).join('\n\n').trim(); }
function truncado(t = '') {
  t = norm(t);
  return !!t && (
    /(?:\.\.\.|…|\[…\])$/.test(t) ||
    /\b(?:a|o|e|de|do|da|dos|das|em|no|na|nos|nas|para|por|com|sem)$/i.test(t) ||
    /\s[A-Za-zÀ-ÿ]$/.test(t)
  );
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
  const A = palavras(a), B = palavras(b);
  if (A.size < 4 || B.size < 4) return 0;
  let n = 0;
  for (const x of A) if (B.has(x)) n++;
  return n / Math.min(A.size, B.size);
}

function limparTexto(m) {
  const h = host(m.url);
  let b = split(m.texto);

  // Resíduos isolados de anúncios que apareceram em mais de uma fonte.
  b = b.filter(x => !/^(?:continua\s+(?:depois|ap[oó]s)\s+da\s+publicidade|publicidade)$/i.test(x));

  if (h === 'clickpetroleoegas.com.br' || h === 'www.clickpetroleoegas.com.br') {
    const out = [];
    let pulando = false;
    let n = 0;
    for (const x of b) {
      if (/^ARTIGO\s+CONTINUA\s+ABAIXO$/i.test(x)) {
        pulando = true;
        n = 0;
        continue;
      }
      if (/^Assista\s+(?:o\s+)?v[ií]deo$/i.test(x)) continue;
      if (pulando) {
        n++;
        const real = x.length >= 55 && /[.!?][”"']?$/.test(x);
        if (!real && n <= 8) continue;
        pulando = false;
      }
      out.push(x);
    }
    b = out;
  }

  if (h === 'www.cnnbrasil.com.br' || h === 'cnnbrasil.com.br') {
    b = b.filter(x =>
      !/^At\s+\d{1,2}:\d{2}\s+p\.m\.\s+ET\s+today\b/i.test(x) &&
      !/^—\s*U\.S\.\s+Central\s+Command\b/i.test(x)
    );
  }

  if (h === 'thmais.com.br' || h === 'www.thmais.com.br') {
    b = b.filter((x, i) => !(i < 3 && /Jornalista\s+e\s+publicit[aá]rio/i.test(x) && /trajet[oó]ria/i.test(x)));
  }

  if (h === 'oantagonista.com.br' || h === 'www.oantagonista.com.br') {
    const c = b.findIndex(x => /^Siga\s+a\s+leitura\s+em\s+Cruso[eé]/i.test(x));
    if (c >= 0) b = b.slice(0, c);
  }

  if (h === 'www.cartacapital.com.br' || h === 'cartacapital.com.br') {
    b = b.filter(x => !(x.length < 420 && /\bFoto\s*:/i.test(x)));
    const c = b.findIndex(x => /^Apoie\s+o\s+jornalismo/i.test(x));
    if (c >= 0) b = b.slice(0, c);
  }

  if (h === 'www.metropoles.com' || h === 'metropoles.com') {
    b = b
      .map(x => x.replace(/\s+Confira\s+todas\s+aqui\.?\s*$/i, '').trim())
      .filter(Boolean);
  }

  if (h === 'revistaoeste.com' || h === 'www.revistaoeste.com') {
    b = b.filter(x => !/^\+?\s*Entenda\s+o\s+que\s+[eé]\s+Pol[ií]tica\s+em\s+Oeste$/i.test(x));
    if (b.length >= 2 && semelhanca(b[0], b[1]) >= 0.40) b.shift();
  }

  if (h === 'www.otempo.com.br' || h === 'otempo.com.br') {
    const c = b.findIndex(x => /^A\s+reportagem\s+est[aá]\s+aberta\s+[aà]\s+manifesta[cç][aã]o/i.test(x));
    if (c >= 0) b = b.slice(0, c);
    b = b.filter(x => !/^A\s+equipe\s+de\s+O\s+TEMPO\s+produziu\s+esta\s+reportagem\s+automaticamente/i.test(x));
  }

  m.texto = join(b);
  return m;
}

function primeiroH2(doc, titulo = '') {
  const nt = norm(titulo).toLowerCase();
  for (const el of doc.querySelectorAll('h2')) {
    const t = norm(el.textContent);
    if (t.length < 20 || t.length > 700) continue;
    const n = t.toLowerCase();
    if (n === nt) continue;
    if (/^(?:leia|veja|confira|resumo|mais\s+lidas)/i.test(t)) continue;
    if (/^leia\s+aqui\s+o\s+resumo/i.test(t)) continue;
    return t;
  }
  return '';
}

function folhasDepoisDoH1(doc, limite = 120) {
  const h1 = doc.querySelector('h1');
  if (!h1) return [];
  const todos = [...doc.querySelectorAll('body *')];
  const i = todos.indexOf(h1);
  if (i < 0) return [];
  const saida = [];
  for (let p = i + 1; p < Math.min(todos.length, i + limite); p++) {
    const el = todos[p];
    if (el.children.length) continue;
    const t = norm(el.textContent);
    if (t && t.length <= 180) saida.push(t);
  }
  return saida;
}

function autorVisivelUol(doc) {
  const folhas = folhasDepoisDoH1(doc, 100);
  const posDoUol = folhas.findIndex(t => /^Do\s+UOL\b/i.test(t));
  if (posDoUol < 0) return '';

  for (let i = posDoUol - 1; i >= Math.max(0, posDoUol - 5); i--) {
    const t = folhas[i];
    if (/^\d{1,2}\/\d{1,2}\/\d{4}/.test(t)) continue;
    if (/^[A-ZÀ-Ý][A-Za-zÀ-ÿ.'’-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ.'’-]+){1,5}$/u.test(t)) return t;
  }
  return 'UOL';
}

function dataVisivelProximaH1(doc) {
  const folhas = folhasDepoisDoH1(doc, 140);
  for (const t of folhas) {
    const m = t.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/);
    if (m) return `${m[1].padStart(2, '0')}/${m[2].padStart(2, '0')}/${m[3]}`;
  }
  return '';
}

async function cabecalho(url) {
  const h = host(url);
  const suportados = [
    'www1.folha.uol.com.br',
    'noticias.r7.com',
    'thmais.com.br',
    'www.thmais.com.br',
    'noticias.uol.com.br',
    'economia.uol.com.br',
    'www.gazetadopovo.com.br'
  ];
  if (!suportados.includes(h)) return {};

  try {
    const cfg = base.carregarConfigProxy();
    const r = await base.fetchComRetry(url, {
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
    if (!r.ok) return {};

    const doc = new JSDOM(await r.text(), { url }).window.document;
    const titulo = [...doc.querySelectorAll('h1')]
      .map(x => norm(x.textContent))
      .find(x => x.length >= 8 && x.length <= 500) || '';

    return {
      titulo,
      subtitulo: primeiroH2(doc, titulo),
      autorUol: (h === 'noticias.uol.com.br' || h === 'economia.uol.com.br') ? autorVisivelUol(doc) : '',
      dataVisivel: dataVisivelProximaH1(doc)
    };
  } catch (_) {
    return {};
  }
}

async function corrigirCabecalho(m) {
  const h = host(m.url);
  const antigo = norm(m.titulo);
  const c = await cabecalho(m.url);

  if (h === 'www1.folha.uol.com.br') {
    m.titulo = c.titulo || norm(m.titulo)
      .replace(/^Eleição\s+2026\s*:\s*/i, '')
      .replace(/\s+-\s+\d{2}\/\d{2}\/\d{4}\s+-\s+[^-]{2,80}\s+-\s+Folha\s*$/i, '')
      .trim();
  }

  if (h === 'noticias.r7.com') {
    if (c.titulo) m.titulo = c.titulo;
    if (c.subtitulo) m.subtitulo = c.subtitulo;
    if (!norm(m.autor)) m.autor = 'R7';
  }

  if (h === 'thmais.com.br' || h === 'www.thmais.com.br') {
    if (c.titulo && c.titulo !== antigo) {
      if (antigo.length >= 25 && antigo.length <= 500 && /[.!?]$/.test(antigo)) m.subtitulo = antigo;
      m.titulo = c.titulo;
    }
  }

  if (h === 'noticias.uol.com.br' || h === 'economia.uol.com.br') {
    if (c.titulo) m.titulo = c.titulo;
    if (c.autorUol) m.autor = c.autorUol;
    if (truncado(m.subtitulo)) m.subtitulo = '';
  }

  if (h === 'www.gazetadopovo.com.br' && c.dataVisivel) {
    m.data = c.dataVisivel;
  }

  if (/\[…\]\s*$/.test(norm(m.subtitulo))) m.subtitulo = '';

  return m;
}

async function extrairMateria(url) {
  const m = await base.extrairMateria(url);
  await corrigirCabecalho(m);
  limparTexto(m);
  if (!m.texto) throw new Error('O texto ficou vazio após as correções de limpeza.');
  return formatar(m);
}

module.exports = {
  ...base,
  VERSAO,
  extrairMateria,
  limparTexto,
  corrigirCabecalho,
  cabecalho,
  autorVisivelUol,
  dataVisivelProximaH1
};
