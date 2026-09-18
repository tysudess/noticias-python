const base = require('./extrator-materia-v1.25.17-runtime.js');

const VERSAO = '1.25.18-CORRETOR-ORTOGRAFICO-PTBR';

// V1.25.18 preserva integralmente o motor V1.25.17.
// A evolução desta versão é somente de interface: corretor ortográfico PT-BR
// na área editável de conteúdo, sem alterar a extração das matérias.

module.exports = {
  ...base,
  VERSAO
};
