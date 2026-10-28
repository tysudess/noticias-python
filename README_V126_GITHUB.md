# V126 — Diagnóstico seguro de falha na leitura da sessão

## Base conferida
- Repositório: `tysudess/noticias-python`
- `main` usada como base: commit `8b38137ff418a7053fbb5fa7d75eabcd176b1b50` (V125)
- Arquivo de produção: `src/monitor_noticias/auth/storage.py`

## Arquivos do ZIP

**SUBSTITUIR** no repositório:
- `src/monitor_noticias/auth/storage.py`

**ADICIONAR** ao repositório:
- `tests/unit/test_v126_auth_storage_diagnostics.py`

Este README serve como instrução de aplicação e pode ficar fora do repositório.

## O que muda
- Quando o cofre seguro falha ao ler o token, registra a classe da exceção (por exemplo, `CredentialStoreUnavailable`), permitindo identificar falhas de infraestrutura sem expor o texto original da exceção.
- Mantém o retorno atual de texto vazio em caso de erro e mantém os registros de duração da leitura lenta adicionados na V125.
- Não grava nem registra token, senha, mensagem original da exceção ou caminho do cofre.
- Adiciona teste que verifica a mensagem de diagnóstico e comprova que texto sensível vindo da exceção não é registrado.

## Workflows
Não alterar os workflows. A mudança de produção está em `src/**`, já coberto pelos triggers existentes.

## Aplicação
A V125 está integrada no commit `8b38137`. No momento da preparação, os workflows Windows e Ubuntu desse commit ainda estavam construindo os pacotes finais. Aguarde ambos terminarem antes de publicar esta V126, pois uma nova execução pode cancelar builds em andamento.

Nenhum commit ou push foi feito por esta preparação.
