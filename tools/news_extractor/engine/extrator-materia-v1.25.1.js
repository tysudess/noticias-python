const { JSDOM } = require('jsdom');
const { Readability } = require('@mozilla/readability');
const readline = require('readline');
const fs = require('fs');
const { spawnSync } = require('child_process');
const path = require('path');
const { fetch: undiciFetch, ProxyAgent } = require('undici');

function obterVersaoUndici() {
  try {
    return require('undici/package.json').version || 'desconhecida';
  } catch (_) {
    return 'desconhecida';
  }
}

const VERSAO = '1.25.1-UNDICI-COMPATIVEL-PROXY-CORPORATIVO';
const ARQUIVO_CONFIG_PROXY = path.join(__dirname, 'config-proxy.json');
const EVITAR_URL_DUPLICADA_NO_HISTORICO = true;
let PROXY_AGENT = null;
let PROXY_AGENT_OPTIONS = null;
let PROXY_STATUS = { ativo: false, descricao: 'Direto (sem proxy)' };

function carregarConfigProxy() {
  const padrao = {
    ATIVADO: false,
    SERVIDOR: '',
    PORTA: '',
    TIMEOUT_MS: 45000,
    CERTIFICADO_CA: ''
  };

  if (!fs.existsSync(ARQUIVO_CONFIG_PROXY)) return padrao;

  try {
    const conteudo = fs.readFileSync(ARQUIVO_CONFIG_PROXY, 'utf8').replace(/^\uFEFF/, '');
    return { ...padrao, ...JSON.parse(conteudo) };
  } catch (erro) {
    throw new Error(`Falha ao ler config-proxy.json: ${erro.message}`);
  }
}

function prepararProxy(usuarioSessao = '', senhaSessao = '', configInformada = null) {
  const config = configInformada || carregarConfigProxy();
  const ativo = config.ATIVADO === true || /^(?:sim|true|1)$/i.test(String(config.ATIVADO || ''));

  if (!ativo) {
    PROXY_AGENT = null;
    PROXY_AGENT_OPTIONS = null;
    PROXY_STATUS = { ativo: false, descricao: 'Direto (sem proxy)' };
    return config;
  }

  const servidorBruto = String(config.SERVIDOR || '').trim();
  const porta = String(config.PORTA || '').trim();
  const usuario = String(usuarioSessao || '').trim();
  const senha = String(senhaSessao || '');

  if (!servidorBruto) throw new Error('Proxy ativado, mas SERVIDOR está vazio em config-proxy.json.');
  if (!porta) throw new Error('Proxy ativado, mas PORTA está vazia em config-proxy.json.');
  if (!usuario) throw new Error('Usuário do proxy não informado.');
  if (!senha) throw new Error('Senha do proxy não informada.');

  const servidor = /^https?:\/\//i.test(servidorBruto) ? servidorBruto : `http://${servidorBruto}`;
  const uri = `${servidor.replace(/\/$/, '')}:${porta}`;

  const opcoes = {
    uri,
    token: `Basic ${Buffer.from(`${usuario}:${senha}`, 'utf8').toString('base64')}`
  };

  PROXY_AGENT_OPTIONS = { ...opcoes };
  PROXY_AGENT = new ProxyAgent(PROXY_AGENT_OPTIONS);
  PROXY_STATUS = {
    ativo: true,
    descricao: `${uri} | usuário informado nesta sessão`
  };

  return config;
}

function esperar(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function detalhesErroRede(erro) {
  const itens = [
    erro?.name,
    erro?.message,
    erro?.code,
    erro?.cause?.name,
    erro?.cause?.message,
    erro?.cause?.code,
    erro?.cause?.errno
  ].filter(Boolean).map(String);
  return itens.join(' | ');
}

function ehErroRedeTransitorio(erro) {
  const texto = detalhesErroRede(erro);
  return /request was cancelled|fetch failed|econnreset|econnaborted|econnclosed|socket hang up|other side closed|und_err_socket|und_err_connect_timeout|und_err_headers_timeout|und_err_body_timeout|etimedout|eai_again|network.*reset|terminated/i.test(texto);
}

async function renovarAgenteProxy() {
  if (!PROXY_STATUS.ativo || !PROXY_AGENT_OPTIONS) return;

  const antigo = PROXY_AGENT;
  PROXY_AGENT = new ProxyAgent(PROXY_AGENT_OPTIONS);

  if (antigo && typeof antigo.close === 'function') {
    try {
      await Promise.race([
        antigo.close(),
        esperar(1200)
      ]);
    } catch (_) {}
  }
}

async function fetchComRetry(url, opcoes = {}, configuracao = {}) {
  const tentativas = Math.max(1, Number(configuracao.tentativas) || 3);
  const timeoutMs = Math.max(5000, Number(configuracao.timeoutMs) || 45000);
  let ultimoErro = null;

  for (let tentativa = 1; tentativa <= tentativas; tentativa++) {
    try {
      const resposta = await undiciFetch(url, {
        ...opcoes,
        dispatcher: PROXY_AGENT || opcoes.dispatcher || undefined,
        signal: AbortSignal.timeout(timeoutMs)
      });

      if ([502, 503, 504].includes(resposta.status) && tentativa < tentativas) {
        try { await resposta.body?.cancel(); } catch (_) {}
        console.log(`Conexão temporariamente indisponível (HTTP ${resposta.status}). Nova tentativa ${tentativa + 1}/${tentativas}...`);
        if (PROXY_STATUS.ativo) await renovarAgenteProxy();
        await esperar(700 * tentativa);
        continue;
      }

      return resposta;
    } catch (erro) {
      ultimoErro = erro;
      const transitorio = ehErroRedeTransitorio(erro);

      if (!transitorio || tentativa >= tentativas) break;

      console.log(`Conexão interrompida. Nova tentativa ${tentativa + 1}/${tentativas}...`);
      if (PROXY_STATUS.ativo) await renovarAgenteProxy();
      await esperar(700 * tentativa);
    }
  }

  throw ultimoErro || new Error('Falha de rede após as tentativas automáticas.');
}

function mensagemErroRede(erro) {
  const texto = detalhesErroRede(erro);

  if (/407|proxy authentication required/i.test(texto)) {
    return 'O proxy recusou a autenticação (HTTP 407). Verifique usuário/senha ou o tipo de autenticação exigido pela rede.';
  }
  if (/self signed certificate|unable to verify|certificate|cert_/i.test(texto)) {
    return 'A conexão HTTPS foi bloqueada por certificado da rede. Não desative a segurança TLS; configure o certificado CA corporativo no Node.js.';
  }
  if (/enotfound|getaddrinfo/i.test(texto)) {
    return `Não foi possível localizar o servidor de rede/proxy. Detalhe: ${texto}`;
  }
  if (/econnrefused/i.test(texto)) {
    return `Conexão recusada pelo servidor/proxy. Detalhe: ${texto}`;
  }
  if (/request was cancelled/i.test(texto)) {
    return `A conexão foi cancelada durante a leitura da página após as tentativas automáticas. Detalhe: ${texto}`;
  }
  if (/etimedout|timeout|und_err_connect_timeout|und_err_headers_timeout|und_err_body_timeout/i.test(texto)) {
    return `Tempo esgotado ao acessar a internet. Detalhe: ${texto}`;
  }
  if (/econnreset|econnaborted|und_err_socket|socket hang up|other side closed|terminated/i.test(texto)) {
    return `A conexão foi interrompida pelo site, proxy ou rede. Detalhe: ${texto}`;
  }

  return texto || 'Falha de rede sem detalhe adicional.';
}

const CABECALHOS_LIXO = [
  'veja também','leia também','leia mais','veja mais','saiba mais','conteúdo relacionado','conteúdos relacionados','matéria relacionada','matérias relacionadas','notícia relacionada','notícias relacionadas','recomendamos','recomendado para você','mais lidas','mais lidos','confira também','confira ainda','você também pode gostar','vale ler também','vale ler tambem','vale a leitura','para ler também','para ler tambem','vídeos em alta no g1','videos em alta no g1','cortes 247','vale ler também','vale ler tambem'
];

const PREFIXOS_LIXO = [
  'publicidade','anúncio','foto:','fotos:','crédito:','créditos:','imagem:','imagens:','reprodução:','divulgação:','assine nossa newsletter','assine a newsletter','receba nossas notícias','receba as notícias','siga-nos','siga a gente','compartilhe','clique aqui para assinar','acompanhe os mercados','acompanhe o mercado','acompanhe as cotações','acompanhe as cotacoes','acompanhe nossas ferramentas','acesse nossas ferramentas','não fique refém dos algoritmos','nao fique refem dos algoritmos','em busca de promoções e descontos','em busca de promocoes e descontos','participe no dia a dia do','dê sugestões de matérias','de sugestoes de materias','❗ se você tem algum posicionamento','se você tem algum posicionamento a acrescentar','✅ receba as notícias','receba as notícias do brasil 247','apoie o jornalismo independente'
];

function normalizarEspacos(texto = '') {
  return String(texto)
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .trim();
}

function decodificarEntidadesHtml(texto = '') {
  const bruto = String(texto || '');
  if (!bruto || !/&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);/i.test(bruto)) return bruto;
  try {
    const dom = new JSDOM('<!doctype html><html><body><textarea id="d"></textarea></body></html>');
    const textarea = dom.window.document.querySelector('#d');
    textarea.innerHTML = bruto;
    return textarea.value;
  } catch (_) {
    return bruto;
  }
}

function textoLimpoHtml(texto = '') {
  return normalizarEspacos(decodificarEntidadesHtml(texto));
}

function normalizarComparacao(texto = '') {
  return normalizarEspacos(texto)
    .toLocaleLowerCase('pt-BR')
    .replace(/[“”"'‘’]/g, '')
    .replace(/[.:;!?]+$/g, '')
    .trim();
}

function extrairSubtituloODiaPeloTitulo(document, titulo = '') {
  const tituloEsperado = normalizarComparacao(titulo);
  if (!tituloEsperado) return '';
  const h1s = [...document.querySelectorAll('h1')];
  let h1Materia = h1s.find(el => normalizarComparacao(textoLimpoHtml(el.textContent || '')) === tituloEsperado);
  if (!h1Materia) {
    h1Materia = h1s.find(el => {
      const t = normalizarComparacao(textoLimpoHtml(el.textContent || ''));
      return t && (t.includes(tituloEsperado) || tituloEsperado.includes(t));
    });
  }
  if (!h1Materia) return '';
  const elementos = [...document.querySelectorAll('body *')];
  const indiceH1 = elementos.indexOf(h1Materia);
  if (indiceH1 >= 0) {
    for (let i = indiceH1 + 1; i < Math.min(elementos.length, indiceH1 + 80); i++) {
      const el = elementos[i];
      const tag = String(el.tagName || '').toUpperCase();
      const texto = textoLimpoHtml(el.textContent || '');
      if (tag === 'P' && /^angra dos reis\s*[-–—:]\s+/i.test(texto)) break;
      if (tag !== 'H2') continue;
      if (candidatoSubtituloODiaValido(texto, titulo)) return texto;
    }
  }
  let pai = h1Materia.parentElement;
  for (let nivel = 0; pai && nivel < 4; nivel++, pai = pai.parentElement) {
    for (const h2 of pai.querySelectorAll('h2')) {
      const pos = h1Materia.compareDocumentPosition(h2);
      const estaDepois = Boolean(pos & 4);
      if (!estaDepois) continue;
      const texto = textoLimpoHtml(h2.textContent || '');
      if (candidatoSubtituloODiaValido(texto, titulo)) return texto;
    }
  }
  return '';
}

function ehUrlODia(url = '') {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host === 'odia.ig.com.br' || host.endsWith('.odia.ig.com.br');
  } catch (_) { return false; }
}

function ehMetadadoPublicacaoODia(texto = '') {
  const linha = normalizarEspacos(texto);
  if (!linha) return false;
  return /^publicado\s+\d{1,2}\/\d{1,2}\/\d{4}\s+\d{1,2}:\d{2}(?:\s*\|\s*atualizado\s+\d{1,2}\/\d{1,2}\/\d{4}\s+\d{1,2}:\d{2})?$/i.test(linha);
}

function ehLegendaCreditoODia(texto = '') {
  const linha = normalizarEspacos(texto);
  if (!linha || linha.length > 320) return false;
  const fontesFoto = ['reprodução','reproducao','divulgação','divulgacao','arquivo redação','arquivo redacao','arquivo pessoal','brazil news','agnews','instagram','facebook','assessoria'];
  const comp = normalizarComparacao(linha);
  if (fontesFoto.some(f => comp.endsWith(normalizarComparacao(f)))) return true;
  if (/\b(?:divulgação|divulgacao|reprodução|reproducao)\s*\/\s*(?:arquivo(?:\s+redação|\s+redacao)?|assessoria)\s*$/i.test(linha)) return true;
  if (/\/\s*(?:brazil\s+news|agnews|arquivo(?:\s+redação|\s+redacao)?|divulgação|divulgacao|reprodução|reproducao|assessoria)\s*$/i.test(linha)) return true;
  return false;
}

function limparCorpoODia(texto = '', url = '') {
  if (!ehUrlODia(url)) return texto;
  const blocos = String(texto || '').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);
  return blocos.filter(b => !ehMetadadoPublicacaoODia(b) && !ehLegendaCreditoODia(b)).join('\n\n').trim();
}

function obterUrlAmpDeclaradaODia(document, url = '') {
  if (!ehUrlODia(url)) return '';
  try {
    const href = document?.querySelector?.('link[rel="amphtml"]')?.getAttribute('href') || document?.querySelector?.('link[rel~="amphtml"]')?.getAttribute('href') || '';
    if (!href) return '';
    return new URL(href, url).toString();
  } catch (_) { return ''; }
}

function montarUrlAmpODia(url = '') {
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    if (!(host === 'odia.ig.com.br' || host.endsWith('.odia.ig.com.br'))) return '';
    if (/\/amp\//i.test(u.pathname)) return u.toString();
    const novoPath = u.pathname.replace(/\/(\d{4})\/(\d{2})\/(?!amp\/)/, '/$1/$2/amp/');
    if (novoPath === u.pathname) return '';
    u.pathname = novoPath;
    return u.toString();
  } catch (_) { return ''; }
}

async function extrairCabecalhoAmpODia(url, timeoutMs = 45000, documentOrigem = null) {
  const urlsTentativa = [];
  const ampDeclarada = obterUrlAmpDeclaradaODia(documentOrigem, url);
  if (ampDeclarada) urlsTentativa.push(ampDeclarada);
  const ampMontada = montarUrlAmpODia(url);
  if (ampMontada && !urlsTentativa.includes(ampMontada)) urlsTentativa.push(ampMontada);
  if (!urlsTentativa.length) return { titulo: '', subtitulo: '' };
  for (const urlAmp of urlsTentativa) {
    let respostaAmp;
    try {
      respostaAmp = await fetchComRetry(urlAmp, { redirect:'follow', headers:{ 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36', 'Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8', 'Accept':'text/html,application/xhtml+xml', 'Connection':'close' } }, { timeoutMs, tentativas:3 });
    } catch (_) { continue; }
    if (!respostaAmp.ok) continue;
    let htmlAmp='';
    try { htmlAmp = await respostaAmp.text(); } catch (_) { continue; }
    if (!htmlAmp) continue;
    try {
      const domAmp = new JSDOM(htmlAmp, { url: urlAmp });
      const docAmp = domAmp.window.document;
      const h1 = [...docAmp.querySelectorAll('h1')].find(el => textoLimpoHtml(el.textContent || '').length >= 8) || null;
      let tituloAmp = h1 ? textoLimpoHtml(h1.textContent || '') : '';
      let subtituloAmp = '';
      if (h1) {
        let el = h1.nextElementSibling;
        for (let i=0; el && i<20; i++, el=el.nextElementSibling) {
          const h2 = el.matches?.('h2') ? el : el.querySelector?.('h2');
          if (h2) {
            const t = textoLimpoHtml(h2.textContent || '');
            if (candidatoSubtituloODiaValido(t, tituloAmp)) { subtituloAmp=t; break; }
          }
        }
      }
      if (!subtituloAmp) {
        for (const h2 of docAmp.querySelectorAll('h2')) {
          const t = textoLimpoHtml(h2.textContent || '');
          if (candidatoSubtituloODiaValido(t, tituloAmp)) { subtituloAmp=t; break; }
        }
      }
      if (!subtituloAmp) {
        const objetosAmp=lerJsonLd(docAmp); const artigoAmpLd=escolherJsonLdArtigo(objetosAmp);
        const cand=[artigoAmpLd.description,textoMeta(docAmp,['meta[property="og:description"]']),textoMeta(docAmp,['meta[name="description"]']),textoMeta(docAmp,['meta[name="twitter:description"]'])];
        for (const c of cand) { const t=textoLimpoHtml(c||''); if (candidatoSubtituloODiaValido(t,tituloAmp)) { subtituloAmp=t; break; } }
      }
      if (tituloAmp || subtituloAmp) return { titulo: tituloAmp, subtitulo: subtituloAmp };
    } catch (_) { continue; }
  }
  return { titulo:'', subtitulo:'' };
}

function extrairSubtituloODiaRobusto(document, htmlBruto = '', titulo = '') {
  for (const h2 of document.querySelectorAll('h2')) {
    const texto = textoLimpoHtml(h2.textContent || '');
    if (candidatoSubtituloODiaValido(texto, titulo)) return texto;
  }
  const bruto = String(htmlBruto || '');
  const re = /<h2\b[^>]*>([\s\S]*?)<\/h2>/gi;
  let m;
  while ((m = re.exec(bruto))) {
    let trecho = m[1].replace(/<script\b[\s\S]*?<\/script>/gi,' ').replace(/<style\b[\s\S]*?<\/style>/gi,' ').replace(/<[^>]+>/g,' ');
    const texto = textoLimpoHtml(trecho);
    if (candidatoSubtituloODiaValido(texto,titulo)) return texto;
  }
  return '';
}

function extrairSubtituloVisivel(document, url = '') {
  const seletores = ['[data-testid*="subtitle" i]','[data-testid*="subheadline" i]','[class*="subtitle" i]','[class*="subtitulo" i]','[class*="subheadline" i]','[class*="article-lead" i]','[class*="article__lead" i]','[class*="post-excerpt" i]','[class*="entry-summary" i]','[class*="headline__subtitle" i]','[class*="dek" i]'];
  for (const seletor of seletores) {
    try {
      for (const el of document.querySelectorAll(seletor)) {
        const texto = textoLimpoHtml(el.textContent);
        if (texto.length >= 25 && texto.length <= 600) return texto;
      }
    } catch (_) {}
  }
  const h1=document.querySelector('h1');
  if (h1) {
    let host=''; try { host=new URL(url).hostname.toLowerCase(); } catch (_) {}
    if (host==='odia.ig.com.br'||host.endsWith('.odia.ig.com.br')) {
      const candidatosLocais=[];
      if (h1.parentElement) candidatosLocais.push(...h1.parentElement.querySelectorAll('h2'));
      if (h1.parentElement?.parentElement) candidatosLocais.push(...h1.parentElement.parentElement.querySelectorAll(':scope > h2, :scope > div > h2'));
      for (const el of candidatosLocais) {
        const texto=textoLimpoHtml(el.textContent);
        if (texto.length>=25&&texto.length<=600&&normalizarComparacao(texto)!==normalizarComparacao(h1.textContent)) return texto;
      }
    }
    let atual=h1.nextElementSibling;
    for (let i=0; atual&&i<8; i++,atual=atual.nextElementSibling) {
      const h2=atual.matches?.('h2')?atual:atual.querySelector?.('h2');
      const alvo=h2||atual; const texto=textoLimpoHtml(alvo?.textContent||'');
      if (texto.length>=30&&texto.length<=500&&!/^(?:por|by)\b/i.test(texto)) return texto;
    }
  }
  return '';
}

function decodificarStringJsonSolta(valor = '') {
  const bruto=String(valor||'');
  try { return JSON.parse(`"${bruto.replace(/"/g,'\\"')}"`); }
  catch (_) { return bruto.replace(/\\u([0-9a-f]{4})/gi,(_,h)=>String.fromCharCode(parseInt(h,16))).replace(/\\n|\\r|\\t/g,' ').replace(/\\\//g,'/').replace(/\\"/g,'"'); }
}

function candidatoSubtituloODiaValido(texto = '', titulo = '') {
  const t=textoLimpoHtml(texto); if(!t||t.length<25||t.length>650)return false;
  const nt=normalizarComparacao(t), nTitulo=normalizarComparacao(titulo);
  if(!nt||nt===nTitulo)return false; if(nTitulo&&(nt.startsWith(nTitulo)||nTitulo.startsWith(nt)))return false;
  if(/^(?:angra dos reis|rio de janeiro|o dia)$/i.test(t))return false;
  if(/^(?:publicado|atualizado|por|redação|redacao)\b/i.test(t))return false;
  if(/\b[\w.+-]+@odia\.com\.br\b/i.test(t))return false;
  if(/^\d{1,2}\/\d{1,2}\/\d{4}(?:\s|$)/.test(t))return false;
  if(/^angra dos reis\s*[-–—:]\s+/i.test(t))return false;
  if(/^(?:foto|crédito|credito|divulgação|divulgacao)\s*:/i.test(t))return false;
  if(/^(?:você pode gostar|voce pode gostar|comentários|comentarios|publicidade)$/i.test(t))return false;
  return true;
}

function extrairSubtituloDeScriptsODia(document, titulo='') {
  const chavesFortes=['subtitulo','subTitulo','subtitle','subTitle','linhaFina','linha_fina','linha-fina','linha fina','summary','resumo'];
  const candidatos=[];
  for(const script of document.querySelectorAll('script')){
    const bruto=String(script.textContent||''); if(!bruto||bruto.length>5000000)continue;
    for(const chave of chavesFortes){
      const esc=chave.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/ /g,'\\s*');
      const re=new RegExp(`["']${esc}["']\\s*:\\s*["']((?:\\\\.|[^"']){20,900})["']`,'ig'); let m;
      while((m=re.exec(bruto))){ const texto=textoLimpoHtml(decodificarStringJsonSolta(m[1])); if(candidatoSubtituloODiaValido(texto,titulo))candidatos.push(texto); if(candidatos.length>=20)break; }
    }
    if(candidatos.length>=20)break;
  }
  if(!candidatos.length)return '';
  candidatos.sort((a,b)=>{const score=x=>(x.length>=45&&x.length<=320?1000:0)-Math.abs(160-x.length); return score(b)-score(a);});
  return candidatos[0];
}

function extrairSubtituloPorProximidadeODia(document,titulo=''){
  const todos=[...document.querySelectorAll('body *')]; if(!todos.length)return '';
  const nTitulo=normalizarComparacao(titulo); let indice=-1; const h1=document.querySelector('h1'); if(h1)indice=todos.indexOf(h1);
  if(indice<0&&nTitulo){ for(let i=0;i<todos.length;i++){const el=todos[i]; if(['SCRIPT','STYLE','NOSCRIPT','META','TITLE'].includes(el.tagName))continue; const texto=textoLimpoHtml(el.textContent||''); if(normalizarComparacao(texto)!==nTitulo)continue; if(el.children.length<=3){indice=i;break;}}}
  if(indice<0)return '';
  const vistos=new Set();
  for(let i=indice+1;i<Math.min(todos.length,indice+140);i++){const el=todos[i]; const tag=el.tagName; if(['SCRIPT','STYLE','NOSCRIPT','SVG','PATH','BUTTON','A'].includes(tag))continue; if(el.children.length>4&&!['P','H2','H3'].includes(tag))continue; const texto=textoLimpoHtml(el.textContent||''); if(!texto||vistos.has(texto))continue; vistos.add(texto); if(/^angra dos reis\s*[-–—:]\s+/i.test(texto))break; if(candidatoSubtituloODiaValido(texto,titulo))return texto;}
  return '';
}

function extrairSubtituloODia(document,titulo=''){const script=extrairSubtituloDeScriptsODia(document,titulo); if(script)return script; const proximo=extrairSubtituloPorProximidadeODia(document,titulo); if(proximo)return proximo; return '';}

function escolherTextoMaisCompleto(atual='',visivel=''){const a=textoLimpoHtml(atual),v=textoLimpoHtml(visivel); if(!v)return a;if(!a)return v;const atualTruncado=/(?:\.\.\.|…)$/.test(a)||/\b(?:a|o|de|do|da|dos|das|em|no|na|para|por|com)$/i.test(a);const visivelMaior=v.length>=a.length+8;if(atualTruncado&&visivelMaior)return v;return a;}
function pareceTruncado(texto=''){const t=textoLimpoHtml(texto);if(!t)return false;if(/(?:\.\.\.|…)$/.test(t))return true;if(/\b(?:a|o|e|de|do|da|dos|das|em|no|na|nos|nas|para|por|com|sem|del)$/i.test(t))return true;if(/\s[A-Za-zÀ-ÿ]$/.test(t))return true;return false;}
function escolherMelhorTitulo(candidatos=[],veiculo=''){const limpos=[],vistos=new Set();for(const item of candidatos){let t=limparTitulo(textoLimpoHtml(item),veiculo);if(!t||t.length<8||t.length>500)continue;const chave=normalizarComparacao(t);if(vistos.has(chave))continue;vistos.add(chave);limpos.push(t);}if(!limpos.length)return'';const completos=limpos.filter(t=>!pareceTruncado(t));const base=completos.length?completos:limpos;return base.sort((a,b)=>b.length-a.length)[0];}
function primeiroParagrafo(texto=''){return String(texto||'').split(/\n\n+/).map(normalizarEspacos).find(Boolean)||'';}
function primeiraFrase(texto=''){const t=normalizarEspacos(texto);if(!t)return'';const m=t.match(/^(.{40,420}?[.!?])(?:\s|$)/);return m?m[1].trim():'';}
function removerPrefixoAutorDoSubtitulo(subtitulo='',autor=''){let s=textoLimpoHtml(subtitulo);const a=textoLimpoHtml(autor);if(!s)return'';if(a){const esc=a.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');s=s.replace(new RegExp(`^por\\s+${esc}\\s*[-–—:]?\\s*`,'i'),'').trim();}return s.replace(/^por\s+[A-ZÀ-Ý][^\n]{2,80}?\s+(?=[A-ZÀ-Ý])/u,'').trim();}
function corrigirSubtituloTruncadoComCorpo(subtitulo='',autor='',texto=''){let s=limparSubtitulo(subtitulo);if(!s||!pareceTruncado(s))return s;const p1=primeiroParagrafo(texto);if(!p1)return s;const semAutor=removerPrefixoAutorDoSubtitulo(s,autor);const compSub=normalizarComparacao(semAutor),compP1=normalizarComparacao(p1);const prefixo=compSub.length>=25&&compP1.startsWith(compSub.slice(0,Math.max(25,compSub.length-2)));if(prefixo){const frase=primeiraFrase(p1);if(frase&&frase.length>=40&&frase.length<=420)return frase;}return'';}

function hostDaUrl(url=''){try{return new URL(url).hostname.toLowerCase();}catch(_){return'';}}
function caminhoDaUrl(url=''){try{return new URL(url).pathname.toLowerCase();}catch(_){return'';}}

function normalizarVeiculo(veiculo='',url=''){
  let v=textoLimpoHtml(veiculo),host='';try{host=new URL(url).hostname.toLowerCase();}catch(_){}
  const mapa=[[/^cbn(?:\.globo\.com)?$/i,'CBN'],[/^g1$/i,'G1'],[/^veja$/i,'VEJA']];for(const[re,nome]of mapa){if(re.test(v))return nome;}
  if(host==='cbn.globo.com')return'CBN';if(host==='ge.globo.com')return'ge';if(host==='g1.globo.com')return'G1';if(host==='www.atribuna.com.br'||host==='atribuna.com.br'||host.endsWith('.atribuna.com.br'))return'A Tribuna';if(host==='sbtnews.sbt.com.br')return'SBT News';if(host==='www.em.com.br'||host==='em.com.br')return'Estado de Minas';if(host==='www.correiobraziliense.com.br'||host==='correiobraziliense.com.br')return'Correio Braziliense';if(host==='noticias.r7.com'||host.endsWith('.r7.com'))return'R7';if(host==='www.oliberal.com'||host==='oliberal.com')return'O Liberal';if(host==='gauchazh.clicrbs.com.br')return'GZH';if(host==='www.cnnbrasil.com.br'||host==='cnnbrasil.com.br')return'CNN Brasil';if(host==='www.nsctotal.com.br'||host==='nsctotal.com.br')return'NSC Total';if(host==='ndmais.com.br'||host==='www.ndmais.com.br')return'ND Mais';return v;
}

function ehMetadadoPoder360(texto=''){const t=normalizarEspacos(texto);return /^PODER360\s+\d{1,2}[.]?[a-zç]{3}[.]?\d{2,4}\s*\([^)]+\)\s*[-–—]\s*\d{1,2}h\d{2}\b/i.test(t);}
function ehChamadaRelacionadaOGloboBlog(texto='',url=''){let host='',pathname='';try{const u=new URL(url);host=u.hostname.toLowerCase();pathname=u.pathname.toLowerCase();}catch(_){}if(host!=='oglobo.globo.com'||!pathname.includes('/blogs/'))return false;const t=normalizarEspacos(texto);if(t.length<45||t.length>220||/[?]$/.test(t))return false;if(/[”"’']\s*,?\s*(?:afirma|diz|revela|conta|explica)\b/i.test(t))return true;if(/^ex[-\s].{5,120}\b(?:detalha|revela|conta|explica|afirma|diz)\b/i.test(t))return true;return false;}
function limparTituloPorPortal(titulo='',url=''){let t=textoLimpoHtml(titulo);const host=hostDaUrl(url);if(host==='valor.globo.com'||host.endsWith('.valor.globo.com')||host==='oglobo.globo.com'||host.endsWith('.oglobo.globo.com')||host==='www.oliberal.com'||host==='oliberal.com')t=t.replace(/\s*\|\s*[^|]{2,90}$/u,'').trim();if(host==='noticias.r7.com'||host.endsWith('.r7.com'))t=t.replace(/\s*[–—-]\s*not[ií]cias\s+r7\s*$/iu,'').trim();if(host==='gauchazh.clicrbs.com.br')t=t.replace(/\s*\|\s*[^|]{2,90}$/u,'').trim();if(host==='www.correiobraziliense.com.br'||host==='correiobraziliense.com.br')t=t.replace(/\s*[-–—]\s*Correio\s+Braziliense\s*[-–—]\s*(?:Aqui|Radar)\s*$/iu,'').trim();return t;}
function ehLegendaFotoGlobo(texto=''){const t=normalizarEspacos(texto);if(!t||t.length>320)return false;return /\s[—–-]\s*foto\s*:/i.test(t)||/^foto\s*:/i.test(t);}
function palavrasComparacaoBloco(texto=''){return new Set(normalizarEspacos(texto).toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').match(/[a-z0-9]{4,}/g)||[]);}
function similaridadeBlocos(a='',b=''){const A=palavrasComparacaoBloco(a),B=palavrasComparacaoBloco(b);if(A.size<5||B.size<5)return 0;let inter=0;for(const x of A)if(B.has(x))inter++;return inter/Math.min(A.size,B.size);}
function intersecaoPalavrasBlocos(a='',b=''){const A=palavrasComparacaoBloco(a),B=palavrasComparacaoBloco(b);let inter=0;for(const x of A)if(B.has(x))inter++;return{inter,a:A.size,b:B.size};}
function removerBlocosSemelhantes(texto='',url=''){const host=hostDaUrl(url);if(host!=='g1.globo.com'&&host!=='ge.globo.com')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];for(const bloco of blocos){let duplicado=false;if(bloco.length>=70){for(const anterior of saida.slice(-7)){if(anterior.length<70)continue;if(similaridadeBlocos(bloco,anterior)>=0.72){duplicado=true;break;}}}if(!duplicado)saida.push(bloco);}return saida.join('\n\n').trim();}

function limparCorpoGloboNoticias(texto='',url='',titulo=''){
  const host=hostDaUrl(url);if(host!=='g1.globo.com'&&host!=='ge.globo.com')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];
  for(let i=0;i<blocos.length;i++){const bloco=blocos[i],comp=normalizarComparacao(bloco);if(ehLegendaFotoGlobo(bloco))continue;if(/^agora\s+no\s+g1$/i.test(bloco))break;if(/^(?:📱\s*)?veja\s+outras\s+not[ií]cias\s+da\s+regi[aã]o\s+no\s+g1\b/i.test(bloco))continue;if(titulo&&bloco.length>=30&&bloco.length<=180&&!/[.!?]\s*$/.test(bloco)){const simTitulo=similaridadeBlocos(bloco,titulo);if(simTitulo>=0.72)continue;if(host==='g1.globo.com'&&i<8&&saida.length>=2){const proximo=blocos[i+1]||'',palavras=intersecaoPalavrasBlocos(bloco,titulo),quantidadePalavras=palavrasComparacaoBloco(bloco).size,pareceManchete=quantidadePalavras>=7&&palavras.inter>=2,entreParagrafos=proximo.length>=90&&/[.!?][”"']?\s*$/.test(proximo);if(pareceManchete&&entreParagrafos)continue;}}if(host==='ge.globo.com'){if(/^voz\s+do\s+setorista\s*:/i.test(bloco))continue;if(/^assista\s*:\s*tudo\s+sobre\b/i.test(bloco))continue;if(comp==='mais do ge'){let removidos=0;while(saida.length&&removidos<4){const ultimo=saida[saida.length-1];if(ultimo.length>=25&&ultimo.length<=190&&!/[.!?][”"']?$/.test(ultimo)){saida.pop();removidos++;}else break;}break;}}saida.push(bloco);}return removerBlocosSemelhantes(saida.join('\n\n'),url);
}

function limparCorpoSBT(texto='',url=''){if(hostDaUrl(url)!=='sbtnews.sbt.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);return blocos.filter(bloco=>{if(/^\d{1,2}\/\d{1,2}\/\d{4}\s*,\s*\d{1,2}:\d{2}\s*[•·|-]\s*atualizado\b/i.test(bloco))return false;if(bloco.length<320&&/\|\s*[A-ZÀ-Ý][^|]{1,120}\/(?:Ag[eê]ncia|Agencia|Divulgação|Divulgacao|Arquivo|SBT|Reuters|AFP|AP)\b/i.test(bloco))return false;if(/receba\s+as\s+principais\s+not[ií]cias.*whatsapp/i.test(bloco))return false;return true;}).join('\n\n').trim();}
function limparCorpoEstadoMinas(texto='',url=''){const host=hostDaUrl(url);if(host!=='em.com.br'&&host!=='www.em.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);return blocos.filter((bloco,i)=>{if(i<4&&bloco.length<330&&/^(?:rep[oó]rter|jornalista|colunista)\b.*\b(?:formad[oa]|graduad[oa]|experi[eê]ncia|especializad[oa])\b/i.test(bloco))return false;if(/^\d{1,2}\/\d{1,2}\/\d{4}\s+\d{1,2}:\d{2}\s*[-–—]\s*atualizado\s+em\s+\d{1,2}\/\d{1,2}\/\d{4}\s+\d{1,2}:\d{2}$/i.test(bloco))return false;if(/^uma\s+ferramenta\s+de\s+ia\s+foi\s+usada\b/i.test(bloco))return false;return true;}).join('\n\n').trim();}
function limparCorpoPoder360(texto='',url=''){if(!hostDaUrl(url).includes('poder360.com.br'))return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!(bloco.length<170&&/^[A-ZÀ-Ý][A-Za-zÀ-ÿ0-9 .()/-]{2,90}\s*[-–—]\s*\d{1,2}[.]?[a-zç]{3}[.]?\d{2,4}$/i.test(bloco))).join('\n\n').trim();}
function limparCorpoIstoe(texto='',url=''){const host=hostDaUrl(url);if(host!=='istoe.com.br'&&host!=='www.istoe.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);if(blocos.length<5)return texto;let fimResumo=1;while(fimResumo<Math.min(blocos.length,5)){const b=blocos[fimResumo];if(b.length>=45&&b.length<=190&&/[.!]$/.test(b))fimResumo++;else break;}if(fimResumo>=3&&blocos[fimResumo]&&blocos[fimResumo].length<=100&&!/[.!?]$/.test(blocos[fimResumo]))return[blocos[0],...blocos.slice(fimResumo)].join('\n\n').trim();return texto;}

function extrairCorpoAlternativoATribuna(document,artigoLd={},metadados={},url=''){if(!hostDaUrl(url).endsWith('atribuna.com.br'))return'';const artigoBody=textoLimpoHtml(artigoLd?.articleBody||'');if(artigoBody.length>=300){const blocos=artigoBody.replace(/\r/g,'').split(/\n{1,}/).map(limparChamadasInline).filter(Boolean).filter(x=>!ehLinhaLixo(x));const texto=blocos.join('\n\n').trim();if(texto.length>=300)return texto;}const seletores=['[itemprop="articleBody"]','article [class*="article-body" i]','article [class*="article-content" i]','article [class*="content" i]','[class*="article-body" i]','[class*="article-content" i]','[class*="materia" i] [class*="conteudo" i]','[class*="noticia" i] [class*="conteudo" i]'];let melhor='';for(const seletor of seletores){let els=[];try{els=[...document.querySelectorAll(seletor)];}catch(_){continue;}for(const el of els){const clone=el.cloneNode(true);removerElementosObvios(clone);const partes=[...clone.querySelectorAll('p, blockquote, h2, h3, li')].map(x=>limparChamadasInline(x.textContent||'')).filter(Boolean).filter(x=>!ehLinhaLixo(x)).filter(x=>!/^clique\s+aqui\s+para\s+seguir.*whatsapp/i.test(x));const cand=partes.join('\n\n').trim();if(cand.length>melhor.length)melhor=cand;}}return melhor.length>=300?melhor:'';}
function pareceNavegacaoATribuna(texto=''){const t=normalizarComparacao(texto);return /meu perfildesconectar/.test(t)||/fundado em 1894 e online desde 1996/.test(t)||/publicidade legalassinante/.test(t);}

function corrigirUolDeutscheWelle(titulo='',subtitulo='',texto='',url=''){const host=hostDaUrl(url),path=caminhoDaUrl(url);if(host!=='noticias.uol.com.br'||!path.includes('/deutschewelle/'))return{subtitulo,texto};const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);if(!blocos.length)return{subtitulo,texto};const primeiro=blocos[0].replace(/([.!?])(?=[A-ZÀ-Ý])/g,'$1 '),escTitulo=textoLimpoHtml(titulo).replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),reInicio=new RegExp(`^${escTitulo}\\s*[-–—:]\\s*`,'i');if(!reInicio.test(primeiro))return{subtitulo:limparSubtitulo(subtitulo),texto};const resto=primeiro.replace(reInicio,'').trim(),frases=[...resto.matchAll(/[^.!?]+[.!?](?:\s+|$)/g)];if(frases.length<3)return{subtitulo:limparSubtitulo(subtitulo),texto};const subtNovo=normalizarEspacos(frases.slice(0,2).map(m=>m[0]).join(' ')),posFim=frases[1].index+frases[1][0].length,corpoPrimeiro=normalizarEspacos(resto.slice(posFim));if(subtNovo.length>=50&&subtNovo.length<=420&&corpoPrimeiro.length>=80){blocos[0]=corpoPrimeiro;return{subtitulo:subtNovo,texto:blocos.join('\n\n').trim()};}return{subtitulo:limparSubtitulo(subtitulo),texto};}
function limparCorpoOLiberal(texto='',url=''){const host=hostDaUrl(url);if(host!=='oliberal.com'&&host!=='www.oliberal.com')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!(bloco.length<360&&/\([^()]{2,140}\s*\/\s*O\s+Liberal\)\s*$/i.test(bloco))).join('\n\n').trim();}
function corrigirUolConfere(subtitulo='',texto='',url=''){const host=hostDaUrl(url),path=caminhoDaUrl(url);if(host!=='noticias.uol.com.br'||!path.includes('/confere/'))return{subtitulo,texto};let s=limparSubtitulo(subtitulo);if(!s)return{subtitulo:s,texto};if(pareceTruncado(s)||/[.!?](?=[A-ZÀ-Ý])/.test(s)||(s.length>260&&!/[.!?]$/.test(s))){const ajustado=s.replace(/([.!?])(?=[A-ZÀ-Ý])/g,'$1 '),m=ajustado.match(/^(.{45,420}?[.!?])(?:\s|$)/);if(m){const primeira=normalizarEspacos(m[1]);if(primeira.length>=45&&primeira.length<=420)s=primeira;}}return{subtitulo:s,texto};}

function limparCorpoMetropoles(texto='',url=''){const host=hostDaUrl(url),path=caminhoDaUrl(url);if(host!=='www.metropoles.com'&&host!=='metropoles.com')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];let emGaleria=false;for(let i=0;i<blocos.length;i++){const bloco=blocos[i];if(/^\d+\s+imagens?$/i.test(bloco)){emGaleria=true;continue;}if(emGaleria){if(/^\d+\s+de\s+\d+$/i.test(bloco))continue;if(bloco.length<=180&&!/[.!?][”"']?$/u.test(bloco))continue;if(bloco.length<=180&&/(?:Metr[oó]poles|Divulga[cç][aã]o|Marinha do Brasil|@\w+)/i.test(bloco))continue;emGaleria=false;}if(path.includes('/artigos/')&&i>=Math.max(0,blocos.length-3)&&bloco.length<700&&/^[A-ZÀ-Ý][^:]{2,90}:\s*/u.test(bloco)&&/\b(?:cofundador|cofundadora|s[oó]cio|s[oó]cia|secret[aá]ri[oa]|minist[eé]rio|consultoria|think\s+tank|organismos internacionais)\b/i.test(bloco))continue;saida.push(bloco);}return saida.join('\n\n').trim();}

function ajustarCorreioBraziliense(autor='',texto='',url=''){const host=hostDaUrl(url);if(host!=='www.correiobraziliense.com.br'&&host!=='correiobraziliense.com.br')return{autor,texto};const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);if(!blocos.length)return{autor,texto};let novoAutor=limparAutor(autor);const primeiro=blocos[0];if(/\s[—–-]\s/.test(primeiro)&&primeiro.length<850){const segmentos=primeiro.split(/;\s*(?=[A-ZÀ-Ý])/u),nomes=[];for(const seg of segmentos){const m=seg.match(/^\s*([^—–]{2,100}?)\s*[—–-]\s*/u);if(!m)continue;const nome=normalizarEspacos(m[1]);if(/^[A-ZÀ-Ý][A-Za-zÀ-ÿ.' -]{2,100}$/u.test(nome))nomes.push(nome);}if(nomes.length&&(!novoAutor||/^opini[aã]o$/i.test(novoAutor))){novoAutor=nomes.join(' e ');blocos.shift();}}if(/^opini[aã]o$/i.test(novoAutor))novoAutor='';return{autor:novoAutor,texto:blocos.join('\n\n').trim()};}
function limparCorpoValor(texto='',url=''){const host=hostDaUrl(url);if(host!=='valor.globo.com'&&!host.endsWith('.valor.globo.com'))return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];for(let i=0;i<blocos.length;i++){const bloco=blocos[i];if(bloco.length>=45&&bloco.length<=220&&/[”"']\s*$/.test(bloco)){const comp=normalizarComparacao(bloco),duplicadoDepois=blocos.slice(i+1,i+12).some(outro=>outro.length>bloco.length+30&&normalizarComparacao(outro).includes(comp));if(duplicadoDepois)continue;}saida.push(bloco);}return saida.join('\n\n').trim();}
function limparCorpoOGlobo(texto='',url=''){const host=hostDaUrl(url);if(host!=='oglobo.globo.com'&&!host.endsWith('.oglobo.globo.com'))return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];for(let i=0;i<blocos.length;i++){const bloco=blocos[i];if(/^\*?\s*estagi[aá]ri[oa]\s+sob\s+supervis[aã]o\s+de\b/i.test(bloco))continue;if(i>=Math.max(0,blocos.length-4)&&/^jogo\s+pol[ií]tico$/i.test(bloco))break;saida.push(bloco);}return saida.join('\n\n').trim();}
function limparCorpoGazetaPovo(texto='',url=''){const host=hostDaUrl(url);if(host!=='www.gazetadopovo.com.br'&&host!=='gazetadopovo.com.br')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!(bloco.length<420&&/\(\s*foto\s*:\s*[^)]+\)\s*$/i.test(bloco))).join('\n\n').trim();}
function limparCorpoR7(texto='',url=''){const host=hostDaUrl(url);if(host!=='noticias.r7.com'&&!host.endsWith('.r7.com'))return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!/fique\s+por\s+dentro\s+das\s+principais\s+not[ií]cias.*whatsapp/i.test(bloco)&&!/siga\s+o\s+canal\s+do\s+r7.*whatsapp/i.test(bloco)&&!/^no\s+recordplus,?\s+tem\s+mais\s+conte[uú]do\s+da\s+record\b/i.test(bloco)&&!(/\bbaixe\s+o\s+app\s+aqui!?\s*$/i.test(bloco)&&/recordplus/i.test(bloco))).join('\n\n').trim();}
function normalizarAutorR7(autor='',url=''){const host=hostDaUrl(url);if(host!=='noticias.r7.com'&&!host.endsWith('.r7.com'))return autor;let a=normalizarEspacos(autor);if(!a)return'';a=a.replace(/\/\s*h[aá]\s+\d+\s+(?:hora|horas|minuto|minutos|dia|dias)\s*$/i,'').trim().replace(/^do\s+r7$/i,'R7').replace(/^r7\s*\/\s*h[aá].*$/i,'R7');return a;}
function limparCorpoDiarioPara(texto='',url=''){const host=hostDaUrl(url);if(host!=='diariodopara.com.br'&&host!=='www.diariodopara.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];for(const bloco of blocos){if(/^(?:rep[oó]rter|assuntos)$/i.test(bloco))break;saida.push(bloco);}return saida.join('\n\n').trim();}
function limparCorpoCNNBrasil(texto='',url=''){const host=hostDaUrl(url);if(host!=='www.cnnbrasil.com.br'&&host!=='cnnbrasil.com.br')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!/^os\s+textos\s+gerados\s+por\s+intelig[eê]ncia\s+artificial\s+na\s+cnn\s+brasil\b/i.test(bloco)).join('\n\n').trim();}
function limparCorpoGZH(texto='',url=''){if(hostDaUrl(url)!=='gauchazh.clicrbs.com.br')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!/^fique\s+informado\b.*\b(?:instagram|facebook|whatsapp)\b/i.test(bloco)&&!/\binscreva-se\s+no\s+canal\s+do\s+whatsapp\b/i.test(bloco)).join('\n\n').trim();}
function limparCorpoRevistaOeste(texto='',url=''){const host=hostDaUrl(url);if(host!=='revistaoeste.com'&&host!=='www.revistaoeste.com')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!/^\+$/u.test(bloco)&&!/^receba\s+nossas\s+atualiza[cç][oõ]es\b/i.test(bloco)&&!/^leia\s+tamb[eé]m\s*:/i.test(bloco)).join('\n\n').trim();}
function corrigirSubtituloTribunaNorte(subtitulo='',texto='',url=''){const host=hostDaUrl(url);if(host!=='tribunadonorte.com.br'&&host!=='www.tribunadonorte.com.br')return subtitulo;let s=limparSubtitulo(subtitulo);if(!s)return'';if(/\[…\]|\.\.\.|…/.test(s)){const semMarcador=s.replace(/\s*\[…\]\s*$/u,'').trim(),completas=semMarcador.match(/^(.+[.!?])(?:\s+[^.!?]*)?$/u);if(completas&&completas[1].length>=45)s=completas[1].trim();const primeiro=String(texto||'').split(/\n\n+/).map(normalizarEspacos).find(Boolean)||'';if(primeiro.length>=60&&primeiro.length<=520){const base=normalizarComparacao(s).slice(0,55),compPrimeiro=normalizarComparacao(primeiro);if(base&&compPrimeiro.startsWith(base.slice(0,Math.min(45,base.length))))s=primeiro;}}return s;}
function limparCorpoNSCTotal(texto='',url=''){const host=hostDaUrl(url);if(host!=='www.nsctotal.com.br'&&host!=='nsctotal.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];for(let i=0;i<blocos.length;i++){const bloco=blocos[i],prox=blocos[i+1]||'';if(i<3&&bloco.length<220&&!/[.!?][”"']?$/u.test(bloco)&&/^\d{2}\/\d{2}\/\d{4}\s+\d{1,2}:\d{2}$/.test(prox))continue;if(/^\d{2}\/\d{2}\/\d{4}\s+\d{1,2}:\d{2}$/.test(bloco))continue;if(/^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$/i.test(bloco))continue;if(/^continua\s+ap[oó]s\s+a\s+publicidade$/i.test(bloco))continue;if(/^veja\s+fotos\b/i.test(bloco))continue;if(/^\*?\s*sob\s+supervis[aã]o\s+de\b/i.test(bloco))continue;saida.push(bloco);}return saida.join('\n\n').trim();}
function limparCorpoBand(texto='',url=''){const host=hostDaUrl(url);if(host!=='www.band.com.br'&&host!=='band.com.br')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!/^compartilhar$/i.test(bloco)).join('\n\n').trim();}
function limparCorpoTerra(texto='',url=''){const host=hostDaUrl(url);if(host!=='www.terra.com.br'&&host!=='terra.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);return blocos.filter((bloco,i)=>!(i>=Math.max(0,blocos.length-3)&&/^por\s*:\s*.+\/\s*licenciado\s+de\b/i.test(bloco))).join('\n\n').trim();}
function limparCorpoNDMais(texto='',url=''){const host=hostDaUrl(url);if(host!=='ndmais.com.br'&&host!=='www.ndmais.com.br')return texto;const blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean),saida=[];for(let bloco of blocos){if(/^conte[uú]dos\s+em\s+alta$/i.test(bloco))continue;bloco=bloco.replace(/\s*Foto\s*:\s*[^.!?]{2,180}$/i,'').trim();if(bloco)saida.push(bloco);}return saida.join('\n\n').trim();}
function limparCorpoCorreioBraziliense(texto='',url=''){const host=hostDaUrl(url);if(host!=='www.correiobraziliense.com.br'&&host!=='correiobraziliense.com.br')return texto;const path=caminhoDaUrl(url);let blocos=String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean);if(path.includes('/cbradar/')){const primeiroCorpo=blocos.findIndex(b=>b.length>=180&&/[.!?][”"']?$/u.test(b));if(primeiroCorpo>=3&&primeiroCorpo<=8)blocos=blocos.slice(primeiroCorpo);const saida=[];let emRaioX=false;for(const bloco of blocos){if(/^raio[- ]x\s+da\s+nova\s+esquadra\s+da\s+marinha$/i.test(bloco)){emRaioX=true;continue;}if(emRaioX){if(/^o\s+momento\s+em\s+que\s+o\s+estaleiro\s+atinge\s+o\s+auge$/i.test(bloco)){emRaioX=false;saida.push(bloco);}continue;}if(/^ver\s+cronograma\s+das\s+pr[oó]ximas\s+fragatas$/i.test(bloco))continue;if(/^📋?\s*status\s+de\s+andamento\s+das\s+embarca[cç][oõ]es\s*:?$/iu.test(bloco))continue;if(/^[•·]\s*F200\b/i.test(bloco))continue;if(/^este\s+conte[uú]do\s+[eé]\s+informativo\b/i.test(bloco))continue;saida.push(bloco);}blocos=saida;}return blocos.join('\n\n').trim();}
function limparCorpoVeja(texto='',url=''){const host=hostDaUrl(url);if(host!=='veja.abril.com.br'&&host!=='www.veja.abril.com.br')return texto;return String(texto||'').split(/\n\n+/).map(normalizarEspacos).filter(Boolean).filter(bloco=>!/^continua\s+ap[oó]s\s+a\s+publicidade$/i.test(bloco)).join('\n\n').trim();}

function extrairAutorVisivelPorPortal(document,url=''){const host=hostDaUrl(url);if(host!=='gauchazh.clicrbs.com.br')return'';const candidatos=[textoMeta(document,['meta[name="parsely-author"]']),textoMeta(document,['meta[name="sailthru.author"]']),textoMeta(document,['meta[name="byl"]']),textoMeta(document,['meta[name="byline"]']),textoMeta(document,['meta[property="article:author"]'])];const seletores=['[rel="author"]','[itemprop="author"] [itemprop="name"]','[itemprop="author"]','a[href*="/colunistas/"]'];for(const seletor of seletores){const el=document.querySelector(seletor);if(el)candidatos.push(normalizarEspacos(el.textContent));}for(const candidato of candidatos.map(normalizarEspacos)){if(!candidato||candidato.length<3||candidato.length>120)continue;if(/^(?:GZH|Ga[uú]chaZH|Reda[cç][aã]o|Por)$/i.test(candidato))continue;if(/^[A-ZÀ-Ý][A-Za-zÀ-ÿ.' -]{2,119}$/u.test(candidato))return candidato;}return'';}
function normalizarUrlHistorico(url=''){try{const u=new URL(String(url||'').trim());u.hash='';if(u.pathname.length>1)u.pathname=u.pathname.replace(/\/+$/,'');return u.toString();}catch(_){return String(url||'').trim();}}
function historicoContemUrl(url='',arquivo='materias-extraidas.txt'){if(!EVITAR_URL_DUPLICADA_NO_HISTORICO||!fs.existsSync(arquivo))return false;const alvo=normalizarUrlHistorico(url);if(!alvo)return false;try{const linhas=fs.readFileSync(arquivo,'utf8').split(/\r?\n/);return linhas.some(linha=>/^https?:\/\//i.test(linha.trim())&&normalizarUrlHistorico(linha.trim())===alvo);}catch(_){return false;}}
function aplicarLimpezasPorPortal(texto='',url='',metadados={}){let t=String(texto||'');t=limparCorpoGloboNoticias(t,url,metadados.titulo||'');t=limparCorpoSBT(t,url);t=limparCorpoEstadoMinas(t,url);t=limparCorpoPoder360(t,url);t=limparCorpoIstoe(t,url);t=limparCorpoOLiberal(t,url);t=limparCorpoMetropoles(t,url);t=limparCorpoValor(t,url);t=limparCorpoOGlobo(t,url);t=limparCorpoGazetaPovo(t,url);t=limparCorpoR7(t,url);t=limparCorpoDiarioPara(t,url);t=limparCorpoCNNBrasil(t,url);t=limparCorpoGZH(t,url);t=limparCorpoRevistaOeste(t,url);t=limparCorpoNSCTotal(t,url);t=limparCorpoBand(t,url);t=limparCorpoTerra(t,url);t=limparCorpoNDMais(t,url);t=limparCorpoCorreioBraziliense(t,url);t=limparCorpoVeja(t,url);return t.trim();}

function textoMeta(document,seletores){for(const seletor of seletores){const el=document.querySelector(seletor),valor=el?.getAttribute('content')||el?.textContent||'';if(textoLimpoHtml(valor))return textoLimpoHtml(valor);}return'';}
function coletarObjetosJsonLd(valor,saida=[]){if(!valor)return saida;if(Array.isArray(valor)){for(const item of valor)coletarObjetosJsonLd(item,saida);return saida;}if(typeof valor==='object'){saida.push(valor);if(valor['@graph'])coletarObjetosJsonLd(valor['@graph'],saida);}return saida;}
function lerJsonLd(document){const objetos=[];for(const script of document.querySelectorAll('script[type="application/ld+json"]')){try{const parsed=JSON.parse(script.textContent);coletarObjetosJsonLd(parsed,objetos);}catch(_){}}return objetos;}
function tiposDoObjeto(obj){const tipo=obj?.['@type'];return(Array.isArray(tipo)?tipo:[tipo]).filter(Boolean).map(v=>String(v).toLowerCase());}
function escolherJsonLdArtigo(objetos){const tiposArtigo=new Set(['article','newsarticle','reportagenewsarticle','blogposting','analysisnewsarticle','opinionnewsarticle']);return objetos.find(obj=>tiposDoObjeto(obj).some(t=>tiposArtigo.has(t)))||{};}
function nomeAutor(valor){if(!valor)return'';if(typeof valor==='string')return textoLimpoHtml(valor);if(Array.isArray(valor))return valor.map(nomeAutor).filter(Boolean).join(', ');if(typeof valor==='object')return textoLimpoHtml(valor.name||valor.alternateName||'');return'';}
function nomeVeiculo(valor){if(!valor)return'';if(typeof valor==='string')return textoLimpoHtml(valor);if(typeof valor==='object')return textoLimpoHtml(valor.name||'');return'';}
function formatarData(valor){if(!valor)return'';const texto=String(valor).trim(),iso=texto.match(/^(\d{4})-(\d{2})-(\d{2})/);if(iso)return`${iso[3]}/${iso[2]}/${iso[1]}`;const br=texto.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/);if(br)return`${br[1].padStart(2,'0')}/${br[2].padStart(2,'0')}/${br[3]}`;const pontuada=texto.match(/\b(\d{1,2})[.](\d{1,2})[.](\d{2}|\d{4})\b/);if(pontuada){let ano=pontuada[3];if(ano.length===2)ano=String(2000+Number(ano));return`${pontuada[1].padStart(2,'0')}/${pontuada[2].padStart(2,'0')}/${ano}`;}const data=new Date(texto);if(!Number.isNaN(data.getTime()))return new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',year:'numeric'}).format(data);return normalizarEspacos(texto);}

function removerElementosObvios(document){const seletores=['script','style','noscript','template','nav','footer','aside','form','button','iframe','figure','figcaption','picture','img','video','audio','svg','[role="navigation"]','[role="complementary"]','[class*="advert"]','[id*="advert"]','[class*="publicidade"]','[id*="publicidade"]','[class*="banner"]','[class*="newsletter"]','[class*="social-share"]','[class*="share-buttons"]','[class*="related-post"]','[class*="related_post"]','[class*="recommended"]','[class*="recomendad"]','[class*="mais-lid"]','[class*="most-read"]','[class*="breadcrumb"]','[class*="comments"]','[id*="comments"]'];for(const seletor of seletores){try{document.querySelectorAll(seletor).forEach(el=>el.remove());}catch(_){}}}
function densidadeLinks(el){const total=normalizarEspacos(el.textContent).length;if(!total)return 0;let links=0;el.querySelectorAll('a').forEach(a=>{links+=normalizarEspacos(a.textContent).length;});return links/total;}

function ehLinhaLixo(texto){const comp=normalizarComparacao(texto);if(!comp)return true;if(CABECALHOS_LIXO.includes(comp))return true;if(PREFIXOS_LIXO.some(p=>comp.startsWith(p)))return true;const linha=normalizarEspacos(texto);if(ehMetadadoPoder360(linha)||ehMetadadoPublicacaoODia(linha))return true;if(/^\d{1,2}:\d{2}(?::\d{2})?$/.test(linha))return true;if(/^(?:\d+(?:[.,]\d+)?x\s*){2,}$/i.test(linha))return true;if(/^(?:velocidade|reproduzir|pausar|ouvir|ouça|áudio|audio)$/i.test(linha))return true;if(/^vídeos?\s+em\s+alta\s+no\s+g1$/i.test(linha)||/^videos?\s+em\s+alta\s+no\s+g1$/i.test(linha))return true;if(/^vídeos?\s*:\s*as\s+notícias\s+que\s+foram\s+ao\s+ar\b/i.test(linha)||/^videos?\s*:\s*as\s+noticias\s+que\s+foram\s+ao\s+ar\b/i.test(linha))return true;if(/^vídeos?\s*:\s*mais\s+vistos\s+do\s+g1\b/i.test(linha)||/^videos?\s*:\s*mais\s+vistos\s+do\s+g1\b/i.test(linha))return true;if(texto.length<140&&/\b(divulgação|reprodução|arquivo pessoal|acervo)\b/i.test(texto))return true;if(ehLegendaCreditoODia(linha))return true;if(texto.length<180&&/\/[A-Z0-9.-]{2,20}\s*[-–—]\s*\d{1,2}[.\/-][a-zç]{3,9}[.\/-]\d{2,4}\b/i.test(texto))return true;if(/^assista\s+(?:à|a|ao|aos|às)\s+(?:vídeo|video|cerimônia|cerimonia|íntegra|integra|transmissão|transmissao)\b/i.test(linha))return true;if(/^assista\s+(?:ao\s+vivo|agora|abaixo)\b/i.test(linha))return true;if(/^(?:veja|confira)\s+(?:o|a)\s+vídeo\b/i.test(linha))return true;if(/^(?:confira|veja|assista)\b.*\b(?:no|o)\s+vídeo\s+abaixo\b/i.test(linha))return true;if(/\b(?:pic\.twitter\.com|twitter\.com\/[^\s]+\/status|x\.com\/[^\s]+\/status)\b/i.test(linha))return true;if(/^©?\s*\d{4}\s+.+todos os direitos reservados\.?$/i.test(linha)||/^todos os direitos reservados\.?$/i.test(linha))return true;if(ehLegendaFotoGlobo(linha))return true;if(/receba\s+(?:as\s+)?(?:principais\s+)?not[ií]cias.*whatsapp/i.test(linha))return true;return false;}

function limparChamadasInline(texto=''){let limpo=normalizarEspacos(texto);if(!limpo)return'';limpo=limpo.replace(/\s*\((?:assista|veja|confira)\b[^)]{0,140}\b(?:topo|acima|abaixo)\b[^)]*\)/gi,'').trim();const chamadas=[/\s+(?:veja|leia|confira|saiba)\s+(?:aqui|mais)\b[^.!?]*(?:[.!?]+)?\s*$/i,/\s+(?:clique|acesse)\s+aqui\b[^.!?]*(?:[.!?]+)?\s*$/i,/\s+continue\s+lendo\b[^.!?]*(?:[.!?]+)?\s*$/i];let anterior;do{anterior=limpo;for(const re of chamadas)limpo=limpo.replace(re,'').trim();}while(limpo!==anterior);return limpo;}

function extrairBlocosLimpos(htmlArtigo,metadados,url=''){
  const dom=new JSDOM(`<main id="artigo">${htmlArtigo||''}</main>`),document=dom.window.document;removerElementosObvios(document);const raiz=document.querySelector('#artigo'),candidatos=[...raiz.querySelectorAll('p, blockquote, h2, h3, li')],resultado=[];let ignorandoRelacionados=false,corpoIniciado=false;const ignorarIndicesIniciais=new Set(),limiteInspecao=Math.min(candidatos.length,8);
  for(let i=0;i<limiteInspecao;i++){const atual=limparChamadasInline(candidatos[i].textContent);if(!atual)continue;if(atual.length<380&&/\b(?:crédito|credito)\s*:/i.test(atual)){ignorarIndicesIniciais.add(i);if(i>0){const anterior=limparChamadasInline(candidatos[i-1].textContent);if(anterior&&anterior.length<220)ignorarIndicesIniciais.add(i-1);}}}
  const metaComparar=new Set([metadados.titulo,metadados.subtitulo,metadados.autor,metadados.data,`Por: ${metadados.autor}`,`Por ${metadados.autor}`].filter(Boolean).map(normalizarComparacao));
  for(let indice=0;indice<candidatos.length;indice++){const el=candidatos[indice];if(!corpoIniciado&&ignorarIndicesIniciais.has(indice))continue;let texto=limparChamadasInline(el.textContent);if(!texto)continue;const comp=normalizarComparacao(texto),tag=el.tagName.toLowerCase(),linkDensity=densidadeLinks(el);if(!corpoIniciado){if(texto.length<320&&/\b(?:crédito|credito)\s*:/i.test(texto))continue;const primeiroParagrafoReal=(tag==='p'||tag==='blockquote')&&texto.length>=80&&linkDensity<0.45;if(!primeiroParagrafoReal)continue;corpoIniciado=true;}if(CABECALHOS_LIXO.includes(comp)){ignorandoRelacionados=true;continue;}if(ignorandoRelacionados){const paragrafoReal=(tag==='p'||tag==='blockquote')&&texto.length>=100&&linkDensity<0.45;if(!paragrafoReal)continue;ignorandoRelacionados=false;}if(ehLinhaLixo(texto)||ehChamadaRelacionadaOGloboBlog(texto,url))continue;if(texto.length<180&&/^\*?\s*com informações\s+(?:da|do|de)\b/i.test(texto))continue;if(metaComparar.has(comp))continue;if(linkDensity>0.70&&texto.length<260)continue;if(tag==='li'&&texto.length<90&&linkDensity>0.30)continue;if(resultado[resultado.length-1]!==texto)resultado.push(texto);}
  return resultado.join('\n\n').trim();
}

function palavrasSignificativas(texto=''){const stopwords=new Set(['a','o','os','as','de','da','do','das','dos','e','em','no','na','nos','nas','um','uma','uns','umas','para','por','com','sem','que','se','ao','aos','é','foi','são','ser','como','mais','menos','muito','sua','seu','suas','seus','esta','este','essa','esse','isso','após','antes','entre','sobre','até','também','já','ainda','mas','ou','quando','onde','quem','qual','quais','pelo','pela','pelos','pelas']);return normalizarEspacos(texto).toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').match(/[a-z0-9]+/g)?.filter(p=>p.length>=4&&!stopwords.has(p))||[];}
function pareceResumoEditorialInicial(primeiro,seguintes){if(!primeiro||!seguintes?.length)return false;if(primeiro.length<300||primeiro.length>900)return false;const frases=(primeiro.match(/[.!?](?:\s|$)/g)||[]).length;if(frases<3)return false;const palavrasPrimeiro=new Set(palavrasSignificativas(primeiro));if(palavrasPrimeiro.size<20)return false;const palavrasSeguintes=new Set(palavrasSignificativas(seguintes.slice(0,5).join(' ')));let repetidas=0;for(const palavra of palavrasPrimeiro)if(palavrasSeguintes.has(palavra))repetidas++;return repetidas/palavrasPrimeiro.size>=0.28;}
function removerResumoEditorialInicial(texto='',url=''){let host='';try{host=new URL(url).hostname.toLowerCase();}catch(_){}if(!host.includes('estadao.com.br'))return texto;const blocos=String(texto).split(/\n\n+/).map(normalizarEspacos).filter(Boolean);if(blocos.length<3)return texto;if(pareceResumoEditorialInicial(blocos[0],blocos.slice(1)))blocos.shift();return blocos.join('\n\n').trim();}
function limparAutor(autor){const limpo=normalizarEspacos(autor).replace(/^por\s*:\s*/i,'').replace(/^por\s+/i,'').replace(/^[—–-]\s*/,'').replace(/\s+-\s*$/,'').trim();if(!limpo||/^(?:null|undefined)$/i.test(limpo))return'';if(/^(?:https?:\/\/)?(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+){1,}(?:\/[^\s]*)?$/i.test(limpo))return'';return limpo;}
function limparTitulo(titulo,veiculo){let t=normalizarEspacos(titulo);if(veiculo){const escaped=veiculo.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');t=t.replace(new RegExp(`\\s*[|–—-]\\s*${escaped}\\s*$`,'i'),'').trim();}return t;}
function limparSubtitulo(subtitulo){let texto=normalizarEspacos(subtitulo);if(!texto)return'';const sufixos=[/\s*(?:[-–—|:]\s*)?(?:veja|confira|saiba|leia)\s+(?:aqui|mais)(?:\s*[!.?]+)?\s*$/i,/\s*(?:[-–—|:]\s*)?(?:clique|acesse)\s+aqui(?:\s*[!.?]+)?\s*$/i,/\s*(?:[-–—|:]\s*)?continue\s+lendo(?:\s*[!.?]+)?\s*$/i,/\s+leia\s+na\s+gazeta\s+do\s+povo(?:\s*[!.?]+)?\s*$/i];let anterior;do{anterior=texto;for(const re of sufixos)texto=texto.replace(re,'').trim();}while(texto!==anterior);return texto;}

async function extrairMateria(url){
  const configProxy=carregarConfigProxy(),timeoutMs=Math.max(5000,Number(configProxy.TIMEOUT_MS)||45000);let resposta;
  try{resposta=await fetchComRetry(url,{redirect:'follow',headers:{'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36','Accept-Language':'pt-BR,pt;q=0.9,en;q=0.8','Accept':'text/html,application/xhtml+xml','Connection':'close'}},{timeoutMs,tentativas:3});}catch(erro){throw new Error(mensagemErroRede(erro));}
  if(!resposta.ok)throw new Error(`HTTP ${resposta.status} ao acessar a página.`);const contentType=resposta.headers.get('content-type')||'';if(!contentType.includes('text/html'))throw new Error(`O link não retornou uma página HTML (${contentType||'tipo desconhecido'}).`);
  const html=await resposta.text(),dom=new JSDOM(html,{url}),document=dom.window.document,objetosLd=lerJsonLd(document),artigoLd=escolherJsonLdArtigo(objetosLd);
  let veiculo=textoMeta(document,['meta[property="og:site_name"]','meta[name="application-name"]'])||nomeVeiculo(artigoLd.publisher)||'';veiculo=textoLimpoHtml(veiculo);if(!veiculo){const host=new URL(url).hostname.replace(/^www\./,'');veiculo=host.split('.')[0];veiculo=veiculo.charAt(0).toUpperCase()+veiculo.slice(1);}veiculo=normalizarVeiculo(veiculo,url);
  const documentParaLeitura=document.cloneNode(true);removerElementosObvios(documentParaLeitura);const artigo=new Readability(documentParaLeitura).parse();if(!artigo)throw new Error('Não foi possível identificar o corpo principal da matéria.');
  const tituloCandidatos=[artigoLd.headline,textoMeta(document,['meta[property="og:title"]']),textoMeta(document,['meta[name="twitter:title"]']),textoMeta(document,['meta[name="parsely-title"]']),textoMeta(document,['meta[name="sailthru.title"]']),textoMeta(document,['meta[name="headline"]']),textoMeta(document,['meta[itemprop="headline"]']),document.querySelector('h1')?.textContent,document.querySelector('[itemprop="headline"]')?.textContent,artigo.title,document.title];let titulo=escolherMelhorTitulo(tituloCandidatos,veiculo);
  try{const hostAtual=new URL(url).hostname.toLowerCase();if(hostAtual==='odia.ig.com.br'||hostAtual.endsWith('.odia.ig.com.br'))titulo=titulo.replace(/\s*\|\s*[^|]{2,120}$/u,'').trim();}catch(_){}titulo=limparTituloPorPortal(titulo,url);
  let subtitulo=textoLimpoHtml(artigoLd.description)||textoMeta(document,['meta[property="og:description"]','meta[name="description"]','meta[name="twitter:description"]','meta[name="parsely-description"]','meta[name="sailthru.description"]','meta[itemprop="description"]'])||textoLimpoHtml(artigo.excerpt);const subtituloVisivel=extrairSubtituloVisivel(document,url);subtitulo=escolherTextoMaisCompleto(subtitulo,subtituloVisivel);
  try{const hostAtual=new URL(url).hostname.toLowerCase();if(hostAtual==='odia.ig.com.br'||hostAtual.endsWith('.odia.ig.com.br')){const subtituloH2Robusto=extrairSubtituloODiaRobusto(document,html,titulo);if(subtituloH2Robusto)subtitulo=subtituloH2Robusto;else{const subtituloH2Exato=extrairSubtituloODiaPeloTitulo(document,titulo);if(subtituloH2Exato)subtitulo=subtituloH2Exato;else{const subtituloODia=extrairSubtituloODia(document,titulo);if(subtituloODia)subtitulo=escolherTextoMaisCompleto(subtitulo,subtituloODia);}}}}catch(_){}
  try{const hostAtual=new URL(url).hostname.toLowerCase();if((hostAtual==='odia.ig.com.br'||hostAtual.endsWith('.odia.ig.com.br'))&&!textoLimpoHtml(subtitulo)){const cabecalhoAmp=await extrairCabecalhoAmpODia(url,timeoutMs,document);if(cabecalhoAmp.titulo){const tituloAmpLimpo=limparTitulo(cabecalhoAmp.titulo,veiculo).replace(/\s*\|\s*[^|]{2,120}$/u,'').trim();if(tituloAmpLimpo&&!pareceTruncado(tituloAmpLimpo))titulo=tituloAmpLimpo;}if(cabecalhoAmp.subtitulo)subtitulo=cabecalhoAmp.subtitulo;}}catch(_){}
  subtitulo=limparSubtitulo(subtitulo);if(normalizarComparacao(subtitulo)===normalizarComparacao(titulo))subtitulo='';
  let autor=nomeAutor(artigoLd.author)||textoMeta(document,['meta[name="author"]','meta[property="article:author"]'])||textoLimpoHtml(artigo.byline);autor=limparAutor(autor);if(!autor)autor=limparAutor(extrairAutorVisivelPorPortal(document,url));autor=normalizarAutorR7(autor,url);
  const dataBruta=artigoLd.datePublished||textoMeta(document,['meta[property="article:published_time"]','meta[name="date"]','meta[name="publish-date"]','time[datetime]']),data=formatarData(dataBruta)||'Data não identificada',metadados={titulo,subtitulo,autor,data};
  let texto=extrairBlocosLimpos(artigo.content,metadados,url);if(texto.length<180){texto=String(artigo.textContent||'').split(/\n+/).map(limparChamadasInline).filter(Boolean).filter(linha=>!ehLinhaLixo(linha)).filter(linha=>!(linha.length<180&&/^\*?\s*com informações\s+(?:da|do|de)\b/i.test(linha))).filter(linha=>!metadados||!new Set([titulo,subtitulo,autor,data].filter(Boolean).map(normalizarComparacao)).has(normalizarComparacao(linha))).join('\n\n');}
  if(hostDaUrl(url).endsWith('atribuna.com.br')&&(texto.length<220||pareceNavegacaoATribuna(texto))){const alternativoATribuna=extrairCorpoAlternativoATribuna(document,artigoLd,metadados,url);if(alternativoATribuna&&alternativoATribuna.length>texto.length)texto=alternativoATribuna;}
  texto=removerResumoEditorialInicial(texto,url);texto=limparCorpoODia(texto,url);texto=aplicarLimpezasPorPortal(texto,url,metadados);const ajusteDW=corrigirUolDeutscheWelle(titulo,subtitulo,texto,url);subtitulo=ajusteDW.subtitulo;texto=ajusteDW.texto;const ajusteConfere=corrigirUolConfere(subtitulo,texto,url);subtitulo=ajusteConfere.subtitulo;texto=ajusteConfere.texto;subtitulo=corrigirSubtituloTribunaNorte(subtitulo,texto,url);const ajusteCB=ajustarCorreioBraziliense(autor,texto,url);autor=ajusteCB.autor;texto=ajusteCB.texto;subtitulo=corrigirSubtituloTruncadoComCorpo(subtitulo,autor,texto);metadados.subtitulo=subtitulo;metadados.autor=autor;if(!texto)throw new Error('O conteúdo principal foi identificado, mas nenhum texto útil restou após a limpeza.');
  const partes=[url,'',veiculo,'',`*${titulo||'Título não identificado'}*`];if(subtitulo)partes.push('',`_${subtitulo}_`);partes.push('');if(autor)partes.push(autor);partes.push(data,'',texto);const resultado=partes.join('\n').replace(/\n{3,}/g,'\n\n').trim()+'\n';return{url,veiculo,titulo,subtitulo,autor,data,texto,resultado};
}

function copiarParaAreaTransferencia(texto=''){const conteudo=String(texto||'');if(!conteudo)return{sucesso:false,motivo:'Texto vazio'};if(process.platform==='win32'){const arquivoClipboard=path.resolve('.clipboard-extrator-utf8.tmp');try{fs.writeFileSync(arquivoClipboard,conteudo,{encoding:'utf8'});const caminhoPs=arquivoClipboard.replace(/'/g,"''"),comandoPs=`Get-Content -LiteralPath '${caminhoPs}' -Raw -Encoding UTF8 | Set-Clipboard`;const ps=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',comandoPs],{encoding:'utf8',windowsHide:true,timeout:15000});if(!ps.error&&ps.status===0)return{sucesso:true,metodo:'PowerShell UTF-8'};const tentativaClip=spawnSync('clip.exe',[],{input:Buffer.from(conteudo,'utf16le'),windowsHide:true,timeout:15000});if(!tentativaClip.error&&tentativaClip.status===0)return{sucesso:true,metodo:'clip.exe UTF-16LE'};return{sucesso:false,motivo:ps.error?.message||tentativaClip.error?.message||String(ps.stderr||'').trim()||'Falha ao acessar a área de transferência.'};}catch(erro){return{sucesso:false,motivo:erro.message};}finally{try{if(fs.existsSync(arquivoClipboard))fs.unlinkSync(arquivoClipboard);}catch(_){}}}return{sucesso:false,motivo:'Cópia automática configurada para Windows.'};}
async function perguntar(rl,mensagem){return new Promise(resolve=>rl.question(mensagem,resolve));}
async function perguntarLinhaUnica(mensagem){const rl=readline.createInterface({input:process.stdin,output:process.stdout});try{return await perguntar(rl,mensagem);}finally{rl.close();}}
async function perguntarSenhaOculta(mensagem='Senha do proxy: '){if(!process.stdin.isTTY||typeof process.stdin.setRawMode!=='function')return await perguntarLinhaUnica(mensagem);return new Promise((resolve,reject)=>{const stdin=process.stdin,stdout=process.stdout;let senha='';const rawAnterior=Boolean(stdin.isRaw),encodingAnterior=stdin.readableEncoding;const limpar=()=>{stdin.removeListener('data',aoDigitar);try{stdin.setRawMode(rawAnterior);}catch(_){}try{if(encodingAnterior)stdin.setEncoding(encodingAnterior);}catch(_){}stdout.write('\n');};const aoDigitar=chunk=>{const texto=String(chunk);for(const ch of texto){if(ch==='\r'||ch==='\n'){limpar();resolve(senha);return;}if(ch==='\u0003'){limpar();reject(new Error('Entrada cancelada pelo usuário.'));return;}if(ch==='\u0008'||ch==='\u007f'){if(senha.length>0){senha=senha.slice(0,-1);stdout.write('\b \b');}continue;}if(ch==='\u001b')continue;if(ch>=' '){senha+=ch;stdout.write('*');}}};try{stdout.write(mensagem);stdin.setEncoding('utf8');stdin.setRawMode(true);stdin.resume();stdin.on('data',aoDigitar);}catch(erro){limpar();reject(erro);}});}
async function perguntarSimNao(mensagem='Usar proxy? (S/N): '){while(true){const resposta=normalizarEspacos(await perguntarLinhaUnica(mensagem)).toLowerCase();if(/^(?:s|sim|y|yes)$/.test(resposta))return true;if(/^(?:n|nao|não|no)$/.test(resposta))return false;console.log('Digite S para usar proxy ou N para conexão direta.');}}

async function main(){let configProxy;try{configProxy=carregarConfigProxy();}catch(erro){console.error(`ERRO DE CONFIGURAÇÃO: ${erro.message}`);return;}console.log(`Extrator de Matérias - ${VERSAO}`);console.log('Esta mesma versão funciona em computador com ou sem proxy.\n');let usarProxy=false;try{usarProxy=await perguntarSimNao('Usar proxy? (S/N): ');}catch(erro){console.error(`ERRO AO LER OPÇÃO DE CONEXÃO: ${erro.message}`);return;}if(usarProxy){const servidor=String(configProxy.SERVIDOR||'').trim(),porta=String(configProxy.PORTA||'').trim();if(!servidor||!porta){console.error('ERRO DE CONFIGURAÇÃO: servidor/porta do proxy não estão preenchidos em config-proxy.json.');return;}console.log(`Proxy configurado: ${servidor}:${porta}`);console.log('As credenciais serão usadas somente nesta execução e não serão salvas.\n');try{const usuario=(await perguntarLinhaUnica('Usuário do proxy: ')).trim(),senha=await perguntarSenhaOculta('Senha do proxy: ');prepararProxy(usuario,senha,{...configProxy,ATIVADO:true});console.log('\n✓ Credenciais carregadas para esta sessão.');}catch(erro){console.error(`ERRO DE AUTENTICAÇÃO/CONFIGURAÇÃO: ${erro.message}`);return;}}else{prepararProxy('','',{...configProxy,ATIVADO:false});console.log('✓ Conexão direta selecionada.');}const rl=readline.createInterface({input:process.stdin,output:process.stdout}),versaoUndici=obterVersaoUndici();console.log(`Node: ${process.version} | Undici: ${versaoUndici}`);if(/^8\./.test(versaoUndici))console.log('AVISO: Undici 8.x detectado. Para maior compatibilidade com proxy corporativo, execute novamente o INSTALAR_EXTRATOR_V1.25.1.bat.');console.log(`Conexão: ${PROXY_STATUS.ativo?'PROXY ATIVO':'DIRETA'}`);if(PROXY_STATUS.ativo)console.log(`Proxy: ${PROXY_STATUS.descricao}`);console.log('O programa ficará aberto para vários links.');console.log('Digite SAIR quando quiser encerrar.\n');try{while(true){const entrada=await perguntar(rl,'Cole o link da matéria: '),url=entrada.trim();if(!url){console.log('Nenhum link informado.\n');continue;}if(/^(?:sair|exit|fechar)$/i.test(url)){console.log('\nExtrator encerrado.');break;}try{if(!/^https?:\/\//i.test(url))throw new Error('Cole um link começando com http:// ou https://');console.log('\nLendo e limpando a matéria...\n');const materia=await extrairMateria(url);console.log('='.repeat(70));console.log(materia.resultado);console.log('='.repeat(70));fs.writeFileSync('materia-extraida.txt',materia.resultado,'utf8');const separador='\n'+'#'.repeat(70)+'\n\n',repetidaNoHistorico=historicoContemUrl(materia.url,'materias-extraidas.txt');if(!repetidaNoHistorico)fs.appendFileSync('materias-extraidas.txt',materia.resultado+separador,'utf8');const copia=copiarParaAreaTransferencia(materia.resultado);console.log('\n✓ Matéria extraída com sucesso');console.log('✓ Arquivo atualizado: materia-extraida.txt');console.log(repetidaNoHistorico?'✓ URL já existia no histórico: não foi duplicada em materias-extraidas.txt':'✓ Histórico acumulado: materias-extraidas.txt');if(copia.sucesso)console.log(`✓ Texto copiado para a área de transferência (${copia.metodo||'UTF-8'})`);else{console.log(`! Não foi possível copiar automaticamente: ${copia.motivo}`);console.log('  O arquivo materia-extraida.txt continua disponível normalmente.');}console.log('\nCole o próximo link ou digite SAIR.\n');}catch(erro){console.error(`\nERRO: ${erro.message}`);console.log('O programa continuará aberto. Tente outro link ou digite SAIR.\n');}}}finally{rl.close();}}

if(require.main===module)main();
module.exports={extrairMateria,extrairBlocosLimpos,ehLinhaLixo,limparAutor,limparSubtitulo,limparChamadasInline,copiarParaAreaTransferencia,carregarConfigProxy,prepararProxy,perguntarSenhaOculta,mensagemErroRede,fetchComRetry,ehErroRedeTransitorio,detalhesErroRede,renovarAgenteProxy,decodificarEntidadesHtml,extrairSubtituloVisivel,escolherTextoMaisCompleto,escolherMelhorTitulo,corrigirSubtituloTruncadoComCorpo,normalizarVeiculo,ehMetadadoPoder360,ehChamadaRelacionadaOGloboBlog,pareceTruncado,montarUrlAmpODia,obterUrlAmpDeclaradaODia,extrairCabecalhoAmpODia,ehMetadadoPublicacaoODia,ehLegendaCreditoODia,limparCorpoODia,perguntarSimNao,limparTituloPorPortal,limparCorpoGloboNoticias,limparCorpoSBT,limparCorpoEstadoMinas,limparCorpoPoder360,limparCorpoIstoe,limparCorpoR7,normalizarAutorR7,corrigirUolDeutscheWelle,corrigirUolConfere,corrigirSubtituloTribunaNorte,ajustarCorreioBraziliense,aplicarLimpezasPorPortal,pareceNavegacaoATribuna,formatarData,historicoContemUrl,normalizarUrlHistorico,extrairAutorVisivelPorPortal,obterVersaoUndici,VERSAO};
