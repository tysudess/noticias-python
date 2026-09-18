const url = document.getElementById('url');
const btnExtrair = document.getElementById('extrair');
const btnUltimo = document.getElementById('ultimo');
const btnHistorico = document.getElementById('historico');
const btnPasta = document.getElementById('pasta');
const btnLimpar = document.getElementById('limpar');
const btnCopiar = document.getElementById('copiar');
const status = document.getElementById('status');
const statusPill = document.getElementById('statusPill');
const resultado = document.getElementById('resultado');
const resultadoVazio = document.getElementById('resultadoVazio');
const info = document.getElementById('info');
const versao = document.getElementById('versao');
const versaoSidebar = document.getElementById('versaoSidebar');
const usarProxy = document.getElementById('usarProxy');
const camposProxy = document.getElementById('camposProxy');
const usuario = document.getElementById('usuario');
const senha = document.getElementById('senha');
const successMark = document.getElementById('successMark');

const revisarRigido = document.getElementById('revisarRigido');
const revisaoRigidaStatus = document.getElementById('revisaoRigidaStatus');
const revisaoRigidaLista = document.getElementById('revisaoRigidaLista');

const assinanteUsuario = document.getElementById('assinanteUsuario');
const assinanteSenha = document.getElementById('assinanteSenha');
const assinanteStatus = document.getElementById('assinanteStatus');
const salvarAssinante = document.getElementById('salvarAssinante');
const apagarAssinante = document.getElementById('apagarAssinante');
const PROVEDOR_ASSINANTE = 'valorGlobo';

const metaTitulo = document.getElementById('metaTitulo');
const metaVeiculo = document.getElementById('metaVeiculo');
const metaData = document.getElementById('metaData');
const metaAutor = document.getElementById('metaAutor');
const metaSubtitulo = document.getElementById('metaSubtitulo');
const metaLink = document.getElementById('metaLink');

let extraindo = false;
let assinanteSenhaSalva = false;
let revisandoRigido = false;
let revisaoRigidaIssues = [];
let revisaoRigidaTimer = null;

function urlInformadaValida() {
  return /^https?:\/\/\S+/i.test(url.value.trim());
}

function sincronizarBotaoExtrair() {
  btnExtrair.disabled = extraindo || !urlInformadaValida();
}

function classificarStatus(mensagem = '') {
  const t = String(mensagem).toLowerCase();
  if (/erro|não foi|nao foi|precisa|informe|cole o link|já existe|ja existe/.test(t)) return 'error';
  if (/^✓|salva|concluída|concluida|extraída|extraida/.test(t)) return 'success';
  if (/lendo|limpando|process|salvando|conexão|conexao/.test(t)) return 'busy';
  return 'ready';
}

function definirStatus(mensagem, estado) {
  status.textContent = mensagem;
  statusPill.dataset.state = estado || classificarStatus(mensagem);
}

window.extratorAPI.onStatus((mensagem) => definirStatus(mensagem));

usarProxy.addEventListener('change', () => {
  camposProxy.classList.toggle('oculto', !usarProxy.checked);
  if (usarProxy.checked) usuario.focus();
});

async function carregarAcessoAssinante() {
  if (!assinanteUsuario || !assinanteSenha || !assinanteStatus) return;

  try {
    const r = await window.extratorAPI.obterCredenciaisAssinante(PROVEDOR_ASSINANTE);
    if (!r.ok) {
      assinanteSenhaSalva = false;
      assinanteStatus.textContent = r.erro || 'Não foi possível consultar o acesso salvo.';
      apagarAssinante.disabled = true;
      return;
    }

    assinanteSenhaSalva = !!(r.salvo && r.temSenha);
    assinanteUsuario.value = r.usuario || '';
    assinanteSenha.value = '';

    if (assinanteSenhaSalva) {
      assinanteSenha.placeholder = 'Senha já salva com segurança';
      assinanteStatus.textContent = '✓ Acesso Valor / Globo salvo neste computador. Não é necessário digitar a senha novamente.';
      apagarAssinante.disabled = false;
    } else {
      assinanteSenha.placeholder = 'Digite uma vez para salvar';
      assinanteStatus.textContent = 'Nenhum acesso de assinante salvo neste computador.';
      apagarAssinante.disabled = true;
    }
  } catch (e) {
    assinanteSenhaSalva = false;
    assinanteStatus.textContent = 'Falha ao consultar o acesso salvo: ' + (e?.message || e);
    apagarAssinante.disabled = true;
  }
}

async function salvarAcessoAssinante() {
  const usuarioAssinante = assinanteUsuario.value.trim();
  const senhaNova = assinanteSenha.value;

  if (!usuarioAssinante) {
    assinanteStatus.textContent = 'Informe o usuário/e-mail da assinatura.';
    assinanteUsuario.focus();
    return;
  }
  if (!senhaNova && !assinanteSenhaSalva) {
    assinanteStatus.textContent = 'Informe a senha da assinatura na primeira vez.';
    assinanteSenha.focus();
    return;
  }

  salvarAssinante.disabled = true;
  assinanteStatus.textContent = 'Salvando acesso com proteção do Windows…';
  try {
    const r = await window.extratorAPI.salvarCredenciaisAssinante(PROVEDOR_ASSINANTE, {
      usuario: usuarioAssinante,
      senha: senhaNova
    });

    if (!r.ok) {
      assinanteStatus.textContent = r.erro || 'Não foi possível salvar o acesso.';
      definirStatus('Não foi possível salvar o acesso de assinante.', 'error');
      return;
    }

    assinanteSenhaSalva = true;
    assinanteUsuario.value = r.usuario || usuarioAssinante;
    assinanteSenha.value = '';
    assinanteSenha.placeholder = 'Senha já salva com segurança';
    assinanteStatus.textContent = '✓ Acesso Valor / Globo salvo neste computador. Nas próximas aberturas ele continuará cadastrado.';
    apagarAssinante.disabled = false;
    definirStatus('✓ Acesso de assinante salvo com proteção local do Windows.', 'success');
  } catch (e) {
    assinanteStatus.textContent = 'Erro ao salvar acesso: ' + (e?.message || e);
    definirStatus('Erro ao salvar o acesso de assinante.', 'error');
  } finally {
    salvarAssinante.disabled = false;
  }
}

async function apagarAcessoAssinante() {
  if (!assinanteSenhaSalva) return;
  const confirmar = window.confirm('Apagar o acesso Valor / Globo salvo neste computador?');
  if (!confirmar) return;

  apagarAssinante.disabled = true;
  try {
    const r = await window.extratorAPI.apagarCredenciaisAssinante(PROVEDOR_ASSINANTE);
    if (!r.ok) {
      assinanteStatus.textContent = r.erro || 'Não foi possível apagar o acesso salvo.';
      return;
    }
    assinanteSenhaSalva = false;
    assinanteUsuario.value = '';
    assinanteSenha.value = '';
    assinanteSenha.placeholder = 'Digite uma vez para salvar';
    assinanteStatus.textContent = 'Acesso salvo apagado deste computador.';
    definirStatus('Acesso de assinante removido.', 'ready');
  } catch (e) {
    assinanteStatus.textContent = 'Erro ao apagar acesso: ' + (e?.message || e);
  } finally {
    apagarAssinante.disabled = !assinanteSenhaSalva;
  }
}

function preencherMetadados(retorno) {
  metaTitulo.textContent = retorno.titulo || 'Não identificado';
  metaVeiculo.textContent = retorno.veiculo || 'Não identificado';
  metaData.textContent = retorno.data || 'Não identificada';
  metaAutor.textContent = retorno.autor || 'Não informado';
  metaSubtitulo.textContent = retorno.subtitulo || 'Não informado';
  metaLink.textContent = retorno.url || '—';
  metaLink.title = retorno.url || '';
  successMark.classList.add('ativo');
}

function limparMetadados() {
  metaTitulo.textContent = 'Aguardando extração';
  metaVeiculo.textContent = '—';
  metaData.textContent = '—';
  metaAutor.textContent = '—';
  metaSubtitulo.textContent = '—';
  metaLink.textContent = '—';
  metaLink.title = '';
  successMark.classList.remove('ativo');
}

function limparDestaquesRigidos() {
  try {
    if (window.CSS?.highlights) CSS.highlights.delete('corretor-rigido-ptbr');
  } catch (_) {}
}

function localizarOffsetTexto(root, offset) {
  const alvo = Math.max(0, Number(offset) || 0);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let acumulado = 0;
  let ultimo = null;

  while (walker.nextNode()) {
    const node = walker.currentNode;
    ultimo = node;
    const tamanho = node.nodeValue?.length || 0;
    if (alvo <= acumulado + tamanho) {
      return { node, offset: Math.min(tamanho, alvo - acumulado) };
    }
    acumulado += tamanho;
  }

  if (ultimo) return { node: ultimo, offset: ultimo.nodeValue?.length || 0 };
  return null;
}

function aplicarDestaquesRigidos(issues) {
  limparDestaquesRigidos();
  if (!issues?.length) return;
  if (!window.CSS?.highlights || typeof Highlight === 'undefined') return;

  const highlight = new Highlight();
  const total = (resultado.textContent || '').length;

  for (const issue of issues) {
    const inicio = Math.max(0, Math.min(total, Number(issue.offset) || 0));
    const fim = Math.max(inicio, Math.min(total, inicio + (Number(issue.length) || String(issue.palavra || '').length)));
    const a = localizarOffsetTexto(resultado, inicio);
    const b = localizarOffsetTexto(resultado, fim);
    if (!a || !b) continue;

    try {
      const range = new Range();
      range.setStart(a.node, a.offset);
      range.setEnd(b.node, b.offset);
      highlight.add(range);
    } catch (_) {}
  }

  CSS.highlights.set('corretor-rigido-ptbr', highlight);
}

function selecionarIssue(issue) {
  const inicio = localizarOffsetTexto(resultado, issue.offset);
  const fim = localizarOffsetTexto(resultado, Number(issue.offset) + Number(issue.length || String(issue.palavra || '').length));
  if (!inicio || !fim) return;

  try {
    const range = new Range();
    range.setStart(inicio.node, inicio.offset);
    range.setEnd(fim.node, fim.offset);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    resultado.focus();
  } catch (_) {}
}

async function substituirIssue(issue, sugestao) {
  const texto = resultado.textContent || '';
  const inicio = Number(issue.offset) || 0;
  const tamanho = Number(issue.length) || String(issue.palavra || '').length;
  const atual = texto.slice(inicio, inicio + tamanho);

  if (atual !== issue.palavra) {
    await revisarTextoRigido();
    return;
  }

  resultado.textContent = texto.slice(0, inicio) + sugestao + texto.slice(inicio + tamanho);
  resultadoVazio.classList.add('oculto');
  btnCopiar.disabled = false;
  await revisarTextoRigido({ automatico: true });
}

function renderizarListaRevisao(issues) {
  if (!revisaoRigidaLista) return;
  revisaoRigidaLista.innerHTML = '';

  if (!issues?.length) {
    revisaoRigidaLista.classList.add('oculto');
    return;
  }

  revisaoRigidaLista.classList.remove('oculto');
  const limite = Math.min(40, issues.length);

  for (let i = 0; i < limite; i++) {
    const issue = issues[i];
    const item = document.createElement('div');
    item.className = 'revisao-issue';

    const palavra = document.createElement('button');
    palavra.type = 'button';
    palavra.className = 'revisao-palavra';
    palavra.textContent = issue.palavra;
    palavra.title = 'Localizar no texto';
    palavra.addEventListener('click', () => selecionarIssue(issue));
    item.appendChild(palavra);

    const sugestoes = document.createElement('div');
    sugestoes.className = 'revisao-sugestoes';

    if (issue.sugestoes?.length) {
      for (const sugestao of issue.sugestoes.slice(0, 5)) {
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'revisao-sugestao';
        botao.textContent = sugestao;
        botao.addEventListener('click', () => substituirIssue(issue, sugestao));
        sugestoes.appendChild(botao);
      }
    } else {
      const sem = document.createElement('span');
      sem.className = 'revisao-sem-sugestao';
      sem.textContent = 'sem sugestão';
      sugestoes.appendChild(sem);
    }

    item.appendChild(sugestoes);
    revisaoRigidaLista.appendChild(item);
  }

  if (issues.length > limite) {
    const mais = document.createElement('div');
    mais.className = 'revisao-mais';
    mais.textContent = `+ ${issues.length - limite} ocorrências adicionais`;
    revisaoRigidaLista.appendChild(mais);
  }
}

async function revisarTextoRigido({ automatico = false } = {}) {
  if (!revisarRigido || revisandoRigido) return;
  const texto = resultado.textContent || '';

  if (!texto.trim()) {
    revisaoRigidaIssues = [];
    limparDestaquesRigidos();
    renderizarListaRevisao([]);
    revisarRigido.disabled = true;
    revisaoRigidaStatus.textContent = 'Modo rígido aguardando texto.';
    return;
  }

  revisandoRigido = true;
  revisarRigido.disabled = true;
  revisaoRigidaStatus.textContent = 'Revisando PT-BR com acentuação obrigatória…';

  try {
    const r = await window.extratorAPI.revisarTextoRigido(texto);
    if (!r.ok) {
      revisaoRigidaStatus.textContent = 'Revisão rígida indisponível: ' + (r.erro || 'erro desconhecido');
      if (!automatico) definirStatus('Falha ao executar a revisão rígida PT-BR.', 'error');
      return;
    }

    revisaoRigidaIssues = Array.isArray(r.issues) ? r.issues : [];
    aplicarDestaquesRigidos(revisaoRigidaIssues);
    renderizarListaRevisao(revisaoRigidaIssues);

    if (revisaoRigidaIssues.length) {
      revisaoRigidaStatus.textContent = `${revisaoRigidaIssues.length} possível(is) erro(s) — acentos e grafia verificados em modo rígido.`;
      if (!automatico) definirStatus('Revisão rígida concluída com palavras para conferir.', 'ready');
    } else {
      revisaoRigidaStatus.textContent = '✓ Nenhum erro ortográfico encontrado pelo modo rígido PT-BR.';
      if (!automatico) definirStatus('✓ Revisão rígida PT-BR concluída.', 'success');
    }
  } catch (e) {
    revisaoRigidaStatus.textContent = 'Erro na revisão rígida: ' + (e?.message || e);
    if (!automatico) definirStatus('Erro na revisão rígida PT-BR.', 'error');
  } finally {
    revisandoRigido = false;
    revisarRigido.disabled = !(resultado.textContent || '').trim();
  }
}

function agendarRevisaoRigida() {
  clearTimeout(revisaoRigidaTimer);
  revisaoRigidaTimer = setTimeout(() => revisarTextoRigido({ automatico: true }), 900);
}

function exibirResultado(texto = '') {
  limparDestaquesRigidos();
  revisaoRigidaIssues = [];
  renderizarListaRevisao([]);
  resultado.textContent = texto;
  const temTexto = !!texto.trim();
  resultadoVazio.classList.toggle('oculto', temTexto);
  btnCopiar.disabled = !temTexto;
  if (revisarRigido) revisarRigido.disabled = !temTexto;
  if (revisaoRigidaStatus) revisaoRigidaStatus.textContent = temTexto
    ? 'Modo rígido pronto para revisar acentos e grafia.'
    : 'Modo rígido aguardando texto.';
}

async function atualizarEstado() {
  const estado = await window.extratorAPI.obterEstado();
  btnUltimo.disabled = !estado.ultimoExiste;

  if (estado.versaoMotor) {
    const texto = 'Motor ' + estado.versaoMotor;
    versao.textContent = texto;
    versaoSidebar.textContent = estado.versaoMotor;
    const versaoCurta = String(estado.versaoMotor).split('-')[0];
    if (versaoCurta) document.title = 'Extrator de Matérias V' + versaoCurta;
  }
}

async function extrair() {
  const informado = url.value.trim();
  if (!informado) {
    definirStatus('Cole o link da matéria.', 'error');
    url.focus();
    sincronizarBotaoExtrair();
    return;
  }
  if (!/^https?:\/\/.+/i.test(informado)) {
    definirStatus('O link precisa começar com http:// ou https://', 'error');
    url.focus();
    sincronizarBotaoExtrair();
    return;
  }
  if (usarProxy.checked && !usuario.value.trim()) {
    definirStatus('Informe o usuário do proxy.', 'error');
    usuario.focus();
    return;
  }
  if (usarProxy.checked && !senha.value) {
    definirStatus('Informe a senha do proxy.', 'error');
    senha.focus();
    return;
  }

  extraindo = true;
  sincronizarBotaoExtrair();
  btnExtrair.setAttribute('aria-busy', 'true');
  exibirResultado('');
  limparMetadados();
  info.textContent = 'Processando…';
  definirStatus('Preparando a extração…', 'busy');

  try {
    const retorno = await window.extratorAPI.extrair({
      url: informado,
      usarProxy: usarProxy.checked,
      usuario: usuario.value,
      senha: senha.value
    });

    if (retorno.ok) {
      exibirResultado(retorno.formatado || '');
      preencherMetadados(retorno);
      info.textContent = `${retorno.corpoCaracteres.toLocaleString('pt-BR')} caracteres`;
      definirStatus('✓ Extração concluída e salva.', 'success');
      await atualizarEstado();
      await revisarTextoRigido({ automatico: true });
    } else {
      definirStatus(retorno.erro || 'Não foi possível concluir a extração.', 'error');
      info.textContent = 'Falha na extração';
    }
  } catch (e) {
    definirStatus('Erro ao processar: ' + (e?.message || e), 'error');
    info.textContent = 'Falha na extração';
  } finally {
    extraindo = false;
    btnExtrair.removeAttribute('aria-busy');
    sincronizarBotaoExtrair();
  }
}

async function abrirUltimo() {
  const r = await window.extratorAPI.abrirUltimo();
  if (!r.ok) definirStatus(r.erro, 'error');
}

async function abrirHistorico() {
  const r = await window.extratorAPI.abrirHistorico();
  if (!r.ok) definirStatus(r.erro, 'error');
}

async function abrirPasta() {
  const r = await window.extratorAPI.abrirPasta();
  if (!r.ok) definirStatus(r.erro, 'error');
}

async function copiarResultado() {
  const texto = resultado.textContent || '';
  if (!texto.trim()) return;

  try {
    await navigator.clipboard.writeText(texto);
    definirStatus('✓ Texto copiado para a área de transferência.', 'success');
  } catch (_) {
    const area = document.createElement('textarea');
    area.value = texto;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    definirStatus(ok ? '✓ Texto copiado para a área de transferência.' : 'Não foi possível copiar o texto.', ok ? 'success' : 'error');
  }
}

function limparTela() {
  clearTimeout(revisaoRigidaTimer);
  url.value = '';
  exibirResultado('');
  limparMetadados();
  info.textContent = 'Nenhuma matéria extraída';
  definirStatus('Pronto para receber um link.', 'ready');
  sincronizarBotaoExtrair();
  url.focus();
}

btnExtrair.addEventListener('click', extrair);
btnUltimo.addEventListener('click', abrirUltimo);
btnHistorico.addEventListener('click', abrirHistorico);
btnPasta.addEventListener('click', abrirPasta);
btnLimpar.addEventListener('click', limparTela);
btnCopiar.addEventListener('click', copiarResultado);
if (revisarRigido) revisarRigido.addEventListener('click', () => revisarTextoRigido());
if (salvarAssinante) salvarAssinante.addEventListener('click', salvarAcessoAssinante);
if (apagarAssinante) apagarAssinante.addEventListener('click', apagarAcessoAssinante);

resultado.addEventListener('input', () => {
  const temTexto = !!(resultado.textContent || '').trim();
  btnCopiar.disabled = !temTexto;
  if (revisarRigido) revisarRigido.disabled = !temTexto;
  agendarRevisaoRigida();
});

url.addEventListener('input', sincronizarBotaoExtrair);
url.addEventListener('change', sincronizarBotaoExtrair);
url.addEventListener('paste', () => setTimeout(sincronizarBotaoExtrair, 0));

document.querySelectorAll('[data-action="historico"]').forEach(el => el.addEventListener('click', abrirHistorico));
document.querySelectorAll('[data-action="pasta"]').forEach(el => el.addEventListener('click', abrirPasta));
document.querySelectorAll('[data-scroll]').forEach(el => {
  el.addEventListener('click', () => {
    const alvo = document.getElementById(el.dataset.scroll);
    if (alvo) alvo.scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('ativo'));
    if (el.classList.contains('nav-item')) el.classList.add('ativo');
  });
});

url.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.ctrlKey && !btnExtrair.disabled) {
    e.preventDefault();
    extrair();
  }
});

sincronizarBotaoExtrair();
if (revisarRigido) revisarRigido.disabled = true;
Promise.all([
  atualizarEstado().catch(() => {}),
  carregarAcessoAssinante().catch(() => {})
]);
