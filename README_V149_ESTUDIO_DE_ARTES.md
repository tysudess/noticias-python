# Central Inteligente de Mídia — V149

## Base

Preparada sobre o `main` consultado em 25/11/2026, commit `9c7969bf2f50789c8100a75db0a40c755f830c82` (V147). Como a V148 ainda não constava na árvore desse `main`, este pacote é cumulativo: inclui V148 e V149, para aplicação única e sequencial.

## Recursos incluídos

### V148 — dimensionamento e preservação
- Alças de redimensionamento para imagens e largura das caixas de texto.
- Campos de largura/altura, manutenção de proporção e espelhamento.
- Persistência da transformação livre das imagens em `.centralart`.
- Proteção das camadas existentes durante a inclusão de novos elementos.

### V149 — precisão e acabamento
- Inspetor de posição X/Y em pixels para o objeto selecionado.
- Preenchimento e contorno configuráveis para retângulos e círculos.
- Espessura de contorno ajustável; valor zero remove o contorno.
- Persistência da aparência das formas em projetos `.centralart`, inclusive dentro de grupos.
- Movimentação precisa com as setas (1 px), `Shift` + setas (10 px) e duplicação por `Ctrl+D`.
- As setas não interceptam a navegação do cursor quando um texto está em edição.

## Arquivos do pacote

- `run.py` — instala as camadas V148 e V149 depois da integração existente e antes do início da aplicação.
- `src/monitor_noticias/ui/art_studio_v148.py` — módulo cumulativo V148.
- `src/monitor_noticias/ui/art_studio_v149.py` — novas ferramentas V149.
- `tests/unit/test_art_studio_v148.py` — regressões V148.
- `tests/unit/test_art_studio_v149.py` — regressões V149.

## Aplicação

Extraia o ZIP na raiz do repositório, mantendo os caminhos, e envie todos os arquivos juntos. Não envie V148 e V149 separadamente. Nenhuma dependência adicional ou alteração de workflow é necessária.

## Validação

Testes estruturais e compilação sintática devem ser executados antes de gerar os builds oficiais Windows Portable e Ubuntu Portable. A interface Qt não foi executada neste ambiente porque PySide6 não está instalado; portanto, o teste visual e o teste funcional interativo ainda precisam ocorrer nos builds.
