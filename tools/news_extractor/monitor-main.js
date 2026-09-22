const { app } = require('electron');
const fs = require('fs');
const path = require('path');

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

  const PASTA_NOME = 'ExtratorMaterias';
  const ARQUIVO_ULTIMO =
    'materia-extraida.txt';
  const ARQUIVO_HISTORICO =
    'materias-extraidas.txt';
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
      String(
        materia.resultado || ''
      ),
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
          String(
            materia.resultado || ''
          )
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
      TIMEOUT_MS: 45000,
      CERTIFICADO_CA: ''
    };

    if (
      !fs.existsSync(
        configFile
      )
    ) {
      return padrao;
    }

    try {
      return {
        ...padrao,
        ...JSON.parse(
          fs.readFileSync(
            configFile,
            'utf8'
          ).replace(
            /^\uFEFF/,
            ''
          )
        )
      };
    } catch (_) {
      return padrao;
    }
  }

  function prepararRede() {
    const config =
      carregarConfigBase();

    // Quando o processo foi iniciado pelo Central, a configuração do
    // Proxy Geral tem prioridade absoluta sobre o config-proxy.json local.
    if (
      CENTRAL_PROXY_PRESENT
    ) {
      if (
        !CENTRAL_PROXY_ENABLED
      ) {
        motor.prepararProxy(
          '',
          '',
          {
            ...config,
            ATIVADO: false
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
            CENTRAL_PROXY_PORT
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

    // Fora do Central preserva o comportamento anterior do executável.
    motor.prepararProxy(
      '',
      '',
      {
        ...config,
        ATIVADO: false
      }
    );

    console.log(
      'REDE: conexão direta (fora do Central)'
    );
  }

  async function executar() {
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

      prepararRede();

      const materia =
        await motor.extrairMateria(
          URL
        );

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

      result = {
        ok: true,
        formatado:
          materia.resultado,
        url:
          materia.url,
        veiculo:
          materia.veiculo,
        titulo:
          materia.titulo,
        subtitulo:
          materia.subtitulo,
        autor:
          materia.autor,
        data:
          materia.data,
        corpoCaracteres:
          String(
            materia.texto || ''
          ).length,
        versaoMotor:
          motor.VERSAO,
        rede:
          CENTRAL_PROXY_PRESENT
            ? (
              CENTRAL_PROXY_ENABLED
                ? 'proxy-central'
                : 'direta-central'
            )
            : 'direta-standalone'
      };

    } catch (erro) {
      result = {
        ok: false,
        erro:
          erro?.message
          || String(erro)
      };
    }

    try {
      fs.mkdirSync(
        path.dirname(
          RESULT_FILE
        ),
        { recursive: true }
      );

      fs.writeFileSync(
        RESULT_FILE,
        JSON.stringify(
          result,
          null,
          2
        ),
        'utf8'
      );
    } catch (_) {}

    app.quit();
  }

  app.whenReady().then(
    executar
  );
}
