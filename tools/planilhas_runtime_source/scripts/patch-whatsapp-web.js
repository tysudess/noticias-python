const fs = require("fs");
const path = require("path");

const target = path.join(
  __dirname,
  "..",
  "node_modules",
  "whatsapp-web.js",
  "src",
  "Client.js"
);

if (!fs.existsSync(target)) {
  throw new Error(
    `Client.js do whatsapp-web.js não encontrado: ${target}`
  );
}

let source = fs.readFileSync(target, "utf8");
const original = source;

function replaceOnce(oldText, newText, label) {
  if (!source.includes(oldText)) {
    throw new Error(
      `Patch incompatível: trecho não encontrado (${label}).`
    );
  }

  source = source.replace(oldText, newText);
}

// 1) O polling com page.evaluate() morre quando o WhatsApp Web navega.
// waitForFunction() é ligado ao mecanismo WaitTask do Puppeteer e é
// reexecutado quando um novo execution context é criado.
replaceOnce(
`        if (
            this.options.authTimeoutMs === undefined ||
            this.options.authTimeoutMs == 0
        ) {
            this.options.authTimeoutMs = 30000;
        }
        let start = Date.now();
        let timeout = this.options.authTimeoutMs;
        let res = false;
        while (start > Date.now() - timeout) {
            res = await this.pupPage.evaluate(
                'window.Debug?.VERSION != undefined',
            );
            if (res) {
                break;
            }
            await new Promise((r) => setTimeout(r, 200));
        }
        if (!res) {
            throw 'auth timeout';
        }`,
`        if (
            this.options.authTimeoutMs === undefined ||
            this.options.authTimeoutMs == 0
        ) {
            this.options.authTimeoutMs = 90000;
        }

        try {
            await this.pupPage.waitForFunction(
                'window.Debug?.VERSION != undefined',
                {
                    timeout: this.options.authTimeoutMs,
                    polling: 200,
                },
            );
        } catch (_) {
            throw 'auth timeout';
        }`,
  "auth waitForFunction"
);

// 2) Mesmo problema no segundo polling, depois que LoadUtils é injetado.
replaceOnce(
`                    let start = Date.now();
                    let res = false;
                    while (start > Date.now() - 30000) {
                        // Check window.WWebJS Injection
                        res = await this.pupPage.evaluate(
                            'window.WWebJS != undefined',
                        );
                        if (res) {
                            break;
                        }
                        await new Promise((r) => setTimeout(r, 200));
                    }
                    if (!res) {
                        throw 'ready timeout';
                    }`,
`                    try {
                        await this.pupPage.waitForFunction(
                            'window.WWebJS != undefined',
                            {
                                timeout: 60000,
                                polling: 200,
                            },
                        );
                    } catch (_) {
                        throw 'ready timeout';
                    }`,
  "ready waitForFunction"
);

// 3) Registra a recuperação de navegação ANTES do inject inicial.
// Também protege o callback contra navegação concorrente.
replaceOnce(
`        await this.inject();

        this.pupPage.on('framenavigated', async (frame) => {
            if (frame.url().includes('post_logout=1') || this.lastLoggedOut) {
                this.emit(Events.DISCONNECTED, 'LOGOUT');
                await this.authStrategy.logout();
                await this.authStrategy.beforeBrowserInitialized();
                await this.authStrategy.afterBrowserInitialized();
                this.lastLoggedOut = false;
            }
            await this.inject();
        });`,
`        let reinjectingAfterNavigation = false;

        this.pupPage.on('framenavigated', async (frame) => {
            if (frame !== this.pupPage.mainFrame()) {
                return;
            }

            if (frame.url().includes('post_logout=1') || this.lastLoggedOut) {
                this.emit(Events.DISCONNECTED, 'LOGOUT');
                await this.authStrategy.logout();
                await this.authStrategy.beforeBrowserInitialized();
                await this.authStrategy.afterBrowserInitialized();
                this.lastLoggedOut = false;
            }

            if (reinjectingAfterNavigation) {
                return;
            }

            reinjectingAfterNavigation = true;

            try {
                await this.inject();
            } catch (err) {
                const message = String(err?.message || err || '');

                if (
                    !message.includes('Execution context was destroyed') &&
                    !message.includes('Cannot find context') &&
                    !message.includes('navigat')
                ) {
                    throw err;
                }
            } finally {
                reinjectingAfterNavigation = false;
            }
        });

        let lastInjectError = null;

        for (let attempt = 1; attempt <= 5; attempt += 1) {
            try {
                await this.inject();
                lastInjectError = null;
                break;
            } catch (err) {
                lastInjectError = err;

                const message = String(err?.message || err || '');

                const navigationError =
                    message.includes('Execution context was destroyed') ||
                    message.includes('Cannot find context') ||
                    message.includes('navigat');

                if (!navigationError || attempt >= 5) {
                    throw err;
                }

                await new Promise((resolve) =>
                    setTimeout(resolve, 600 + attempt * 350),
                );
            }
        }

        if (lastInjectError) {
            throw lastInjectError;
        }`,
  "navigation recovery"
);

if (source === original) {
  throw new Error("Nenhuma alteração foi aplicada.");
}

fs.writeFileSync(target, source, "utf8");

console.log(
  "whatsapp-web.js Client.js corrigido para sobreviver à navegação interna."
);
