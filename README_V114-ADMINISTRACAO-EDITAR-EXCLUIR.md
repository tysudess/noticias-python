# Central V114 — Editar e excluir usuários na Administração

## Base confirmada
Repositório `tysudess/noticias-python`, branch `main`, commit `78020b61f19e6a3a6f89e546399e24e27b516bb3` (22/10/2026).

## O que muda
Na aba Administração, ao lado de “Atualizar usuários”, aparecem os botões **Editar usuário** e **Excluir usuário**. É necessário selecionar uma conta na tabela. A edição permite mudar nome, perfil, situação, validade, limite de dispositivos e permissões. O identificador/login permanece imutável para não quebrar vínculos com sessões e dispositivos.

A exclusão remove a conta da aba USUARIOS, revoga sessões antigas, desativa os dispositivos registrados e preserva os registros de auditoria.

## Proteções
- Todas as operações continuam exigindo sessão ADMIN, validada novamente pelo Apps Script no servidor.
- Não permite editar ou excluir a conta que está usando a sessão administrativa atual.
- Não permite desativar, rebaixar ou excluir o último administrador ativo.
- Edição/exclusão exige confirmação na interface; a exclusão é permanente.
- Alterações revogam as sessões do usuário para que permissões e situação antigas não continuem valendo.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/app/composition.py`
- `src/monitor_noticias/auth/admin_api.py`

### ADICIONAR
- `src/monitor_noticias/ui/admin_user_management_patch.py`
- `tools/auth_server/apply_admin_users_v114_patch.py`
- `tests/unit/test_v114_admin_user_management.py`
- `README_V114-ADMINISTRACAO-EDITAR-EXCLUIR.md`

### Atualização obrigatória do Apps Script
O pacote não altera o projeto remoto do Apps Script automaticamente. Depois de extrair o ZIP para a raiz do repositório:

1. Execute na raiz: `python tools/auth_server/apply_admin_users_v114_patch.py`
2. Confira a alteração gerada em `tools/auth_server/Code.gs` com `git diff -- tools/auth_server/Code.gs`.
3. Atualize o conteúdo do projeto do Apps Script usando esse `Code.gs`, salve e publique uma **nova versão** da implantação do Web App. A operação não funciona enquanto a URL configurada continuar servindo o código antigo.
4. Só então reconstrua e teste os portables Windows e Ubuntu.

## Workflow
**WORKFLOW: NÃO PRECISA ALTERAR.** A alteração de `src/**` já aciona os builds Windows e Ubuntu. A publicação do Apps Script é uma etapa separada e manual.

## Testes
Foram adicionados testes unitários para os payloads, patch idempotente do Code.gs, proteções contra autoexclusão/último administrador e presença dos controles na tela. O build real e a chamada ao servidor publicado ainda precisam ser testados após a implantação.
