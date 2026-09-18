const base = require('./extrator-materia-v1.25.16-runtime.js');

const VERSAO = '1.25.17-ACESSO-ASSINANTE-SALVO-SEGURO';

// V1.25.17 preserva integralmente o motor V1.25.16.
// A evolução desta versão é de interface/armazenamento seguro de credenciais
// de assinante no Windows. O motor de extração permanece inalterado.

module.exports = {
  ...base,
  VERSAO
};
