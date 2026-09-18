const base = require('./extrator-materia-v1.25.18-runtime.js');

const VERSAO = '1.25.19-CORRETOR-RIGIDO-PTBR-ACENTOS';

// V1.25.19 preserva integralmente o motor V1.25.18.
// A evolução desta versão é somente de revisão local do texto:
// uma segunda camada PT-BR mais rígida, com acentuação obrigatória.

module.exports = {
  ...base,
  VERSAO
};
