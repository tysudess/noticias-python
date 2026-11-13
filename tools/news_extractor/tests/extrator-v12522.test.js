'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const runtime = require('../engine/extrator-materia-v1.25.22-runtime.js');

const ARTICLE_URL = 'https://www.naval.com.br/blog/2026/11/11/classe-udaloy-os-cacadores-de-submarinos-da-marinha-sovietica-e-russa/';

const HTML = `<!doctype html><html lang="pt-BR"><head>
  <meta property="og:site_name" content="Poder Naval">
  <meta property="og:title" content="Classe Udaloy: os caçadores de submarinos da Marinha soviética e russa">
  <meta property="article:published_time" content="2026-11-11T08:00:00-03:00">
  <meta name="author" content="Alexandre Galante">
</head><body>
  <header><nav>Início Notícias Arquivo</nav></header>
  <main><article class="post">
    <h1>Classe Udaloy: os caçadores de submarinos da Marinha soviética e russa</h1>
    <div class="entry-content">
      <p>A URSS planejou 15 navios do Projeto 1155 e terminou 13. Eles foram concebidos nos anos 1970 para caçar submarinos nucleares americanos e sobreviveram ao fim da União Soviética.</p>
      <p>O primeiro navio da classe entrou em serviço em 1980, e as unidades seguintes foram distribuídas entre as frotas do Norte e do Pacífico.</p>
      <h2>Dois navios no lugar de um</h2>
      <p>A classe Udaloy nasceu de uma decisão de economia. A Marinha soviética concluiu que navios polivalentes do tamanho de um cruzador eram caros demais.</p>
      <p>O Projeto 1155 foi desenvolvido para a guerra antissubmarino, com sonar de casco e helicópteros embarcados para ampliar a área de busca.</p>
      <p>Tags: História Naval, Marinhas de Guerra, Submarinos</p>
      <p>Fonte: Poder Naval</p>
      <p>Leia mais: https://www.naval.com.br/blog/arquivo/</p>
    </div>
    <div class="related-posts"><p>Outra notícia relacionada que não integra a matéria principal e deve ser descartada da extração.</p></div>
    <section class="comments"><p>Deixe seu comentário</p></section>
  </article></main><footer>Publicidade</footer>
</body></html>`;

test('reconhece o domínio Poder Naval com e sem www', () => {
  assert.equal(runtime.isPoderNaval('https://www.naval.com.br/blog/noticia/'), true);
  assert.equal(runtime.isPoderNaval('https://naval.com.br/blog/noticia/'), true);
  assert.equal(runtime.isPoderNaval('https://exemplo.com/naval.com.br/noticia/'), false);
});

test('usa o corpo do Poder Naval quando a extração principal não localiza o artigo', () => {
  const result = runtime.extractPoderNavalBody(HTML, ARTICLE_URL, {});
  assert.ok(result);
  assert.equal(result.veiculo, 'Poder Naval');
  assert.match(result.texto, /A URSS planejou 15 navios/);
  assert.match(result.texto, /A classe Udaloy nasceu de uma decisão de economia/);
  assert.doesNotMatch(result.texto, /Tags:|Fonte:|Leia mais|Outra notícia relacionada|comentário|Publicidade/i);
});

test('a limpeza preserva parágrafos e remove repetições e rodapés', () => {
  const body = [
    'A Marinha anunciou uma nova etapa de exercícios navais no Atlântico Sul, com participação de navios e equipes embarcadas.',
    'A Marinha anunciou uma nova etapa de exercícios navais no Atlântico Sul, com participação de navios e equipes embarcadas.',
    'Créditos: Poder Naval',
    'As atividades incluem treinamento de comunicações, segurança e interoperabilidade entre as unidades participantes.'
  ].join('\n\n');
  const cleaned = runtime.cleanPoderNavalText(body, ARTICLE_URL, {});
  assert.equal((cleaned.match(/A Marinha anunciou/g) || []).length, 1);
  assert.match(cleaned, /As atividades incluem treinamento/);
  assert.doesNotMatch(cleaned, /Créditos:/i);
});
