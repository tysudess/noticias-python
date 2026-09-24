# V61 — Correção da troca obrigatória de senha no primeiro acesso

## Erro corrigido

Na V60 havia uma inconsistência: senha processada com TROCAR_SENHA vazio virava TRUE, mas o login interpretava o mesmo campo vazio como FALSE para usuários já existentes.

## Correções

- TROCAR_SENHA vazio + senha configurada agora significa TRUE.
- setupCentralAuth() migra usuários existentes com senha e flag vazia para TRUE.
- Toda senha definida pelo administrador via NOVA_SENHA passa a ser temporária e marca TROCAR_SENHA=TRUE.
- Apps Script sobe para versão 1.1.1.
- Central recusa implantação antiga em vez de liberar silenciosamente.
- Testar conexão passa a mostrar a versão publicada do servidor.

## SUBSTITUIR

- tools/auth_server/Code.gs
- src/monitor_noticias/auth/client.py

## NOVO

- tests/unit/test_auth_password_force_v61.py

## PASSOS NO APPS SCRIPT

1. Substitua Code.gs.
2. Execute setupCentralAuth() uma vez.
3. Confira TROCAR_SENHA = TRUE para o usuário.
4. Implante -> Gerenciar implantações -> Editar -> Nova versão -> Implantar.
5. A URL /exec permanece a mesma.

Depois, em Testar conexão com servidor, deve aparecer versão 1.1.1.

## WORKFLOW

NÃO PRECISA ALTERAR.
