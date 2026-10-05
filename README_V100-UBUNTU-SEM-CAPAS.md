# Central V100 — Ubuntu sem a aba Capas

Base usada: `main` em `8cfd60f26fc9869faf510dd02626a09c012a4649`.

## Alteração

A seção **Capas** foi retirada exclusivamente da versão Ubuntu/Linux.

No Linux:

- `Section.COVERS` não entra em `SECTION_ORDER`;
- a aba não aparece no menu lateral;
- a página não entra no `QStackedWidget`;
- `Section.COVERS` também é retirada de `TOOL_SECTIONS`;
- as demais abas continuam na mesma ordem.

No Windows:

- a aba **Capas** permanece disponível;
- nenhuma funcionalidade de Capas foi removida do Windows.

O código-fonte da ferramenta de Capas foi preservado no repositório para o Windows. A mudança apenas impede que a seção seja exposta/ativada na versão Linux.

## Gravador de Tela

Esta atualização não altera o gravador. A correção do gravador Ubuntu deve continuar separadamente sobre esta base, evitando misturar duas mudanças no mesmo diagnóstico.

**WORKFLOW: NÃO PRECISA ALTERAR.**
