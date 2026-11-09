# V128 — Proporção original e formato Celular deitado no Editor de Vídeo

Base conferida: `tysudess/noticias-python`, branch `main`, commit `1d6563743265a8d8142a214ce8577913f67a99e0` (V127).

## Arquivos do pacote

**SUBSTITUIR** no repositório:
- `src/monitor_noticias/video_editor/integrated_editor/__init__.py`

**ADICIONAR** ao repositório:
- `src/monitor_noticias/video_editor/output_format.py`
- `src/monitor_noticias/ui/video_output_format_v128.py`
- `tests/unit/test_video_output_format_v128.py`

## Comportamento

- A opção padrão é **Original — manter formato do vídeo**. Mantém a proporção do primeiro vídeo da timeline; com vários clipes, os demais são encaixados nesse quadro sem esticar nem cortar.
- A opção **Celular deitado — 16:9** cria um quadro horizontal 16:9.
- O seletor de resolução continua separado: Original, 360p, 480p, 720p e 1080p.
- O modo 16:9 usa a resolução selecionada; com resolução Original, usa o maior lado do primeiro vídeo, limitado a Full HD.
- Se a proporção de origem não for 16:9, o conteúdo é reduzido para caber integralmente no quadro. O espaço restante recebe faixas pretas, sem deformar nem cortar o vídeo.
- A pré-visualização mantém a proporção de origem.
- A escolha de formato participa da estimativa e da exportação final, tanto com tamanho automático quanto com tamanho aproximado definido pelo usuário.

## Workflows

Não alterar workflows. O pacote altera `src/**`, coberto pelos triggers existentes, e adiciona teste em `tests/**`. Os workflows Windows Portable e Ubuntu Portable devem executar os testes e gerar seus pacotes depois do push na `main`.

## Validação

A base V127 tinha builds Windows e Ubuntu concluídos com sucesso no commit informado. Esta V128 precisa ser validada pelos workflows depois da aplicação. Nenhum commit ou push foi feito por esta preparação.
