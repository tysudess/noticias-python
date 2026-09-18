const camada = require('./extrator-materia-v1.25.10.js');
const { recuperarCorpoCompletoG1 } = require('./correcoes-g1-v1.25.10.js');

const VERSAO = '1.25.10-CORRECOES-FONTES-G1-CORPO-LITERAL-HOTFIX';

function formatar(m) {
  const p = [m.url, '', m.veiculo, '', `*${m.titulo || 'Título não identificado'}*`];
  if (m.subtitulo) p.push('', `_${m.subtitulo}_`);
  p.push('');
  if (m.autor) p.push(m.autor);
  p.push(m.data || 'Data não identificada', '', m.texto || '');
  m.resultado = p.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
  return m;
}

async function extrairMateria(url) {
  const materia = await camada.extrairMateria(url);

  // G1: a recuperação complementar é conservadora. Ela nunca substitui o
  // corpo por resumo/card; apenas acrescenta parágrafos literais que estejam
  // depois do último parágrafo já extraído no corpo principal da notícia.
  await recuperarCorpoCompletoG1(materia, camada);

  if (!materia.texto) throw new Error('O corpo da matéria ficou vazio após as correções.');
  return formatar(materia);
}

module.exports = {
  ...camada,
  VERSAO,
  extrairMateria
};
