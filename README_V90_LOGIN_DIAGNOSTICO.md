# Central V90 — Login mais rápido + Diagnóstico do Sistema

Base conferida antes da alteração:

`2018132683561c396e6dc94e8548212254ec4613`

## 1. Certificação/login

A V88 reduziu custo no cliente desktop e passou a medir o transporte. A revisão
seguinte mostrou que o maior gargalo restante estava no Apps Script.

Na versão anterior, toda validação de token na abertura fazia:

1. `waitLock(20000)` no `ScriptLock`;
2. leitura completa de `SESSOES`;
3. leitura completa de `USUARIOS`;
4. gravação de `ULTIMA_VALIDACAO`;
5. leitura completa de `DISPOSITIVOS`;
6. gravação de `ULTIMO_ACESSO`.

A V90 mantém a validação remota obrigatória ao abrir e continua verificando:

- token;
- dispositivo;
- sessão revogada;
- validade da sessão;
- existência do usuário;
- STATUS ATIVO/BLOQUEADO;
- validade do usuário;
- perfil e permissões;
- TROCAR_SENHA.

### Otimizações do servidor 1.2.0

- `validate` não espera mais até 20 segundos por um lock de escrita;
- busca de token e usuário usa `TextFinder` no lado do Google Sheets;
- mantém fallback compatível para planilhas antigas;
- cache de Spreadsheet/abas/configuração existe somente durante a execução da
  requisição e não mantém autorização entre chamadas;
- `ULTIMA_VALIDACAO`/`ULTIMO_ACESSO` viram heartbeat de auditoria;
- heartbeat só é necessário a cada 15 minutos;
- quando precisa escrever, tenta o lock por apenas 50 ms; se outra operação
  estiver gravando, a autenticação não é atrasada;
- cada POST passa a informar `server_timing_ms` para diagnóstico.

Login com usuário/senha, troca de senha, logout e revogações continuam usando
lock exclusivo porque são operações que realmente alteram o estado de segurança.

## IMPORTANTE — Apps Script

`tools/auth_server/Code.gs` precisa substituir o código da implantação atual.
Depois é necessário criar uma **NOVA versão da implantação do Web App** no
Google Apps Script. Apenas subir o arquivo no GitHub não atualiza o Web App.

O formato das abas e os hashes existentes são compatíveis com a versão anterior;
não é necessário recriar usuários ou senhas.

## 2. Diagnóstico do Sistema

Configurações ganha um card compacto **Diagnóstico do sistema**.

O diálogo testa:

- pastas de dados/logs/temp;
- bancos de notícias e vídeos;
- FFmpeg e FFprobe;
- yt-dlp;
- Deno;
- helper Globoplay;
- motor do Extrator de Notícias;
- cofre seguro de credenciais;
- Proxy Geral, quando ativado;
- GET do Apps Script;
- POST do Apps Script;
- validação real da sessão atual, com tempo em milissegundos;
- espaço livre em disco.

O botão **Gerar ZIP de diagnóstico** cria em Downloads:

`Central-Diagnostico-AAAAMMDD-HHMMSS.zip`

O pacote contém o relatório JSON e cópias sanitizadas dos logs recentes. Senhas,
tokens, Authorization Bearer e credenciais embutidas em URL são mascarados.

## Arquivos para substituir

- `tools/auth_server/Code.gs`
- `src/monitor_noticias/app/application.py`

## Arquivos para adicionar

- `src/monitor_noticias/diagnostics.py`
- `src/monitor_noticias/ui/diagnostics_panel.py`
- `tests/unit/test_v90_auth_server_diagnostics.py`
- `README_V90_LOGIN_DIAGNOSTICO.md`

## Workflow

**WORKFLOW: NÃO PRECISA ALTERAR**

As mudanças desktop estão dentro de `src/**`, já observado pelos workflows.
`Code.gs` é implantado manualmente no Google Apps Script e não faz parte do
Portable.
