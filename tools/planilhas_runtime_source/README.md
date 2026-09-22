# Automação Planilhas — Windows Portable

Interface Windows para o motor WhatsApp → Google Planilhas.

## v1.1.2

- Proxy corporativo configurável dentro do programa.
- Servidor padrão: `proxy-7dn.mb:6060`.
- Usuário e senha do proxy configuráveis localmente.
- Autenticação do proxy aplicada ao WhatsApp Web pelo `whatsapp-web.js`.
- Proxy também aplicado ao envio para o Apps Script.
- Botão **TESTAR PROXY** na tela de configurações.
- Status do proxy exibido no painel.
- Reconexão automática do WhatsApp Web.
- Recuperação automática do motor após encerramento inesperado.
- Detecção persistente de mensagens duplicadas, gravada somente após processamento bem-sucedido.
- Contador de erros e última linha registrada no painel.
- Seleção automática da aba mensal pela data da matéria.
- Chrome executado oculto em segundo plano.
- Mantém as regras atuais de notícias, vídeos, análise e assunto.

## Configuração do proxy

Abra **Configurações → Proxy** e informe:

- Servidor: `proxy-7dn.mb`
- Porta: `6060`
- Usuário: fornecido pelo ambiente de rede, quando necessário
- Senha: fornecida pelo ambiente de rede, quando necessário

Depois clique em **TESTAR PROXY**. Se o teste for aprovado, clique em **SALVAR CONFIGURAÇÕES** e inicie o motor.

As credenciais são salvas somente no `config.json` local da instalação. Elas não devem ser adicionadas ao repositório GitHub.

## Uso

1. Baixe o `.exe` da Release.
2. Abra o programa.
3. Configure o proxy, se necessário.
4. Confira a URL do Apps Script e os grupos monitorados.
5. Clique em **INICIAR**.
6. Na primeira execução, faça a autenticação do WhatsApp.
7. A sessão é preservada pelo LocalAuth.

## Build

O GitHub Actions valida o JavaScript, gera o Windows Portable e publica automaticamente a Release correspondente à versão.

> Usa WhatsApp Web por meio de `whatsapp-web.js`; mudanças no WhatsApp Web podem exigir atualização futura.
