# Central Auth — troca obrigatória e alteração de senha

## Atualização da planilha

Depois de substituir `Code.gs`, execute novamente:

`setupCentralAuth`

A aba `USUARIOS` ganhará a coluna:

`TROCAR_SENHA`

Os usuários atuais não são forçados automaticamente a trocar a senha.

## Senha temporária para um novo usuário

Preencha a linha normalmente e coloque a senha inicial em:

`NOVA_SENHA`

Na coluna `TROCAR_SENHA`:

- deixe vazio ou coloque `TRUE` para exigir troca no primeiro acesso;
- coloque `FALSE` se não quiser exigir troca.

Depois use:

`Central Auth -> Processar senhas pendentes`

Se `TROCAR_SENHA` estiver vazio, o processamento passa a gravar `TRUE`.

## Primeiro acesso

Quando `TROCAR_SENHA=TRUE`:

1. o usuário entra com a senha temporária;
2. a Central não abre ainda;
3. aparece `Alteração obrigatória de senha`;
4. o usuário informa a senha temporária novamente;
5. cria e confirma a nova senha;
6. o Apps Script grava novo salt/hash;
7. `TROCAR_SENHA` vira `FALSE`;
8. todas as sessões antigas são revogadas;
9. uma nova sessão é emitida;
10. a Central é liberada.

## Troca voluntária

Depois de entrar, o usuário pode usar:

`Minha conta -> Alterar senha`

ou a opção `Alterar senha` no menu da bandeja.

Ele precisa informar a senha atual antes de criar a nova.

## Regras

- mínimo de 8 caracteres;
- nova senha deve ser diferente da atual;
- confirmação deve coincidir;
- senha em texto puro não é armazenada;
- cada troca gera novo salt/hash;
- sessões anteriores são revogadas.

## IMPORTANTE — atualizar a implantação

Depois de salvar o novo `Code.gs`:

1. `Implantar -> Gerenciar implantações`;
2. abra a implantação atual;
3. clique em editar;
4. escolha `Nova versão`;
5. clique em `Implantar`.

A URL `/exec` pode continuar a mesma.
