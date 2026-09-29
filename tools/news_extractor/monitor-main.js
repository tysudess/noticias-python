const { app } = require('electron');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const headless = String(
  process.env.MONITOR_HEADLESS || ''
).trim() === '1';

if (!headless) {
  require('./main.js');
} else {
  const motor = require(
    './engine/extrator-materia-v1.25.10-runtime.js'
  );

  const RESULT_FILE = String(
    process.env.MONITOR_RESULT_FILE || ''
  ).trim();

  const URL = String(
    process.env.MONITOR_NEWS_URL || ''
  ).trim();

  const PERSISTENT = String(
    process.env.MONITOR_PERSISTENT || ''
  ).trim() === '1';

  const CENTRAL_PROXY_PRESENT =
    Object.prototype.hasOwnProperty.call(
      process.env,
      'CENTRAL_PROXY_ENABLED'
    );

  const CENTRAL_PROXY_ENABLED =
    process.env.CENTRAL_PROXY_ENABLED === '1';

  const CENTRAL_PROXY_HOST = String(
    process.env.CENTRAL_PROXY_HOST || ''
  ).trim();

  const CENTRAL_PROXY_PORT = String(
    process.env.CENTRAL_PROXY_PORT || ''
  ).trim();

  const CENTRAL_PROXY_USERNAME = String(
    process.env.CENTRAL_PROXY_USERNAME || ''
  ).trim();

  const CENTRAL_PROXY_PASSWORD = String(
    process.env.CENTRAL_PROXY_PASSWORD || ''
  );

  const FAST_MODE = String(
    process.env.CENTRAL_NEWS_FAST_MODE || ''
  ).trim() === '1';

  const NAV_TIMEOUT_MS =
    Number.parseInt(
      process.env.CENTRAL_NEWS_NAV_TIMEOUT_MS || '',
      10
    )
    || (FAST_MODE ? 18000 : 30000);

  const IDLE_TIMEOUT_MS =
    Number.parseInt(
      process.env.CENTRAL_NEWS_IDLE_TIMEOUT_MS || '',
      10
    )
    || (FAST_MODE ? 800 : 1400);

  const BLOCK_IMAGES = String(
    process.env.CENTRAL_NEWS_BLOCK_IMAGES || ''
  ).trim() === '1';

  const BLOCK_MEDIA = String(
    process.env.CENTRAL_NEWS_BLOCK_MEDIA || ''
  ).trim() === '1';

  const PASTA_NOME = 'ExtratorMaterias';
  const ARQUIVO_ULTIMO = 'materia-extraida.txt';
  const ARQUIVO_HISTORICO = 'materias-extraidas.txt';
  const SEPARADOR =
    '\n'
    + '#'.repeat(70)
    + '\n\n';

  function pastaDownload() {
    return path.join(
      app.getPath('downloads'),
      PASTA_NOME
    );
  }

  function salvarResultado(materia) {
    const pasta = pastaDownload();

    fs.mkdirSync(
      pasta,
      { recursive: true }
    );

    const ultimo = path.join(
      pasta,
      ARQUIVO_ULTIMO
    );

    const historico = path.join(
      pasta,
      ARQUIVO_HISTORICO
    );

    fs.writeFileSync(
      ultimo,
      String(materia.resultado || ''),
      'utf8'
    );

    try {
      const repetida = motor.historicoContemUrl(
        materia.url,
        historico
      );

      if (!repetida) {
        fs.appendFileSync(
          historico,
          String(materia.resultado || '')
            + SEPARADOR,
          'utf8'
        );
      }
    } catch (_) {}
  }

  function carregarConfigBase() {
    const configFile = path.join(
      __dirname,
      'engine',
      'config-proxy.json'
    );

    const padrao = {
      ATIVADO: false,
      SERVIDOR: '',
      PORTA: '',
      TIMEOUT_MS: FAST_MODE ? 25000 : 45000,
      CERTIFICADO_CA: '',
      NAV_TIMEOUT_MS,
      IDLE_TIMEOUT_MS,
      BLOCK_IMAGES,
      BLOCK_MEDIA,
      FAST_MODE,
    };

    if (!fs.existsSync(configFile)) {
      return padrao;
    }

    try {
      return {
        ...padrao,
        ...JSON.parse(
          fs
            .readFileSync(
              configFile,
              'utf8'
            )
            .replace(/^\uFEFF/, '')
        ),
        NAV_TIMEOUT_MS,
        IDLE_TIMEOUT_MS,
        BLOCK_IMAGES,
        BLOCK_MEDIA,
        FAST_MODE,
      };
    } catch (_) {
      return padrao;
    }
  }

  function prepararRede() {
    const config = carregarConfigBase();

    if (CENTRAL_PROXY_PRESENT) {
      if (!CENTRAL_PROXY_ENABLED) {
        motor.prepararProxy(
          '',
          '',
          {
            ...config,
            ATIVADO: false,
          }
        );

        if (!PERSISTENT) {
          console.log(
            'REDE: configuração recebida do Proxy Geral do Central'
          );
          console.log('PROXY: DESATIVADO');
        }

        return;
      }

      if (
        !CENTRAL_PROXY_HOST
        || !CENTRAL_PROXY_PORT
      ) {
        throw new Error(
          'Proxy Geral do Central está ativo, mas servidor/porta não foram informados.'
        );
      }

      if (
        !CENTRAL_PROXY_USERNAME
        || !CENTRAL_PROXY_PASSWORD
      ) {
        throw new Error(
          'Proxy Geral do Central está ativo, mas usuário/senha não foram informados.'
        );
      }

      motor.prepararProxy(
        CENTRAL_PROXY_USERNAME,
        CENTRAL_PROXY_PASSWORD,
        {
          ...config,
          ATIVADO: true,
          SERVIDOR: CENTRAL_PROXY_HOST,
          PORTA: CENTRAL_PROXY_PORT,
        }
      );

      if (!PERSISTENT) {
        console.log(
          'REDE: configuração recebida do Proxy Geral do Central'
        );
        console.log(
          `PROXY ATIVO: ${CENTRAL_PROXY_HOST}:${CENTRAL_PROXY_PORT}`
        );
        console.log(
          'PROXY COM AUTENTICAÇÃO CONFIGURADA'
        );
      }

      return;
    }

    motor.prepararProxy(
      '',
      '',
      {
        ...config,
        ATIVADO: false,
      }
    );

    if (!PERSISTENT) {
      console.log(
        'REDE: conexão direta (fora do Central)'
      );
    }
  }

  function corpo(materia) {
    return String(
      materia?.texto || ''
    ).trim();
  }

  function titulo(materia) {
    return String(
      materia?.titulo || ''
    ).trim();
  }

  function blocos(materia) {
    return corpo(materia)
      .split(/\n\s*\n/)
      .map(value => value.trim())
      .filter(Boolean);
  }

  function pontuarMateria(materia) {
    if (!materia) {
      return 0;
    }

    const texto = corpo(materia);
    const head = titulo(materia);
    const paragraphs = blocos(materia);

    let score = 0;

    if (head.length >= 8) score += 20;
    if (head.length >= 25) score += 5;

    if (texto.length >= 350) score += 15;
    if (texto.length >= 700) score += 20;
    if (texto.length >= 1400) score += 20;
    if (texto.length >= 2600) score += 10;

    if (paragraphs.length >= 2) score += 4;
    if (paragraphs.length >= 4) score += 4;

    if (String(materia.autor || '').trim()) {
      score += 1;
    }

    if (
      String(materia.data || '').trim()
      && !/não identificada/i.test(
        String(materia.data)
      )
    ) {
      score += 1;
    }

    return score;
  }

  function resultadoSuspeito(materia) {
    if (
      !materia
      || !materia.resultado
    ) {
      return true;
    }

    const texto = corpo(materia);
    const head = titulo(materia);
    const paragraphs = blocos(materia);

    if (head.length < 8) {
      return true;
    }

    if (texto.length < 350) {
      return true;
    }

    if (
      paragraphs.length < 2
      && texto.length < 800
    ) {
      return true;
    }

    return false;
  }

  function erroNaoDeveRepetir(erro) {
    const text = String(
      erro?.message
      || erro
      || ''
    );

    return (
      /\b(?:401|403|404|407)\b/i.test(text)
      || /proxy authentication required/i.test(text)
      || /usuário\/senha/i.test(text)
      || /credenciais/i.test(text)
    );
  }

  async function extrairComConferencia(url) {
    const started = Date.now();

    let materia = null;
    let primeiroErro = null;
    let segundaLeituraUsada = false;

    try {
      materia = await motor.extrairMateria(url);
    } catch (erro) {
      primeiroErro = erro;
    }

    const tentarDeNovo = (
      (
        !materia
        && !erroNaoDeveRepetir(primeiroErro)
      )
      || resultadoSuspeito(materia)
    );

    if (tentarDeNovo) {
      segundaLeituraUsada = true;

      try {
        const segunda =
          await motor.extrairMateria(url);

        if (
          !materia
          || pontuarMateria(segunda)
            > pontuarMateria(materia)
        ) {
          materia = segunda;
        }
      } catch (segundoErro) {
        if (!materia) {
          throw segundoErro;
        }
      }
    }

    if (!materia) {
      throw (
        primeiroErro
        || new Error(
          'Não foi possível extrair a matéria.'
        )
      );
    }

    return {
      materia,
      segundaLeituraUsada,
      qualidadeScore:
        pontuarMateria(materia),
      duracaoMs:
        Date.now() - started,
    };
  }

  async function executarUrl(url) {
    const rawUrl = String(
      url || ''
    ).trim();

    if (!rawUrl) {
      throw new Error(
        'MONITOR_NEWS_URL não informado.'
      );
    }

    if (!/^https?:\/\//i.test(rawUrl)) {
      throw new Error(
        'O link precisa começar com http:// ou https://.'
      );
    }

    const extraction =
      await extrairComConferencia(rawUrl);

    const materia =
      extraction.materia;

    if (
      !materia
      || !materia.resultado
      || !materia.texto
    ) {
      throw new Error(
        'O motor não retornou o corpo completo da matéria.'
      );
    }

    salvarResultado(materia);

    return {
      ok: true,
      formatado: materia.resultado,
      url: materia.url,
      veiculo: materia.veiculo,
      titulo: materia.titulo,
      subtitulo: materia.subtitulo,
      autor: materia.autor,
      data: materia.data,
      corpoCaracteres:
        String(materia.texto || '').length,
      versaoMotor: motor.VERSAO,
      rede: CENTRAL_PROXY_PRESENT
        ? (
          CENTRAL_PROXY_ENABLED
            ? 'proxy-central'
            : 'direta-central'
        )
        : 'direta-standalone',
      modoRapido: FAST_MODE,
      segundaLeituraUsada:
        extraction.segundaLeituraUsada,
      qualidadeScore:
        extraction.qualidadeScore,
      duracaoMs:
        extraction.duracaoMs,
    };
  }

  function gravarArquivoResultado(
    resultFile,
    result
  ) {
    const target = String(
      resultFile || ''
    ).trim();

    if (!target) {
      return;
    }

    fs.mkdirSync(
      path.dirname(target),
      { recursive: true }
    );

    const tmp =
      target
      + '.tmp-'
      + process.pid;

    fs.writeFileSync(
      tmp,
      JSON.stringify(
        result,
        null,
        2
      ),
      'utf8'
    );

    try {
      fs.renameSync(
        tmp,
        target
      );
    } catch (erro) {
      try {
        fs.unlinkSync(target);
      } catch (_) {}

      fs.renameSync(
        tmp,
        target
      );
    }
  }

  async function executarUmaVez() {
    let result;

    try {
      if (!RESULT_FILE) {
        throw new Error(
          'MONITOR_RESULT_FILE não informado.'
        );
      }

      prepararRede();

      console.log(
        `EXTRAÇÃO: modo ${FAST_MODE ? 'rápido' : 'padrão'}`
      );

      result =
        await executarUrl(URL);

    } catch (erro) {
      result = {
        ok: false,
        erro:
          erro?.message
          || String(erro),
      };
    }

    try {
      gravarArquivoResultado(
        RESULT_FILE,
        result
      );
    } catch (_) {}

    app.quit();
  }

  function protocolo(payload) {
    try {
      process.stdout.write(
        'CENTRAL_RESULT '
        + JSON.stringify(payload)
        + '\n'
      );
    } catch (_) {}
  }

  async function executarPersistente() {
    // Rede e Proxy são preparados UMA vez. Isso permite reaproveitar
    // o ProxyAgent / pool de conexões entre várias matérias.
    prepararRede();

    const rl = readline.createInterface({
      input: process.stdin,
      crlfDelay: Infinity,
    });

    let chain = Promise.resolve();

    const handle = async line => {
      let request;

      try {
        request = JSON.parse(
          String(line || '').trim()
        );
      } catch (_) {
        return;
      }

      if (
        String(
          request.command || ''
        ).toLowerCase()
        === 'shutdown'
      ) {
        protocolo({
          command: 'shutdown',
          ok: true,
        });

        rl.close();
        app.quit();
        return;
      }

      const id = String(
        request.id || ''
      );

      const url = String(
        request.url || ''
      );

      const resultFile = String(
        request.resultFile || ''
      );

      let result;

      try {
        result =
          await executarUrl(url);
      } catch (erro) {
        result = {
          ok: false,
          erro:
            erro?.message
            || String(erro),
        };
      }

      try {
        gravarArquivoResultado(
          resultFile,
          result
        );
      } catch (erroArquivo) {
        result = {
          ok: false,
          erro:
            'Falha ao gravar o resultado temporário: '
            + (
              erroArquivo?.message
              || String(erroArquivo)
            ),
        };
      }

      protocolo({
        id,
        ok: Boolean(result.ok),
        resultFile,
      });
    };

    rl.on(
      'line',
      line => {
        chain = chain
          .then(
            () => handle(line)
          )
          .catch(
            erro => {
              protocolo({
                ok: false,
                erro:
                  erro?.message
                  || String(erro),
              });
            }
          );
      }
    );
  }

  app.whenReady().then(
    async () => {
      if (PERSISTENT) {
        await executarPersistente();
        return;
      }

      await executarUmaVez();
    }
  );
}
