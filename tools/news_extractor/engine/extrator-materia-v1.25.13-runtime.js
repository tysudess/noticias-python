const base = require('./extrator-materia-v1.25.12-runtime.js');

const VERSAO = '1.25.13-PROXY-RESTAURADO-SENHA-VISIVEL';

// V1.25.13 preserva integralmente o motor V1.25.12.
// A correção desta versão é de configuração/conexão e interface:
// - restaura servidor/porta do proxy corporativo no pacote;
// - mantém usuário/senha apenas na memória da sessão;
// - deixa o campo de senha visível na interface, conforme solicitado.

module.exports = {
  ...base,
  VERSAO
};
