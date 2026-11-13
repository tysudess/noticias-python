'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const runtime = require('../engine/extrator-materia-v1.25.21-runtime.js');

test('Zona Militar: localiza o corpo editorial e remove chamadas de leitura e créditos', () => {
  const html = `<!doctype html><html><head><title>Matéria</title></head><body>
    <header>Menu principal</header>
    <article>
      <h1>Exército Brasileiro avança em novo programa</h1>
      <div class="entry-content">
        <p>O Exército Brasileiro avançou nesta semana em um programa de modernização de suas capacidades operacionais, conforme informações divulgadas pela instituição.</p>
        <p>O planejamento prevê novas etapas de avaliação técnica, integração dos sistemas e preparação das equipes que participarão das próximas atividades.</p>
        <p>As medidas fazem parte de um cronograma mais amplo, que busca ampliar a disponibilidade dos meios e a capacidade de atuação das unidades envolvidas.</p>
        <p>👉 Leia mais: https://www.zona-militar.com/relacionada/</p>
        <p>Fuente: arquivo institucional</p>
        <p>Créditos Baykar</p>
        <p>Publicidad</p>
      </div>
      <div class="related-posts"><p>Outra notícia relacionada com texto suficientemente longo que não pertence à matéria principal e deve ser ignorado.</p></div>
      <section class="comments"><p>Deixe seu comentário</p></section>
    </article>
    <footer>Rodapé do portal</footer>
  </body></html>`;

  const result = runtime.extractPortalBody(
    html,
    'https://www.zona-militar.com/pt/2026/09/02/exemplo/',
    {}
  );
  assert.ok(result, 'deve identificar um corpo com vários parágrafos');
  assert.equal(result.veiculo, 'Zona Militar');
  assert.match(result.text, /O Exército Brasileiro avançou nesta semana/);
  assert.doesNotMatch(result.text, /Leia mais|Fuente:|Créditos Baykar|Publicidad|Outra notícia relacionada|comentário/i);
});

test('Defesa Aérea & Naval: usa o conteúdo WordPress e preserva os parágrafos da matéria', () => {
  const html = `<!doctype html><html><head>
    <meta property="og:site_name" content="Defesa Aérea & Naval">
    <meta property="og:title" content="Navio inicia exercício no Atlântico Sul">
  </head><body><article>
    <h1>Navio inicia exercício no Atlântico Sul</h1>
    <div class="td-post-content">
      <p>O navio iniciou uma nova etapa de exercício no Atlântico Sul, com atividades de navegação e treinamento coordenado entre as equipes embarcadas.</p>
      <p>Durante a comissão, os militares realizarão procedimentos de segurança, comunicações e exercícios de interoperabilidade com outras unidades participantes.</p>
      <h2>Atividades no mar</h2>
      <p>A programação inclui cenários de treinamento e avaliações operacionais para verificar os procedimentos adotados durante as operações conjuntas.</p>
      <p>Tags: Marinha, exercício, Atlântico Sul</p>
      <p>Notícia Anterior Próxima Notícia</p>
    </div>
    <div class="post-share">Compartilhe esta notícia</div>
  </article></body></html>`;

  const result = runtime.extractPortalBody(
    html,
    'https://www.defesaaereanaval.com.br/naval/exemplo-de-materia',
    {}
  );
  assert.ok(result);
  assert.equal(result.veiculo, 'Defesa Aérea & Naval');
  assert.match(result.text, /O navio iniciou uma nova etapa/);
  assert.match(result.text, /A programação inclui cenários/);
  assert.doesNotMatch(result.text, /Tags:|Compartilhe|Notícia Anterior/i);
});

test('limpeza genérica remove lixo isolado e duplicações sem apagar os parágrafos', () => {
  const source = [
    'Publicidade',
    'Este é um parágrafo jornalístico completo que apresenta os fatos centrais da notícia e explica o que aconteceu.',
    'Este é um parágrafo jornalístico completo que apresenta os fatos centrais da notícia e explica o que aconteceu.',
    'Fonte: divulgação',
    'Créditos: arquivo da redação',
    'A equipe responsável informou que as próximas etapas serão realizadas após a conclusão das avaliações técnicas previstas.'
  ].join('\n\n');

  const result = runtime.cleanGenericText(source, 'https://portal.example/noticia', {});
  assert.match(result, /apresenta os fatos centrais/);
  assert.match(result, /próximas etapas serão realizadas/);
  assert.equal((result.match(/apresenta os fatos centrais/g) || []).length, 1);
  assert.doesNotMatch(result, /Publicidade|Fonte:|Créditos:/i);
});
