# V59 — Login obrigatório ativado

URL configurada:

https://script.google.com/macros/s/AKfycbzSv0Zxz-EQnFHKPTTtfvAErWt2cL2gPBLryMnMQiOFNv4L14FpgpZVeXWVy3YEVXgW/exec

## Efeito

Depois desta versão:

1. a Central abre;
2. antes da MainWindow, valida token salvo;
3. se não houver token válido, mostra a tela de login;
4. se Proxy Geral estiver ativo, a autenticação usa o proxy;
5. se o usuário for autorizado, a Central abre;
6. as abas são filtradas pelas permissões retornadas pelo Apps Script.

Windows:
- token protegido por DPAPI.

Ubuntu:
- token protegido por Secret Service / Keyring.

## Arquivo SUBSTITUIR

`src/monitor_noticias/auth/config.py`

## Dependência

A V58 precisa já estar aplicada na main.

## WORKFLOW

NÃO PRECISA ALTERAR.

Os workflows Windows e Ubuntu atuais já são disparados por alterações em `src/**`.
