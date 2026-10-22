'use strict';

// V108: bootstrap do worker de extração rápida e com limpeza de legendas.
// A interface Electron normal continua no monitor-main.js/main.js. Este arquivo
// só aplica as otimizações quando a Central inicia o extrator em modo headless.
const { app } = require('electron');

const HEADLESS = String(process.env.MONITOR_HEADLESS || '').trim() === '1';
const FAST_MODE = String(process.env.CENTRAL_NEWS_FAST_MODE || '').trim() === '1';

if (!HEADLESS) {
  require('./monitor-main.js');
} else {
  const { cleanArticleBody, installCaptionSanitizer } = require('./article-quality.js');

  const FAST_TIMEOUT_MS = 8500;
  const HTML_CACHE_LIMIT_BYTES = 5 * 1024 * 1024;
  const FAST_NETWORK_MAX_ATTEMPTS = 2;
  const htmlCache = new Map();
  const fastRequestAttempts = new Map();

  function timeoutFor(ms) {
    const requested = Number(ms);
    return Math.max(
      1000,
      Math.min(
        Number.isFinite(requested) && requested > 0
          ? requested
          : FAST_TIMEOUT_MS,
        FAST_TIMEOUT_MS
      )
    );
  }

  function readHeader(headers, wanted) {
    if (!headers) return '';
    if (typeof headers.get === 'function') {
      return String(headers.get(wanted) || '');
    }
    const match = Object.entries(headers).find(
      ([key]) => String(key).toLowerCase() === wanted.toLowerCase()
    );
    return match ? String(match[1] || '') : '';
  }

  function htmlCacheKey(input, init = {}) {
    const rawUrl = typeof input === 'string'
      ? input
      : String(input && input.url ? input.url : input);
    let parsedUrl;
    try {
      parsedUrl = new URL(rawUrl);
    } catch (_) {
      return null;
    }

    // Só o G1 tem uma segunda leitura conhecida da mesma URL para completar
    // parágrafos. Em outros portais, cachear toda página custa mais do que ajuda.
    if (parsedUrl.hostname.toLowerCase() !== 'g1.globo.com') return null;
    const parsed = parsedUrl.toString();

    const method = String(
      init.method || (input && input.method) || 'GET'
    ).toUpperCase();
    if (method !== 'GET' || init.body) return null;

    const headers = init.headers || (input && input.headers);
    const accept = readHeader(headers, 'accept');
    const userAgent = readHeader(headers, 'user-agent');
    if (!/text\/html|application\/xhtml\+xml/i.test(accept)) return null;

    return `${method}\n${parsed}\n${accept}`;
  }

  function responseFromCache(ResponseCtor, item) {
    return new ResponseCtor(item.body, {
      status: item.status,
      statusText: item.statusText,
      headers: item.headers
    });
  }

  function fastRequestKey(input) {
    const rawUrl = typeof input === 'string'
      ? input
      : String(input && input.url ? input.url : input);
    try {
      return new URL(rawUrl).toString();
    } catch (_) {
      return null;
    }
  }

  function fastRetryLimitError() {
    // Não replica a mensagem de erro transitório original: isso faz o motor
    // encerrar o ciclo de retry de forma deliberada no modo rápido.
    return new Error(
      'Modo rápido: limite de duas tentativas atingido para este endereço. Tente novamente se a rede estiver instável.'
    );
  }

  function installNetworkOptimizations() {
    const undici = require('undici');
    const originalFetch = undici.fetch;
    const ResponseCtor = undici.Response;

    if (typeof originalFetch !== 'function' || typeof ResponseCtor !== 'function') {
      console.warn('NEWS PERF: cache HTML indisponível; usando Undici original.');
      return;
    }

    const optimizedFetch = async function centralNewsOptimizedFetch(input, init = {}) {
      const key = htmlCacheKey(input, init);
      const requestKey = fastRequestKey(input);
      if (key && htmlCache.has(key)) {
        console.log('NEWS PERF: reutilizando HTML da mesma URL na extração atual.');
        return responseFromCache(ResponseCtor, htmlCache.get(key));
      }

      let response;
      try {
        response = await originalFetch(input, init);
      } catch (error) {
        if (!FAST_MODE || !requestKey) throw error;
        const attempts = (fastRequestAttempts.get(requestKey) || 0) + 1;
        if (attempts >= FAST_NETWORK_MAX_ATTEMPTS) {
          fastRequestAttempts.delete(requestKey);
          console.warn('NEWS PERF: retry encerrado pelo limite rápido de tentativas.');
          throw fastRetryLimitError();
        }
        fastRequestAttempts.set(requestKey, attempts);
        throw error;
      }

      if (FAST_MODE && requestKey) {
        if ([502, 503, 504].includes(response.status)) {
          const attempts = (fastRequestAttempts.get(requestKey) || 0) + 1;
          if (attempts >= FAST_NETWORK_MAX_ATTEMPTS) {
            fastRequestAttempts.delete(requestKey);
            try { await response.body?.cancel(); } catch (_) {}
            console.warn(`NEWS PERF: retry encerrado após HTTP ${response.status} repetido.`);
            throw new Error(
              `Modo rápido: o portal respondeu HTTP ${response.status} em duas tentativas.`
            );
          }
          fastRequestAttempts.set(requestKey, attempts);
        } else if (!response.ok) {
          fastRequestAttempts.delete(requestKey);
        }
      }

      if (!key || !response.ok) {
        const retryableHttp = [502, 503, 504].includes(response.status);
        if (FAST_MODE && requestKey && !retryableHttp) {
          fastRequestAttempts.delete(requestKey);
        }
        return response;
      }

      const contentType = String(response.headers.get('content-type') || '');
      if (!/text\/html|application\/xhtml\+xml/i.test(contentType)) {
        if (FAST_MODE && requestKey) fastRequestAttempts.delete(requestKey);
        return response;
      }

      const declaredLengthHeader = response.headers.get('content-length');
      const declaredLength = Number(declaredLengthHeader || 0);
      // Não duplicamos corpos grandes ou sem tamanho declarado: a cópia
      // especulativa de HTML sem chance clara de cache só encarece a extração.
      if (!declaredLengthHeader || !Number.isFinite(declaredLength)
        || declaredLength <= 0 || declaredLength > HTML_CACHE_LIMIT_BYTES) {
        if (FAST_MODE && requestKey) fastRequestAttempts.delete(requestKey);
        return response;
      }
      if (response.headers.has('set-cookie')) {
        if (FAST_MODE && requestKey) fastRequestAttempts.delete(requestKey);
        return response;
      }

      try {
        // Lê o fluxo uma única vez e reconstrói uma resposta em memória. Isso
        // evita o tee de response.clone(), que mantinha duas cópias do corpo
        // aguardando consumo. O cache é usado somente se o HTML for pequeno.
        const body = await response.text();
        const size = Buffer.byteLength(body, 'utf8');
        const headers = [...response.headers].filter(([name]) => {
          return !['content-encoding', 'content-length', 'transfer-encoding']
            .includes(String(name).toLowerCase());
        });
        const buffered = {
          body,
          status: response.status,
          statusText: response.statusText,
          headers
        };
        if (size <= HTML_CACHE_LIMIT_BYTES) htmlCache.set(key, buffered);
        if (FAST_MODE && requestKey) fastRequestAttempts.delete(requestKey);
        const replay = responseFromCache(ResponseCtor, buffered);
        try {
          Object.defineProperty(replay, 'url', { value: response.url });
          Object.defineProperty(replay, 'redirected', { value: response.redirected });
        } catch (_) {}
        return replay;
      } catch (error) {
        console.warn('NEWS PERF: leitura do HTML falhou durante o buffer curto:', error.message);
        if (!FAST_MODE || !requestKey) throw error;
        const attempts = (fastRequestAttempts.get(requestKey) || 0) + 1;
        if (attempts >= FAST_NETWORK_MAX_ATTEMPTS) {
          fastRequestAttempts.delete(requestKey);
          throw fastRetryLimitError();
        }
        fastRequestAttempts.set(requestKey, attempts);
        throw error;
      }
    };

    try {
      Object.defineProperty(undici, 'fetch', {
        value: optimizedFetch,
        configurable: true,
        enumerable: true,
        writable: true
      });
    } catch (error) {
      console.warn('NEWS PERF: não foi possível ativar cache HTML:', error.message);
    }

    if (FAST_MODE && typeof AbortSignal !== 'undefined'
      && typeof AbortSignal.timeout === 'function') {
      const nativeTimeout = AbortSignal.timeout.bind(AbortSignal);
      AbortSignal.timeout = function centralNewsFastTimeout(ms) {
        return nativeTimeout(timeoutFor(ms));
      };
    }

    // Mantém o limite na função exportada para chamadas diretas. A extração
    // principal também recebe o limite no fetch real acima, pois a função
    // extrairMateria mantém uma referência lexical à rotina original.
    if (FAST_MODE) {
      try {
        const core = require('./engine/extrator-materia-v1.25.1.js');
        if (typeof core.fetchComRetry === 'function'
          && !core.fetchComRetry._centralV104Fast) {
          const originalFetchWithRetry = core.fetchComRetry;
          const limitedFetchWithRetry = function (url, options = {}, config = {}) {
            const timeout = Math.max(
              5000,
              Number(config.timeoutMs) || FAST_TIMEOUT_MS
            );
            const retries = Math.max(
              1,
              Number(config.tentativas) || 3
            );
            return originalFetchWithRetry(url, options, {
              ...config,
              timeoutMs: Math.min(timeout, FAST_TIMEOUT_MS),
              tentativas: Math.min(retries, 2)
            });
          };
          limitedFetchWithRetry._centralV104Fast = true;
          core.fetchComRetry = limitedFetchWithRetry;
        }
      } catch (error) {
        console.warn('NEWS PERF: não foi possível limitar leituras complementares:', error.message);
      }
    }
  }

  function reformatArticle(materia) {
    const parts = [
      String(materia.url || ''),
      '',
      String(materia.veiculo || ''),
      '',
      `*${String(materia.titulo || 'Título não identificado')}*`
    ];
    if (materia.subtitulo) parts.push('', `_${String(materia.subtitulo)}_`);
    parts.push('');
    if (materia.autor) parts.push(String(materia.autor));
    parts.push(String(materia.data || 'Data não identificada'), '', String(materia.texto || ''));
    materia.resultado = parts.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
    return materia;
  }

  function isUol(url) {
    try {
      const hostname = new URL(url).hostname.toLowerCase();
      return hostname === 'uol.com.br' || hostname.endsWith('.uol.com.br');
    } catch (_) {
      return false;
    }
  }

  function installQualityGuards(motor) {
    const originalExtract = motor.extrairMateria;
    if (typeof originalExtract !== 'function' || originalExtract._centralV104Quality) return;

    const guardedExtract = async function centralNewsQualityExtract(url) {
      const materia = await originalExtract.call(motor, url);
      if (!materia || !materia.texto) {
        throw new Error('O site não disponibilizou o corpo da matéria. Confira o link original.');
      }

      const oldText = String(materia.texto || '').trim();
      const cleanedText = cleanArticleBody(oldText);
      const paragraphs = cleanedText.split(/\n\s*\n+/).filter(Boolean);
      const changed = cleanedText !== oldText;
      if (changed) {
        materia.texto = cleanedText;
        reformatArticle(materia);
      }

      if (cleanedText.length < 180) {
        throw new Error(
          'O site retornou somente um trecho muito curto. A Central não vai apresentar esse trecho como matéria completa; confira o acesso e tente novamente.'
        );
      }

      // A regra de completude já existente no motor V1.25.20 identifica páginas
      // UOL em que o corpo parece um preview. Não declara sucesso silencioso
      // nesses casos quando o texto ainda está claramente abaixo do esperado.
      const aviso = String(materia.avisoCompletude || '').trim();
      if (aviso && isUol(materia.url || url)
        && (cleanedText.length < 1100 || paragraphs.length < 4)) {
        throw new Error(aviso);
      }

      if (cleanedText.length < 350) {
        console.warn('NEWS QUALITY: texto curto; revisar antes de utilizar.');
      }
      return materia;
    };
    guardedExtract._centralV104Quality = true;
    motor.extrairMateria = guardedExtract;
  }

  // A limpeza deve ser instalada antes de qualquer módulo do motor importar
  // JSDOM e executar o Readability sobre a página original.
  installCaptionSanitizer();
  installNetworkOptimizations();

  // Carrega o motor depois de instalar o wrapper de rede, para que Undici seja
  // importado já com a otimização. A referência mutada é reutilizada pelo
  // monitor-main.js quando ele é exigido abaixo.
  const motor = require('./engine/extrator-materia-v1.25.10-runtime.js');
  installQualityGuards(motor);

  console.log(
    `NEWS PERF V108: fastMode=${FAST_MODE}; timeout por requisição=${FAST_MODE ? FAST_TIMEOUT_MS : 'padrão'}ms; no máximo ${FAST_NETWORK_MAX_ATTEMPTS} tentativas por URL no modo rápido; cache HTML temporário restrito ao G1.`
  );

  // Reutiliza o caminho existente para proxy, saída JSON, histórico e timeout.
  // O processo permanece one-shot, evitando a regressão antiga do worker stdin.
  require('./monitor-main.js');
}
