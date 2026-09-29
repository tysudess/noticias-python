# Central V90.1 — Hotfix do pipeline Windows/Ubuntu

Base conferida antes da correção:

`86983e7c92349c78121e47162b4ac38a648c0fe3`

## Log real analisado

Windows:
- workflow `Build e Release Windows Portable`
- run `233`
- job `Gerar portable`
- falha no passo `Validar código e testes unitários`

Ubuntu:
- workflow `Build e Release Ubuntu Portable`
- run `62`
- mesma classe de falhas de testes.

O PyInstaller não chegou a executar.

## Causas

A V89 passou a executar toda a suíte unitária antes do build e revelou testes
antigos que ainda descreviam contratos anteriores:

- fixtures de autenticação sem versão de servidor;
- helper Globoplay assumindo `.exe` também no Linux;
- teste do Editor de Vídeo ainda esperando janela externa;
- teste do Extrator ainda esperando QObject worker separado, embora o código
  atual use QThread autocontida;
- teste de startup usando diretamente um RegistryBackend onde hoje existe
  WindowsStartupBackend;
- teste de notificação esperando a marca antiga "Monitor de Notícias";
- teste de UI dependente do estado visual do checkbox de startup.

Além disso, `.gitignore` não chegou à main.

## Duas correções reais reveladas pela suíte

### Certificado corporativo

`ssl.DER_cert_to_PEM_cert()` apenas converte bytes para PEM e não valida que os
bytes representam um X.509. Agora a Central força o parser OpenSSL usando
`SSLContext.load_verify_locations(cadata=...)`.

Bytes inválidos são rejeitados antes de qualquer bundle CA ser criado.

### Encerramento de subprocessos

`HiddenProcessRunner.destroy_tree()` agora aguarda o processo realmente sair
depois de `taskkill`, SIGTERM/SIGKILL ou `process.kill()`.

Isso evita `shutdown()` retornar enquanto um helper ainda aparece vivo.

## Workflow

Os YAMLs não precisam mudar neste hotfix.

A estratégia correta continua sendo executar a suíte antes do build; o que foi
corrigido foram os contratos/testes e os dois bugs reais encontrados.

**WORKFLOW: NÃO PRECISA ALTERAR**
