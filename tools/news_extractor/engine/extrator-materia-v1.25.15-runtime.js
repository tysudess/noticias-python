const base = require('./extrator-materia-v1.25.14-runtime.js');

const VERSAO = '1.25.15-BOTAO-EXTRAIR-URL-FIX';

// V1.25.15 preserva integralmente o motor V1.25.14.
// A correção desta versão é exclusivamente na interface:
// - o botão Extrair matéria acompanha o conteúdo do campo de URL;
// - habilita imediatamente para http:// ou https://;
// - volta ao estado correto após colar, limpar, erro ou término da extração.

module.exports = {
  ...base,
  VERSAO
};
