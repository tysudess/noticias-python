# MIGRAÇÃO — PASSO 20

## Escopo

Concluir o run existente `34768584764` do candidato `186a28e4a5f53296178fd9d0ee74637a8a5149bf`, sem criar automaticamente outro candidato e sem alterar código antes de conhecer o resultado.

## Resultado do run

- status: `completed`
- conclusion: `failure`
- head SHA: `186a28e4a5f53296178fd9d0ee74637a8a5149bf`
- build job: `success`
- external validation job: `failure`

O run efetivamente pertence ao candidato esperado.

## Build

A build limpa concluiu com sucesso.

- suíte: `148 passed`
- smoke local: PASS
- ZIP: `MONITOR-DE-NOTICIAS-PYTHON-portable-windows-x64.zip`
- ZIP bytes: `651329759`
- pasta descompactada bytes: `1262864276`
- SHA-256 build: `5ebd57f312d3ce66b51b10b1abda8d92076a7971ad25aeb0bf0b23f78ee13cf2`

## Segundo runner

Runner: `GitHub Actions 1000000690` / `windows-latest`.

- Windows Server 2025
- NT 10.0.26100
- AMD64
- somente ZIP recebido
- sem checkout de desenvolvimento
- FFmpeg/FFprobe globais ausentes

SHA-256 recalculado:

`5ebd57f312d3ce66b51b10b1abda8d92076a7971ad25aeb0bf0b23f78ee13cf2`

Resultado: IDÊNTICO ao hash da build.

## Evidência positiva antes da falha

Passaram no segundo runner:

- reextração do zero
- primeira inicialização
- Qt/resources/bancos/log
- FFmpeg empacotado
- FFprobe empacotado
- primeiro smoke completo
- banco/persistência
- notícias
- vídeos
- automação
- Extrator
- PDF
- Editor de Vídeo
- preview/play/pause
- seek 500/1000/1500 ms
- exportação H.264/AAC
- reabertura
- movimentação física da pasta
- caminho com espaços
- caminho com acentos
- nova abertura após movimentação
- segundo smoke até depois do Extrator

PORT-004 não reapareceu.

## PORT-005 — novo bloqueador

Classificação: **FALHA DO GATE**.

Mensagem:

`Evento de notícia nova não acionou callback de notificação.`

Causa comprovada:

- o primeiro smoke grava a notícia artificial em `temp/pipeline-smoke/news.db`;
- o segundo smoke usa a mesma pasta/banco já movidos;
- `FakeGoogle` devolve novamente o mesmo link artificial fixo;
- o repository corretamente não o contabiliza como notícia nova;
- `AutomationService` corretamente só notifica quando o resultado possui novos itens;
- o gate, porém, recria uma lista de eventos vazia e exige uma nova notificação em toda execução.

A asserção do segundo smoke não é idempotente. O resultado não comprova defeito no motor de notificação.

Status do PORT-005: **ABERTO / NÃO CORRIGIDO NESTE PASSO**.

## Por que não houve correção

O Passo 20 exige que, diante de falha técnica real, a validação pare e qualquer correção seja feita em novo commit, seguido obrigatoriamente de nova build, novo ZIP, novo hash e nova validação.

Por isso nenhuma alteração no gate, no `AutomationService` ou no aplicativo foi feita no Passo 20.

## Itens não concluídos depois da falha

Como o segundo smoke abortou no gate de notificação antes do teardown:

- restante do pipeline depois desse ponto no segundo smoke: NÃO EXECUTADO
- shutdown final do segundo smoke: NÃO EXECUTADO
- gate final de processos órfãos: NÃO EXECUTADO
- marcadores finais de segredos/dados pessoais pós-smoke: NÃO EXECUTADOS

A evidência correspondente do primeiro smoke continua válida, mas não substitui o requisito do segundo smoke integral.

## Warnings

Mensagens DXVA2 foram classificadas como warnings inofensivos neste ambiente, pois o preview realmente avançou e os seeks funcionaram. Não foram usadas para mascarar o erro real do gate.

## MIGs

`MIG-079`–`MIG-083` não foram promovidos. O ciclo externo obrigatório não completou, portanto o estado documental anterior é preservado.

## Repositório original

`tysudess/noticias-monitor`, branch `work/v8-extrator-v301-tab`, permanece em `e7b5d8eaac68bce6a9785e4da5b8ca5f83c34d2e`.

Não houve modificação do Kotlin.

## Rastreabilidade

Commit de código/artefato avaliado:

`186a28e4a5f53296178fd9d0ee74637a8a5149bf`

A documentação do resultado é posterior e não integra o ZIP portable. O commit documental deve ser registrado separadamente no relatório final do Passo 20.

## Conclusão

**PORTABLE NÃO VALIDADO — FALHA TÉCNICA**
