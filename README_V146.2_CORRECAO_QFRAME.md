# V146.2 — correção da inicialização do Estúdio de Artes

Base verificada: `aa756feecd1b8ead95f7ed5f1286505f87b92f9d` (`main`).

## Causa

O traceback do Windows aponta para `art_studio_v146.py`, dentro de `enhance_art_studio_page_v146`, ao construir `tools = QFrame()`. O módulo V146 utilizava `QFrame` sem declará-lo na lista de imports, gerando `NameError` durante a inicialização da página.

## Correção

`art_studio_integration.py` agora importa `QFrame` de PySide6 e o disponibiliza no namespace do módulo V146 imediatamente antes de executar o aprimoramento V146. A integração preserva o adaptador `_DeferredArtStudioView` da correção V145.1 e mantém a chamada de V145 antes da V146.

## Arquivos do pacote

- `src/monitor_noticias/ui/art_studio_integration.py`
- `tests/unit/test_art_studio_v146_qframe.py`
- `README_V146.2_CORRECAO_QFRAME.md`

Não há mudança em dependências, workflows, nome dos executáveis, tela do editor, módulos V145 ou recursos da V146. Não foi feita alteração direta no GitHub.

## Validação realizada

- Testes de regressão estáticos desta correção: 3 aprovados.
- Compilação sintática Python dos dois arquivos `.py`: aprovada.
- Integridade do ZIP: aprovada.

A execução da interface Qt e os builds oficiais Windows/Ubuntu ainda precisam ser confirmados após o envio deste pacote ao repositório.
