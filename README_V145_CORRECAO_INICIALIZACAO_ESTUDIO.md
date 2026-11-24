# V145.1 — Correção da inicialização do Estúdio de Artes

## Base conferida

Repositório: `tysudess/noticias-python`  
Branch: `main`  
Commit-base: `ca8a6228d2b44fff5c13bf1a1153ab540e889ef0`

## Causa

Durante `ArtStudioPage._build_ui`, o botão de zoom `100%` conectava-se a `self.view.actual_size` antes da criação do `self.view` real. Python avalia esse atributo no momento da conexão, provocando `AttributeError` e interrompendo a inicialização da Central.

## Correção

O arquivo de integração instala uma propriedade compatível com acesso adiado ao canvas. Antes da criação do `QGraphicsView`, a propriedade fornece uma pequena fachada para a conexão do botão. Depois que `ArtStudioPage._build_ui` atribui o canvas real a `self.view`, todas as leituras passam a retornar o componente real. O botão `100%` então encaminha a chamada ao canvas já inicializado.

A alteração é limitada à integração do Estúdio e a um teste de regressão. Não modifica `art_studio_page.py`, os arquivos de projeto `.centralart`, ferramentas existentes, dependências, workflows ou configurações de build.

## Arquivos do pacote

- `src/monitor_noticias/ui/art_studio_integration.py`
- `tests/unit/test_art_studio_view_startup.py`

Os caminhos de destino são os mesmos do repositório.

## Validação

Foram executadas verificações de sintaxe Python e os testes estruturais de regressão deste pacote. A interface Qt e os builds Windows/Ubuntu devem ser confirmados pelos workflows após a aplicação no GitHub.
