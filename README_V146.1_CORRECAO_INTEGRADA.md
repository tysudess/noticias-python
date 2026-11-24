# V146.1 — Estúdio de Artes: V146 + correção da inicialização V145

## Base conferida

- Repositório: `tysudess/noticias-python`
- Branch: `main`
- Commit-base conferido: `ca8a6228d2b44fff5c13bf1a1153ab540e889ef0`

## O que este pacote reúne

Esta entrega consolidada contém os recursos da V146 e a correção do erro de inicialização identificado na V145. A integração foi unificada para instalar o proxy de acesso adiado ao canvas antes da criação da interface e, depois de construir a página, aplicar primeiro os recursos V145 e em seguida os recursos V146.

### Recursos V146 preservados

- Agrupar e desagrupar objetos com `Ctrl+G` e `Ctrl+Shift+G`.
- Preservar grupos dentro de projetos `.centralart`.
- Ajustar brilho, contraste, saturação e nitidez com prévia.
- Aplicar molduras, contornos e sombras.
- Persistir ajustes e efeitos nos projetos.

### Correção V145.1 incorporada

- Corrige a conexão antecipada do botão de zoom `100%`, que acessava `self.view` antes da criação do canvas.
- Utiliza uma propriedade com proxy adiado; depois da criação, o acesso passa ao `QGraphicsView` real.
- Mantém a sequência de ativação V145 → V146.

## Arquivos do ZIP

1. `src/monitor_noticias/ui/art_studio_integration.py` — integração consolidada com a correção de inicialização e ativação V146.
2. `src/monitor_noticias/ui/art_studio_v146.py` — recursos adicionais V146.
3. `tests/unit/test_art_studio_v146.py` — testes da V146.
4. `tests/unit/test_art_studio_view_startup.py` — testes de regressão da inicialização e da ordem V145/V146.

Os caminhos de destino são os mesmos do repositório. O ZIP contém apenas esses quatro arquivos, além deste README. Não altera `art_studio_page.py`, dependências, `.spec` ou workflows.

## Aplicação

Extraia o pacote na raiz do repositório e envie todos os arquivos preservando os caminhos. **Use este pacote consolidado no lugar dos ZIPs V145.1 e V146 separados.** Não aplique os dois pacotes antigos em sequência: ambos substituem `art_studio_integration.py`.

## Validação desta preparação

Foram executadas verificações sintáticas Python, testes estruturais dos recursos V146 e testes de regressão para a correção do zoom e a ordem de instalação V145/V146. A interface Qt real e os builds oficiais Windows/Ubuntu precisam ser confirmados após o envio ao GitHub.
