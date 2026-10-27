# V118 — Correções complementares do restante do programa

Base de referência: `main` do repositório `tysudess/noticias-python`, commit `6750157d805fc94c3f684ad924d48c18a02bf4ff`.

## O que muda

- **Login:** adiciona controle para mostrar/ocultar a senha, mantendo-a oculta por padrão.
- **Falhas transitórias de acesso:** preserva a senha digitada quando o problema é rede, proxy ou TLS, para permitir nova tentativa sem redigitação. Falhas de autenticação continuam limpando o campo.
- **Configurações:** adiciona controle para mostrar/ocultar a senha do Proxy Geral e volta a ocultá-la depois de salvar.
- **Ubuntu:** troca o rótulo “Iniciar com o Windows” por “Iniciar com o sistema” na tela de configurações, sem mudar o mecanismo de inicialização.
- **Fontes:** separa as fontes gerais das fontes de mídia especializada na lista de seleção, sem duplicar as especializadas na aba Notícias. A seleção de “todas” da mídia especializada passa a ser independente.
- **Busca de notícias:** combina as seleções independentes de fontes gerais e especializadas na execução real, mantendo compatibilidade com as preferências já gravadas.
- **Editor de vídeo:** atualiza o tamanho da prévia depois que o layout termina de redimensionar a janela, inclusive quando a reprodução está pausada.

O patch não desativa verificações de acesso, não muda permissões de usuário, não desativa validação TLS e não altera o transporte/proxy de autenticação. As correções anteriores de capas, extratores, PDF e gravação de tela permanecem instaladas. No Ubuntu, a opção de inicialização passa a usar o rótulo “Iniciar com o sistema”.

## Arquivos

### SUBSTITUIR
- `src/monitor_noticias/app/composition.py`
- `src/monitor_noticias/app/runtime_runners.py`

### ADICIONAR
- `src/monitor_noticias/ui/remaining_program_patch.py`
- `tests/unit/test_v118_remaining_program_fixes.py`
- `README_V118_RESTANTE_PROGRAMA.md`

### WORKFLOW
`WORKFLOW: NÃO PRECISA ALTERAR`

## Validação

Os testes V118 cobrem a política de preservação de senha em falhas transitórias, a manutenção das proteções de autenticação e a integração dos patches anteriores. A validação completa dos workflows Windows e Ubuntu deve ser realizada depois de aplicar o ZIP no repositório; este pacote, sozinho, não executa CI remoto nem publica uma nova release.
