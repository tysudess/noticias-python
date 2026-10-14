'use strict';

// V104: bootstrap do worker de extração.
// A interface Electron normal continua no monitor-main.js/main.js. Este arquivo
// só aplica as otimizações quando a Central inicia o extrator em modo headless.
const { app } = require('electron');

const HEADLESS = String(process.env.MONITOR_HEADLESS || '').trim() === '1';
const FAST_MODE = String(process.env.CENTRAL_NEWS_FAST_MODE || '').trim() === '1';

if (!HEADLESS) {
  require('./monitor-main.js');
} else {
  const FAST_TIMEOUT_MS = 8500;
  const HTML_CACHE_LIMIT_BYTES = 5 * 1024 * 1024;
  const htmlCache = new Map();

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
    let parsed;
    try {
      parsed = new URL(rawUrl).toString();
    } catch (_) {
      return null;
    }

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
      if (key && htmlCache.has(key)) {
        console.log('NEWS PERF: reutilizando HTML da mesma URL na extração atual.');
        return responseFromCache(ResponseCtor, htmlCache.get(key));
      }

      const response = await originalFetch(input, init);
      if (!key || !response.ok) return response;

      const contentType = String(response.headers.get('content-type') || '');
      if (!/text\/html|application\/xhtml\+xml/i.test(contentType)) return response;

      const declaredLength = Number(response.headers.get('content-length') || 0);
      if (declaredLength > HTML_CACHE_LIMIT_BYTES) return response;

      try {
        // O motor já precisa ler todo o HTML para analisá-lo. A cópia é lida
        // na mesma passagem e fica disponível para as conferências do portal.
        const body = await response.clone().text();
        if (Buffer.byteLength(body, 'utf8') > HTML_CACHE_LIMIT_BYTES) return response;

        const headers = [...response.headers].filter(([name]) => {
          return !['content-encoding', 'content-length', 'transfer-encoding']
            .includes(String(name).toLowerCase());
        });
        htmlCache.set(key, {
          body,
          status: response.status,
          statusText: response.statusText,
          headers
        });
      } catch (error) {
        console.warn('NEWS PERF: não foi possível armazenar HTML em memória:', error.message);
      }
      return response;
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

    // Reduz apenas as leituras complementares (metadados/conferências). A
    // leitura principal mantém a lógica nativa de retry do motor e o fallback
    // por AMP/portal continua disponível.
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

  function normalizeParagraph(value) {
    return String(value || '')
      .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
      .replace(/\u00a0/g, ' ')
      .replace(/[ \t]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function isStandaloneNoise(paragraph) {
    const value = normalizeParagraph(paragraph);
    if (!value || value.length > 240) return false;
    return (
      /^(?:publicidade|anúncio|anuncio|compartilhe|continue lendo)$/i.test(value)
      || /^(?:leia|veja|confira)\s+(?:também|tambem|mais)\b/i.test(value)
      || /^(?:conteúdos?|matérias?|notícias?)\s+relacionad[oa]s?\b/i.test(value)
      || /^(?:assine|inscreva-se|receba)\s+(?:o|a|os|as|nossa|nosso|nossas|nossos|as notícias|as noticias|a newsletter|nossa newsletter)\b/i.test(value)
      || /^(?:foto|fotos|imagem|imagens|crédito|créditos|credito|creditos)\s*:/i.test(value)
    );
  }

  function cleanArticleBody(text) {
    const original = String(text || '').trim();
    const paragraphs = original
      .split(/\n\s*\n+/)
      .map(normalizeParagraph)
      .filter(Boolean);
    const seen = new Set();
    const clean = [];

    for (const paragraph of paragraphs) {
      if (isStandaloneNoise(paragraph)) continue;
      const key = paragraph.toLocaleLowerCase('pt-BR');
      // Deduplica parágrafos longos repetidos pelo DOM, sem remover nomes,
      // subtítulos curtos ou referências breves que podem aparecer de novo.
      if (paragraph.length >= 70 && seen.has(key)) continue;
      if (paragraph.length >= 70) seen.add(key);
      clean.push(paragraph);
    }
    return clean.join('\n\n').trim();
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

  installNetworkOptimizations();

  // Carrega o motor depois de instalar o wrapper de rede, para que Undici seja
  // importado já com a otimização. A referência mutada é reutilizada pelo
  // monitor-main.js quando ele é exigido abaixo.
  const motor = require('./engine/extrator-materia-v1.25.10-runtime.js');
  installQualityGuards(motor);

  console.log(
    `NEWS PERF V104: fastMode=${FAST_MODE}; timeout por requisição=${FAST_MODE ? FAST_TIMEOUT_MS : 'padrão'}ms; cache HTML de curta duração ativo.`
  );

  // Reutiliza o caminho existente para proxy, saída JSON, histórico e timeout.
  // O processo permanece one-shot, evitando a regressão antiga do worker stdin.
  require('./monitor-main.js');
}
