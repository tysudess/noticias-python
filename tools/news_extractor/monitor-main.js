const { app } = require('electron');
const fs = require('fs');
const path = require('path');

const headless =
  String(process.env.MONITOR_HEADLESS || '').trim() === '1';

if (!headless) {
  require('./main.js');
} else {
  const motor = require(
    './engine/extrator-materia-v1.25.10-runtime.js'
  );

  const RESULT_FILE =
    String(process.env.MONITOR_RESULT_FILE || '').trim();

  const URL =
    String(process.env.MONITOR_NEWS_URL || '').trim();

  const CENTRAL_PROXY_PRESENT =
    Object.prototype.hasOwnProperty.call(
      process.env,
      'CENTRAL_PROXY_ENABLED'
    );

  const CENTRAL_PROXY_ENABLED =
    process.env.CENTRAL_PROXY_ENABLED === '1';

  const CENTRAL_PROXY_HOST =
    String(process.env.CENTRAL_PROXY_HOST || '').trim();

  const CENTRAL_PROXY_PORT =
    String(process.env.CENTRAL_PROXY_PORT || '').trim();

  const CENTRAL_PROXY_USERNAME =
    String(process.env.CENTRAL_PROXY_USERNAME || '').trim();

  const CENTRAL_PROXY_PASSWORD =
    String(process.env.CENTRAL_PROXY_PASSWORD || '');

  const FAST_MODE =
    String(process.env.CENTRAL_NEWS_FAST_MODE || '').trim() === '1';

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

  const BLOCK_IMAGES =
    String(process.env.CENTRAL_NEWS_BLOCK_IMAGES || '').trim() === '1';

  const BLOCK_MEDIA =
    String(process.env.CENTRAL_NEWS_BLOCK_MEDIA || '').trim() === '1';

  const HARD_TIMEOUT_MS =
    Math.max(
      15000,
      Math.min(
        90000,
        Number.parseInt(
          process.env.CENTRAL_NEWS_HARD_TIMEOUT_MS || '',
          10
        )
        || (FAST_MODE ? 38000 : 65000)
      )
    );

  const PASTA_NOME = 'ExtratorMaterias';
  const ARQUIVO_ULTIMO = 'materia-extraida.txt';
  const ARQUIVO_HISTORICO = 'materias-extraidas.txt';
  const SEPARADOR =
    '\n' + '#'.repeat(70) + '\n\n';

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
      const repetida =
        motor.historicoContemUrl(
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
      TIMEOUT_MS:
        FAST_MODE
          ? 25000
          : 45000,
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
      const arquivo = JSON.parse(
        fs
          .readFileSync(
            configFile,
            'utf8'
          )
          .replace(/^\uFEFF/, '')
      );

      return {
        ...padrao,
        ...arquivo,
        // Em modo rápido o config histórico não pode elevar novamente
        // o teto para 45 s.
        TIMEOUT_MS:
          FAST_MODE
            ? Math.min(
                25000,
                Number(arquivo.TIMEOUT_MS)
                  || 25000
              )
            : (
                Number(arquivo.TIMEOUT_MS)
                || 45000
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
    const config =
      carregarConfigBase();

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

        console.log(
          'REDE: configuração recebida do Proxy Geral do Central'
        );
        console.log(
          'PROXY: DESATIVADO'
        );
        return;
      }

      if (
        !CENTRAL_PROXY_HOST
        || !CENTRAL_PROXY_PORT
      ) {
        throw new Error(
          'Proxy Geral do Central está ativo, '
          + 'mas servidor/porta não foram informados.'
        );
      }

      if (
        !CENTRAL_PROXY_USERNAME
        || !CENTRAL_PROXY_PASSWORD
      ) {
        throw new Error(
          'Proxy Geral do Central está ativo, '
          + 'mas usuário/senha não foram informados.'
        );
      }

      motor.prepararProxy(
        CENTRAL_PROXY_USERNAME,
        CENTRAL_PROXY_PASSWORD,
        {
          ...config,
          ATIVADO: true,
          SERVIDOR:
            CENTRAL_PROXY_HOST,
          PORTA:
            CENTRAL_PROXY_PORT,
        }
      );

      console.log(
        'REDE: configuração recebida do Proxy Geral do Central'
      );
      console.log(
        `PROXY ATIVO: ${CENTRAL_PROXY_HOST}:${CENTRAL_PROXY_PORT}`
      );
      console.log(
        'PROXY COM AUTENTICAÇÃO CONFIGURADA'
      );
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

    console.log(
      'REDE: conexão direta (fora do Central)'
    );
  }

  function timeoutPromise(ms) {
    return new Promise(
      (_resolve, reject) => {
        const timer = setTimeout(
          () => reject(
            new Error(
              `Tempo limite da extração atingido (${Math.round(ms / 1000)} s).`
            )
          ),
          ms
        );

        // Não mantém o processo vivo somente por causa do timer.
        if (
          timer
          && typeof timer.unref === 'function'
        ) {
          timer.unref();
        }
      }
    );
  }

  function pontuarMateria(materia) {
    if (!materia) {
      return 0;
    }

    const titulo =
      String(materia.titulo || '').trim();

    const texto =
      String(materia.texto || '').trim();

    let score = 0;

    if (titulo.length >= 8) score += 20;
    if (titulo.length >= 25) score += 5;
    if (texto.length >= 350) score += 20;
    if (texto.length >= 700) score += 20;
    if (texto.length >= 1400) score += 20;
    if (texto.length >= 2600) score += 10;

    return score;
  }

  function gravarResultadoAtomico(
    resultFile,
    result
  ) {
    const target =
      String(resultFile || '').trim();

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
    } catch (_) {
      try {
        fs.unlinkSync(target);
      } catch (_) {}

      fs.renameSync(
        tmp,
        target
      );
    }
  }

  async function executar() {
    const started =
      Date.now();

    let result;

    try {
      if (!RESULT_FILE) {
        throw new Error(
          'MONITOR_RESULT_FILE não informado.'
        );
      }

      if (!URL) {
        throw new Error(
          'MONITOR_NEWS_URL não informado.'
        );
      }

      if (!/^https?:\/\//i.test(URL)) {
        throw new Error(
          'O link precisa começar com http:// ou https://.'
        );
      }

      prepararRede();

      console.log(
        `EXTRAÇÃO: modo ${FAST_MODE ? 'rápido' : 'padrão'}`
      );

      // Uma única leitura. O próprio motor já possui retry interno de rede.
      // Evitamos repetir a matéria inteira e dobrar/triplicar o tempo.
      const materia =
        await Promise.race([
          motor.extrairMateria(URL),
          timeoutPromise(HARD_TIMEOUT_MS),
        ]);

      if (
        !materia
        || !materia.resultado
        || !materia.texto
      ) {
        throw new Error(
          'O motor não retornou o corpo completo da matéria.'
        );
      }

      salvarResultado(
        materia
      );

      const bodyLength =
        String(
          materia.texto || ''
        ).length;

      result = {
        ok: true,
        formatado: materia.resultado,
        url: materia.url,
        veiculo: materia.veiculo,
        titulo: materia.titulo,
        subtitulo: materia.subtitulo,
        autor: materia.autor,
        data: materia.data,
        corpoCaracteres:
          bodyLength,
        versaoMotor:
          motor.VERSAO,
        rede:
          CENTRAL_PROXY_PRESENT
            ? (
                CENTRAL_PROXY_ENABLED
                  ? 'proxy-central'
                  : 'direta-central'
              )
            : 'direta-standalone',
        modoRapido:
          FAST_MODE,
        qualidadeScore:
          pontuarMateria(materia),
        qualidadeAviso:
          bodyLength < 350
            ? 'O corpo extraído ficou curto; revise antes de usar.'
            : '',
        duracaoMs:
          Date.now() - started,
      };

    } catch (erro) {
      result = {
        ok: false,
        erro:
          erro?.message
          || String(erro),
        duracaoMs:
          Date.now() - started,
      };
    }

    try {
      gravarResultadoAtomico(
        RESULT_FILE,
        result
      );
    } catch (_) {}

    // O processo é one-shot. Força saída mesmo se Undici ainda mantiver
    // sockets/handles pendentes depois de um timeout.
    setImmediate(
      () => app.exit(0)
    );
  }

  app
    .whenReady()
    .then(executar);
}
